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
    if specs is not None:
        fd, tmp_path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"inputs": specs}, fh, indent=2)
        except Exception:
            os.unlink(tmp_path)
            raise
        opts["specs"] = tmp_path
    elif specs_path is not None:
        opts["specs"] = specs_path

    try:
        _, stdout = _engine().run_gpa(opts, True)
    finally:
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
