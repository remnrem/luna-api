"""Direct reader for Luna STOUT output databases (.db files).

Provides :class:`destrat`, a pure-Python / SQLite reader that replicates
the functionality of the ``destrat`` command-line tool without subprocess
overhead.  One or more ``.db`` files (glob patterns accepted) are opened
read-only, and data can be extracted as tidy pandas DataFrames.

Example usage::

    import lunapi as lp

    db = lp.destrat('out/run-*.db')
    db.tables()                                   # summary of available data
    df = db.get('+PSD', r=['B', 'CH'])            # all PSD vars, all levels
    df = db.get('+PSD', r='B/ALPHA,SIGMA CH', v=['PSD'])  # destrat-style
    df = db.get('+PSD', r={'B': ['ALPHA','SIGMA'], 'CH': None}, v=['PSD'])
    df = db.get('STATS')                          # baseline (no row factors)
"""

import glob
import os
import sqlite3
import warnings
from collections import defaultdict

import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_r(r):
    """Return {factor_name: set_of_levels_or_None} from any supported input.

    Accepted forms:
      - None                        → {} (no factor filtering)
      - list  ['B', 'CH']           → all levels of each factor
      - dict  {'B': ['A','S'], 'CH': None}
      - str   'B/ALPHA,SIGMA CH'    → destrat-style
    """
    if r is None:
        return {}
    if isinstance(r, dict):
        return {k: (set(v) if v is not None else None) for k, v in r.items()}
    if isinstance(r, str):
        r = r.split()
    # list of tokens, each 'FAC' or 'FAC/L1,L2'
    result = {}
    for token in r:
        parts = token.split('/', 1)
        fac = parts[0]
        levels = set(parts[1].split(',')) if len(parts) > 1 else None
        result[fac] = levels
    return result


def _placeholders(n):
    return ','.join('?' * n)


# ---------------------------------------------------------------------------
# Per-file metadata cache
# ---------------------------------------------------------------------------

class _DBMeta:
    """Load and cache all metadata tables from one .db file."""

    __slots__ = (
        'path',
        'factors',      # factor_id  -> factor_name
        'factor_ids',   # factor_name -> factor_id
        'variables',    # variable_id -> variable_name
        'var_ids',      # variable_name -> variable_id
        'individuals',  # indiv_id   -> indiv_name
        'ind_ids',      # indiv_name -> indiv_id
        'commands',     # cmd_id     -> cmd_name
        'strata_map',   # strata_id  -> {factor_name: level_name}
        'fset_index',   # frozenset(factor_names) -> [strata_id, ...]
    )

    def __init__(self, path):
        self.path = path
        self.factors = {}
        self.factor_ids = {}
        self.variables = {}
        self.var_ids = {}
        self.individuals = {}
        self.ind_ids = {}
        self.commands = {}
        self.strata_map = {}
        self.fset_index = defaultdict(list)
        self._load()

    def _load(self):
        con = sqlite3.connect(f'file:{self.path}?mode=ro', uri=True)
        try:
            cur = con.cursor()

            for fid, fname in cur.execute("SELECT factor_id, factor_name FROM factors"):
                self.factors[fid] = fname
                self.factor_ids[fname] = fid

            for vid, vname in cur.execute("SELECT variable_id, variable_name FROM variables"):
                self.variables[vid] = vname
                self.var_ids[vname] = vid

            for iid, iname in cur.execute("SELECT indiv_id, indiv_name FROM individuals"):
                self.individuals[iid] = iname
                self.ind_ids[iname] = iid

            for cid, cname in cur.execute("SELECT cmd_id, cmd_name FROM commands"):
                self.commands[cid] = cname

            # Build strata_map: strata_id -> {factor_name: level_name}
            for sid, fname, lname in cur.execute("""
                SELECT s.strata_id, f.factor_name, l.level_name
                FROM strata s
                JOIN levels l ON s.level_id = l.level_id
                JOIN factors f ON l.factor_id = f.factor_id
            """):
                if sid not in self.strata_map:
                    self.strata_map[sid] = {}
                self.strata_map[sid][fname] = lname

            # Index by factor-set
            for sid, fac_lvl in self.strata_map.items():
                fset = frozenset(fac_lvl.keys())
                self.fset_index[fset].append(sid)

        finally:
            con.close()

    def resolve_strata(self, required_fset, r_filter):
        """Return list of strata_ids matching required_fset and level filters."""
        candidates = self.fset_index.get(required_fset, [])
        if not r_filter:
            return list(candidates)
        result = []
        for sid in candidates:
            fac_lvl = self.strata_map[sid]
            ok = all(
                allowed is None or fac_lvl.get(fac) in allowed
                for fac, allowed in r_filter.items()
            )
            if ok:
                result.append(sid)
        return result


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class destrat:
    """Read one or more Luna STOUT output databases.

    Parameters
    ----------
    pattern : str or list of str
        Glob pattern, single path, or list of paths/patterns pointing to
        Luna ``.db`` files.

    Examples
    --------
    >>> db = lp.destrat('out/run-*.db')
    >>> db.tables()
    >>> db.get('+PSD', r=['B', 'CH'], v=['PSD'])
    >>> db.get('+PSD', r='B/ALPHA,SIGMA CH', v=['PSD'])
    >>> db.get('+PSD', r={'B': ['ALPHA','SIGMA'], 'CH': None})
    >>> db.get('STATS')
    """

    def __init__(self, pattern):
        if isinstance(pattern, (list, tuple)):
            files = []
            for p in pattern:
                files.extend(sorted(glob.glob(os.path.expanduser(str(p)))))
        else:
            files = sorted(glob.glob(os.path.expanduser(str(pattern))))

        files = [f for f in files if os.path.isfile(f)]
        if not files:
            raise FileNotFoundError(f"No .db files found matching: {pattern!r}")

        self._files = files
        if len(files) > 1:
            print(f"attaching {len(files)} databases")

        self._meta = {f: _DBMeta(f) for f in files}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def tables(self):
        """Summary of all command/strata/variable combinations across all databases.

        Returns
        -------
        pandas.DataFrame
            Columns: ``CMD``, ``FACTORS``, ``N_VARS``, ``VARIABLES``
        """
        rows = []
        seen = set()

        for f, meta in self._meta.items():
            # Detect which strata have epoch/interval timepoints
            con = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            try:
                cur = con.cursor()

                # strata_id -> has_timepoints
                has_tp = {}
                for sid, has_t in cur.execute(
                    "SELECT DISTINCT strata_id, (timepoint_id IS NOT NULL) FROM datapoints"
                ):
                    has_tp[sid] = has_tp.get(sid, False) or bool(has_t)

                # variable_ids per strata_id
                vars_by_strata = defaultdict(set)
                for sid, vid in cur.execute(
                    "SELECT DISTINCT strata_id, variable_id FROM datapoints"
                ):
                    vars_by_strata[sid].add(vid)
            finally:
                con.close()

            # Group strata by (cmd, row-factors, has_timepoints)
            group_vars = defaultdict(set)  # (cmd, factors_tuple, has_tp_flag) -> var_ids
            for fset, sids in meta.fset_index.items():
                cmd_facs = [fn for fn in fset if fn.startswith('_')]
                row_facs = tuple(sorted(fn for fn in fset if not fn.startswith('_')))
                cmd = cmd_facs[0][1:] if cmd_facs else 'NA'
                tp_flag = any(has_tp.get(sid, False) for sid in sids)
                key = (cmd, row_facs, tp_flag)
                for sid in sids:
                    group_vars[key].update(vars_by_strata.get(sid, set()))

            for (cmd, row_facs, tp_flag), vid_set in sorted(group_vars.items()):
                fac_list = list(row_facs)
                if tp_flag:
                    fac_list = ['E'] + fac_list  # put E first
                factors_str = ','.join(fac_list)
                key = (cmd, factors_str)
                if key in seen:
                    continue
                seen.add(key)
                var_names = sorted(meta.variables.get(vid, str(vid)) for vid in vid_set)
                rows.append({
                    'CMD': cmd,
                    'FACTORS': factors_str,
                    'N_VARS': len(var_names),
                    'VARIABLES': ','.join(var_names),
                })

        # Baseline (NULL strata_id) — checked once across all files
        baseline_vids = set()
        baseline_meta = None
        for f2, meta2 in self._meta.items():
            con2 = sqlite3.connect(f'file:{f2}?mode=ro', uri=True)
            try:
                cur2 = con2.cursor()
                for (vid,) in cur2.execute(
                    "SELECT DISTINCT variable_id FROM datapoints WHERE strata_id IS NULL"
                ):
                    baseline_vids.add(vid)
                    baseline_meta = meta2
            finally:
                con2.close()
        if baseline_vids and baseline_meta is not None:
            key = ('NA', '')
            if key not in seen:
                vnames = sorted(
                    baseline_meta.variables.get(vid, str(vid)) for vid in baseline_vids
                )
                rows.append({
                    'CMD': 'NA',
                    'FACTORS': '',
                    'N_VARS': len(vnames),
                    'VARIABLES': ','.join(vnames),
                })

        if not rows:
            return pd.DataFrame(columns=['CMD', 'FACTORS', 'N_VARS', 'VARIABLES'])
        return (
            pd.DataFrame(rows)
            .drop_duplicates(subset=['CMD', 'FACTORS'])
            .sort_values(['CMD', 'FACTORS'])
            .reset_index(drop=True)
        )

    def vars(self, cmd=None):
        """List variables available in the database(s).

        Parameters
        ----------
        cmd : str, optional
            Filter to a single command (e.g. ``'PSD'``).  Leading ``+``/``#``
            is stripped automatically.

        Returns
        -------
        pandas.DataFrame
            Columns: ``CMD``, ``VAR``
        """
        if cmd is not None:
            cmd = cmd.lstrip('+#')

        seen = set()
        rows = []
        for f in self._files:
            con = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            try:
                cur = con.cursor()
                if cmd is not None:
                    cur.execute(
                        "SELECT DISTINCT variable_name, command_name FROM variables"
                        " WHERE command_name = ?",
                        (cmd,),
                    )
                else:
                    cur.execute(
                        "SELECT DISTINCT variable_name, command_name FROM variables"
                    )
                for vname, cname in cur.fetchall():
                    k = (cname, vname)
                    if k not in seen:
                        seen.add(k)
                        rows.append({'CMD': cname, 'VAR': vname})
            finally:
                con.close()

        if not rows:
            return pd.DataFrame(columns=['CMD', 'VAR'])
        return (
            pd.DataFrame(rows)
            .sort_values(['CMD', 'VAR'])
            .reset_index(drop=True)
        )

    def get(self, cmd, r=None, v=None, ids=None, c=None):
        """Extract data from the database(s) and return a tidy DataFrame.

        Parameters
        ----------
        cmd : str
            Command name.  Leading ``+`` or ``#`` is accepted and stripped,
            so ``'+PSD'``, ``'#PSD'``, and ``'PSD'`` are all equivalent.
        r : str, list, or dict, optional
            Row stratifiers — each unique combination becomes a separate row.
            Accepted forms (all equivalent):

            - space-separated string: ``'B CH'`` or ``'B/ALPHA,SIGMA CH'``
            - list: ``['B', 'CH']``
            - dict: ``{'B': ['ALPHA','SIGMA'], 'CH': None}``

            A ``/``-suffix restricts to specific levels: ``'B/ALPHA,SIGMA'``.
            Use ``'E'`` to include epoch numbers (joined from timepoints table).
        c : str, list, or dict, optional
            Column stratifiers — each level combination is pivoted into its
            own set of column(s) named ``VAR.FAC_LEVEL``.  Accepts the same
            forms as *r*.
        v : str or list of str, optional
            Variable name(s) to include.  Space-separated string accepted.
            ``None`` returns all variables.
        ids : str or list of str, optional
            Individual IDs to include.  Space-separated string accepted.
            ``None`` returns all individuals.

        Returns
        -------
        pandas.DataFrame
            Without *c*: columns are ``ID``, row-factor columns, variable
            columns.  With *c*: variable columns are named ``VAR.FAC_LVL``
            for each col-strata level.  Missing combinations yield ``NaN``.
        """
        # ---- parse arguments ----
        cmd_name = cmd.lstrip('+#') if cmd else None
        cmd_factor = f'_{cmd_name}' if cmd_name else None

        r_filter = _parse_r(r)
        c_filter = _parse_r(c)

        overlap = set(r_filter) & set(c_filter)
        if overlap:
            raise ValueError(
                f"factor(s) cannot appear in both r= and c=: {sorted(overlap)}"
            )

        req_epoch = 'E' in r_filter or 'E' in c_filter
        req_interval = 'T' in r_filter or 'T' in c_filter
        req_timepoints = req_epoch or req_interval

        # Factors that map to real DB strata factors (not E/T timepoint markers)
        regular_r = {k: val for k, val in r_filter.items() if k not in ('E', 'T')}
        regular_c = {k: val for k, val in c_filter.items() if k not in ('E', 'T')}
        all_regular = {**regular_r, **regular_c}

        required_fset = frozenset(
            ([cmd_factor] if cmd_factor else []) +
            list(regular_r.keys()) +
            list(regular_c.keys())
        )

        # Normalise v and ids: accept space-separated strings
        if isinstance(v, str):
            v = v.split()
        if isinstance(ids, str):
            ids = ids.split()

        # Ordered factor column names for row index vs column labels
        def _factor_names(spec):
            if spec is None:
                return []
            if isinstance(spec, dict):
                return list(spec.keys())
            if isinstance(spec, str):
                return [tok.split('/')[0] for tok in spec.split()]
            return [tok.split('/')[0] for tok in spec]

        row_factor_names = _factor_names(r)
        col_factor_names = _factor_names(c)

        all_long = []
        matched_any = False

        for f, meta in self._meta.items():

            # ---- find matching strata_ids ----
            if required_fset:
                matched_sids = meta.resolve_strata(required_fset, all_regular)
            else:
                matched_sids = None  # sentinel → strata_id IS NULL (baseline)

            if matched_sids is not None and not matched_sids:
                continue

            matched_any = True

            # ---- resolve filter IDs ----
            vid_filter = None
            if v is not None:
                vid_filter = [meta.var_ids[vn] for vn in v if vn in meta.var_ids]
                if not vid_filter:
                    continue

            iid_filter = None
            if ids is not None:
                iid_filter = [meta.ind_ids[id_] for id_ in ids if id_ in meta.ind_ids]
                if not iid_filter:
                    continue

            # ---- build SQL ----
            conditions = []
            params = []

            if matched_sids is None:
                conditions.append("d.strata_id IS NULL")
            else:
                conditions.append(
                    f"d.strata_id IN ({_placeholders(len(matched_sids))})"
                )
                params.extend(matched_sids)

            if req_timepoints:
                conditions.append("d.timepoint_id IS NOT NULL")
            else:
                conditions.append("d.timepoint_id IS NULL")

            if vid_filter:
                conditions.append(
                    f"d.variable_id IN ({_placeholders(len(vid_filter))})"
                )
                params.extend(vid_filter)

            if iid_filter:
                conditions.append(
                    f"d.indiv_id IN ({_placeholders(len(iid_filter))})"
                )
                params.extend(iid_filter)

            where = ' AND '.join(conditions)

            if req_timepoints:
                sql = f"""
                    SELECT d.indiv_id, d.variable_id, d.strata_id,
                           tp.epoch, tp.start, tp.stop, d.value
                    FROM datapoints d
                    LEFT JOIN timepoints tp ON d.timepoint_id = tp.timepoint_id
                    WHERE {where}
                """
            else:
                sql = f"""
                    SELECT d.indiv_id, d.variable_id, d.strata_id, d.value
                    FROM datapoints d
                    WHERE {where}
                """

            con = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            try:
                cur = con.cursor()
                cur.execute(sql, params)
                raw_rows = cur.fetchall()
            finally:
                con.close()

            if not raw_rows:
                continue

            # ---- convert to long-format dicts ----
            for raw in raw_rows:
                if req_timepoints:
                    indiv_id, var_id, strata_id, tp_epoch, tp_start, tp_stop, value = raw
                else:
                    indiv_id, var_id, strata_id, value = raw
                    tp_epoch = tp_start = tp_stop = None

                fac_lvl = (
                    meta.strata_map.get(strata_id, {}) if strata_id is not None else {}
                )

                row = {
                    'ID': meta.individuals.get(indiv_id, str(indiv_id)),
                    '_VAR': meta.variables.get(var_id, str(var_id)),
                    '_VAL': value,
                }

                # Row-factor columns
                for fn in row_factor_names:
                    if fn == 'E':
                        row['E'] = tp_epoch
                    elif fn == 'T':
                        row['T'] = f"{tp_start}_{tp_stop}"
                    else:
                        row[fn] = fac_lvl.get(fn)

                # Column-factor label (for c= pivot)
                if col_factor_names:
                    parts = []
                    for fn in col_factor_names:
                        if fn == 'E':
                            parts.append(f"E_{tp_epoch}")
                        elif fn == 'T':
                            parts.append(f"T_{tp_start}_{tp_stop}")
                        else:
                            parts.append(f"{fn}_{fac_lvl.get(fn, 'NA')}")
                    row['_CLAB'] = '.'.join(parts)

                all_long.append(row)

        if not matched_any:
            warnings.warn(
                f"No matching strata found for cmd={cmd!r}, r={r!r}",
                stacklevel=2,
            )
            return pd.DataFrame()

        if not all_long:
            return pd.DataFrame()

        # ---- pivot to wide format ----
        long_df = pd.DataFrame(all_long)
        index_cols = ['ID'] + [fn for fn in row_factor_names if fn in long_df.columns]

        if col_factor_names:
            # c= mode: column names are VAR.CLAB
            long_df['_COL'] = long_df['_VAR'] + '.' + long_df['_CLAB']
            wide_df = long_df.pivot_table(
                index=index_cols,
                columns='_COL',
                values='_VAL',
                aggfunc='first',
            )
            wide_df.columns.name = None
            wide_df = wide_df.reset_index()
            # order columns: if v given, group by v order then c-label sort
            existing_index = set(index_cols)
            if v is not None:
                var_cols = sorted(
                    (col for col in wide_df.columns if col not in existing_index),
                    key=lambda col: (
                        v.index(col.split('.')[0]) if col.split('.')[0] in v else len(v),
                        col,
                    ),
                )
            else:
                var_cols = sorted(c for c in wide_df.columns if c not in existing_index)
        else:
            # r= only mode: column names are VAR
            wide_df = long_df.pivot_table(
                index=index_cols,
                columns='_VAR',
                values='_VAL',
                aggfunc='first',
            )
            wide_df.columns.name = None
            wide_df = wide_df.reset_index()
            existing_index = set(index_cols)
            if v is not None:
                var_cols = [vn for vn in v if vn in wide_df.columns]
            else:
                var_cols = sorted(col for col in wide_df.columns if col not in existing_index)

        final_cols = [col for col in index_cols if col in wide_df.columns] + var_cols
        return wide_df[final_cols].reset_index(drop=True)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self):
        n = len(self._files)
        if n == 1:
            return f"destrat('{self._files[0]}')"
        return f"destrat([{n} files])"

    def __len__(self):
        return len(self._files)

    @property
    def files(self):
        """List of resolved .db file paths."""
        return list(self._files)


__all__ = ['destrat']
