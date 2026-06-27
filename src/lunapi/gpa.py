#    --------------------------------------------------------------------
#
#    This file is part of Luna.
#
#    LUNA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Luna is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Luna. If not, see <http://www.gnu.org/licenses/>.
#
#    Please see LICENSE.txt for more details.
#
#    --------------------------------------------------------------------

"""lunapi.gpa — Python interface to Luna's GPA association-analysis commands.

Two underlying Luna commands are exposed:

  --gpa-prep  build a binary data matrix from tabular input files
  --gpa       run linear association models on that matrix

Both are invoked in-process via the lunapi0 C++ bindings (no subprocess).
"""

import io
import json
import os
import tempfile
from typing import Dict, List, Optional, Union

import pandas as pd

import lunapi.lunapi0 as _l0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _engine():
    return _l0.inaugurate()


def _parse_tsv(text: str) -> pd.DataFrame:
    """Parse a tab-delimited stdout block (manifest / dump) into a DataFrame."""
    text = text.strip()
    if not text:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(text), sep="\t", dtype=str)


def _rtables_to_dfs(raw: dict) -> Dict[str, pd.DataFrame]:
    """Convert rtables_return_t dict to {\"CMD: STRATA\" -> DataFrame}."""
    out: Dict[str, pd.DataFrame] = {}
    for cmd, strata_map in raw.items():
        for stratum, (cols, data) in strata_map.items():
            key = f"{cmd}: {stratum}"
            df = pd.DataFrame(data).T
            df.columns = cols
            out[key] = df
    return out


def _join(v: Union[str, List[str], None]) -> Optional[str]:
    if v is None:
        return None
    return ",".join(v) if isinstance(v, (list, tuple)) else str(v)


def _ensure_lf(path: str) -> tuple[str, bool]:
    """Normalize CR/CRLF→LF and strip trailing tabs from each line.

    Returns (path, created_temp). Creates a temp copy only if the file
    actually needed changes; otherwise returns the original path unchanged.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = normalized.split(b"\n")
    if lines:
        ncols = len(lines[0].split(b"\t"))
        for idx in range(1, len(lines)):
            if not lines[idx]:
                continue
            fields = lines[idx].split(b"\t")
            # Strip trailing empty fields that exceed the header column count
            while len(fields) > ncols and fields[-1] == b"":
                fields.pop()
            # Replace remaining empty fields with "." so the C++ parser accepts them
            fields = [f if f else b"." for f in fields]
            lines[idx] = b"\t".join(fields)
        normalized = b"\n".join(lines)
    if normalized == data:
        return path, False
    fd, tmp = tempfile.mkstemp(suffix=".tsv")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(normalized)
    except Exception:
        os.unlink(tmp)
        raise
    return tmp, True


def _validate_tsv(path: str, display_name: Optional[str] = None) -> None:
    """Pre-validate a tab-delimited file before passing it to the C++ engine.

    Raises ValueError identifying the file, row number, and column counts so
    the user gets an actionable message instead of a cryptic C++ RuntimeError.
    display_name overrides the filename shown in error messages (use the
    original path when validating a normalized temp copy).
    """
    label = os.path.basename(display_name or path)
    with open(path, "rb") as fh:
        raw = fh.read()

    lines = raw.split(b"\n")
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        raise ValueError(f"{label!r} is empty")

    expected = len(lines[0].split(b"\t"))
    for i, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        n = len(line.split(b"\t"))
        if n != expected:
            preview = repr(line[:120])
            raise ValueError(
                f"{label!r}: row {i} has {n} tab-delimited columns but the "
                f"header has {expected}\n  line content: {preview}"
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def gpa_prep(
    dat_path: str,
    specs: Optional[List[dict]] = None,
    specs_path: Optional[str] = None,
) -> str:
    """Run ``--gpa-prep`` to build a binary GPA data matrix.

    Exactly one of *specs* or *specs_path* should be supplied.

    Parameters
    ----------
    dat_path : str
        Output path for the binary ``.dat`` file.
    specs : list[dict] or None
        Structured input-file specification list.  Each dict may contain
        ``file``, ``group``, ``vars``, ``facs``, ``fixed``, ``mappings``.
        The list is serialised to a temporary JSON file and passed as
        ``specs=<tmpfile>`` to ``--gpa-prep``.
    specs_path : str or None
        Path to an existing JSON specs file.

    Returns
    -------
    str
        Manifest text captured from stdout (tab-delimited, same columns as
        :func:`gpa_manifest` output).  Empty if no manifest was produced.

    Raises
    ------
    RuntimeError
        Propagated from ``Helper::halt()`` inside the Luna C++ library.
    """
    opts: Dict[str, str] = {"dat": dat_path}

    tmp_path: Optional[str] = None
    lf_tmps: List[str] = []
    if specs is not None:
        normalized: List[dict] = []
        for entry in specs:
            if "file" in entry:
                orig = entry["file"]
                lf_path, created = _ensure_lf(orig)
                if created:
                    lf_tmps.append(lf_path)
                    entry = {**entry, "file": lf_path}
                _validate_tsv(entry["file"], display_name=orig)
            normalized.append(entry)

        fd, tmp_path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"inputs": normalized}, fh, indent=2)
        except Exception:
            os.unlink(tmp_path)
            raise
        opts["specs"] = tmp_path
    elif specs_path is not None:
        opts["specs"] = specs_path

    try:
        _, stdout = _engine().run_gpa(opts, True)
    except RuntimeError as exc:
        # Attach the specs file list so the error is traceable even when the
        # C++ message doesn't include a filename.
        files = [e["file"] for e in (specs or []) if "file" in e]
        context = ", ".join(os.path.basename(f) for f in files)
        raise RuntimeError(
            f"{exc}" + (f" (files: {context})" if context else "")
        ) from exc
    finally:
        for p in lf_tmps:
            try:
                os.unlink(p)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return stdout


def gpa_manifest(dat_path: str) -> pd.DataFrame:
    """Return the variable manifest for a ``.dat`` file as a DataFrame.

    Runs ``--gpa manifest`` and parses the tab-delimited stdout.

    Columns always include ``NV``, ``VAR``, ``NI``, ``GRP``, ``BASE``, plus
    any factor columns present in the dataset (e.g. ``CH``, ``F``, ``SS``).
    """
    opts: Dict[str, str] = {"dat": dat_path, "manifest": ""}
    _, stdout = _engine().run_gpa(opts, False)
    return _parse_tsv(stdout)


def gpa_run(
    dat_path: str,
    X: Union[str, List[str], None] = None,
    Y: Union[str, List[str], None] = None,
    Z: Union[str, List[str], None] = None,
    Xg: Union[str, List[str], None] = None,
    Yg: Union[str, List[str], None] = None,
    Zg: Union[str, List[str], None] = None,
    mode: str = "assoc",
    nreps: int = 0,
    fdr: bool = True,
    bonf: bool = False,
    holm: bool = False,
    fdr_by: bool = False,
    adj_all_x: bool = False,
    x_factors: bool = False,
    p: Optional[float] = None,
    padj: Optional[float] = None,
    vars: Optional[str] = None,
    xvars: Optional[str] = None,
    grps: Optional[str] = None,
    xgrps: Optional[str] = None,
    facs: Optional[str] = None,
    xfacs: Optional[str] = None,
    faclvls: Optional[str] = None,
    xfaclvls: Optional[str] = None,
    n_prop: Optional[float] = None,
    n_req: Optional[int] = None,
    knn: Optional[int] = None,
    winsor: Optional[float] = None,
    subset: Optional[str] = None,
    inc_ids: Optional[str] = None,
    ex_ids: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, pd.DataFrame]:
    """Run GPA association analysis against a pre-built ``.dat`` file.

    Parameters
    ----------
    dat_path : str
        Binary data file created by :func:`gpa_prep`.
    X, Y, Z : str | list[str] | None
        Predictor, outcome, and covariate variable names.
        Lists are joined with commas and passed as a single ``X=a,b,c`` argument.
    Xg, Yg, Zg : str | list[str] | None
        Group-based variable selection (predictor, outcome, covariate groups).
    mode : "assoc" | "stats" | "comp"
        * ``"assoc"``  — linear association models (default)
        * ``"stats"``  — descriptive statistics only
        * ``"comp"``   — comparison-style enrichment tests
    nreps : int
        Permutation replicates (0 = asymptotic p-values only).
    fdr : bool
        Apply FDR(B&H) correction (default True; pass ``fdr=False`` to disable).
    bonf, holm, fdr_by : bool
        Additional multiple-testing corrections to add to the output.
    adj_all_x : bool
        Adjust p-values across all X variables jointly instead of per-X.
    x_factors : bool
        Append X-variable manifest columns (XBASE, XGROUP, XSTRAT) to output.
    p, padj : float | None
        Only return rows below this nominal or adjusted significance threshold.
    vars, xvars : str | None
        Explicit variable include / exclude lists (comma-separated).
    grps, xgrps : str | None
        Group include / exclude lists.
    facs, xfacs : str | None
        Factor include / exclude lists.
    faclvls, xfaclvls : str | None
        Factor-level include / exclude filters (``CH/FZ|CZ`` syntax).
    n_prop : float | None
        Drop columns with more than this proportion of missing values.
    n_req : int | None
        Drop columns with fewer than this many non-missing values.
    knn : int | None
        k for kNN imputation of missing values.
    winsor : float | None
        Winsorisation proportion applied before modelling.
    subset : str | None
        Include only subjects positive for these variables (``+VAR`` syntax).
    inc_ids, ex_ids : str | None
        Comma-separated subject ID include / exclude lists.
    verbose : bool

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys follow ``"GPA: STRATA"`` convention, e.g.:
        ``"GPA: X,Y"`` — main association results
        ``"GPA: VAR"`` — descriptive statistics (mode="stats")
        ``"GPA: X"``   — comparison test results (mode="comp")
    """
    opts: Dict[str, str] = {"dat": dat_path}

    for key, val in [("X", X), ("Y", Y), ("Z", Z),
                     ("Xg", Xg), ("Yg", Yg), ("Zg", Zg)]:
        v = _join(val)
        if v is not None:
            opts[key] = v

    if nreps:       opts["nreps"]     = str(nreps)
    if not fdr:     opts["fdr"]       = "F"
    if bonf:        opts["bonf"]      = ""
    if holm:        opts["holm"]      = ""
    if fdr_by:      opts["fdr-by"]   = ""
    if adj_all_x:   opts["adj-all-X"] = ""
    if x_factors:   opts["X-factors"] = ""

    if mode == "stats": opts["stats"] = ""
    elif mode == "comp": opts["comp"] = ""

    if p    is not None: opts["p"]    = str(p)
    if padj is not None: opts["padj"] = str(padj)

    for k, v in [
        ("vars",     vars),    ("xvars",    xvars),
        ("grps",     grps),    ("xgrps",    xgrps),
        ("facs",     facs),    ("xfacs",    xfacs),
        ("faclvls",  faclvls), ("xfaclvls", xfaclvls),
    ]:
        if v is not None:
            opts[k] = v

    if n_prop is not None: opts["n-prop"] = str(n_prop)
    if n_req  is not None: opts["n-req"]  = str(n_req)
    if knn    is not None: opts["knn"]    = str(knn)
    if winsor is not None: opts["winsor"] = str(winsor)

    if subset:  opts["subset"]  = subset
    if inc_ids: opts["inc-ids"] = inc_ids
    if ex_ids:  opts["ex-ids"]  = ex_ids
    if verbose: opts["verbose"] = ""

    raw, _ = _engine().run_gpa(opts, False)
    return _rtables_to_dfs(raw)


def gpa_dump(dat_path: str, **filter_opts) -> pd.DataFrame:
    """Dump the raw data matrix from a ``.dat`` file as a DataFrame.

    Any keyword argument is forwarded as a Luna parameter string, e.g.
    ``X="male"``, ``lvars="PSD_CH_CZ_F_13.5"``.
    """
    opts: Dict[str, str] = {"dat": dat_path, "dump": ""}
    opts.update({k: str(v) for k, v in filter_opts.items()})
    _, stdout = _engine().run_gpa(opts, False)
    return _parse_tsv(stdout)


def gpa_get_xy_partial(xvar: str, yvar: str, zvars: List[str]):
    """Return (ids, x_resid, y_resid) after regressing *zvars* out of both axes.

    Uses the same Rz = I - Z(Z'Z)^{-1}Z' projection as the GPA linear model,
    so the residual scatter exactly matches what went into the regression.
    Falls back to :func:`gpa_get_xy` when *zvars* is empty.

    Raises ``RuntimeError`` if no matrix is cached (call :func:`gpa_run` first).
    """
    eng = _engine()
    if not eng.gpa_has_cache():
        raise RuntimeError(
            "No GPA matrix cached — call gpa_run() before gpa_get_xy_partial().")
    return eng.gpa_get_xy_partial(xvar, yvar, list(zvars))


def gpa_get_xy(xvar: str, yvar: str):
    """Return (ids, x_vals, y_vals) from the cached GPA analysis matrix.

    Filters to rows where both *xvar* and *yvar* are non-NaN — the exact
    same subjects used in the most recent :func:`gpa_run` call.

    Raises ``RuntimeError`` if no matrix is cached (call :func:`gpa_run` first).
    """
    eng = _engine()
    if not eng.gpa_has_cache():
        raise RuntimeError(
            "No GPA matrix cached — call gpa_run() before gpa_get_xy().")
    return eng.gpa_get_xy(xvar, yvar)


def gpa_clear_cache():
    """Release the cached GPA analysis matrix to free memory."""
    _engine().gpa_clear_cache()


__all__ = [
    "gpa_prep",
    "gpa_manifest",
    "gpa_run",
    "gpa_dump",
    "gpa_get_xy",
    "gpa_get_xy_partial",
    "gpa_clear_cache",
]
