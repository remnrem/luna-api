"""EDF manipulation and annotation analysis utilities.

Wraps ``luna`` command-line tools for operations not directly exposed through
the Python bindings: EDF merging/binding and multi-sample annotation overlap
analysis.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_luna(luna_bin=None):
    if luna_bin:
        return str(luna_bin)
    found = shutil.which('luna')
    if found:
        return found
    raise FileNotFoundError(
        "luna binary not found in PATH. "
        "Install luna or pass luna_bin='/path/to/luna'."
    )


def _run_luna(args, label):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"luna {label} failed (exit {result.returncode}):\n"
            f"{result.stderr.strip()}"
        )
    return result


def _str_list(x):
    """Normalise a str, list, or set to a comma-separated string."""
    if x is None:
        return None
    if isinstance(x, str):
        return x
    return ','.join(str(v) for v in x)


def _parse_files_arg(files):
    """Return list of (id, annot_path) from various input forms.

    Accepted forms
    --------------
    dict       {'id1': 'id1.annot', ...}
    list       [('id1', 'path'), ...] or ['path1', 'path2', ...]
    DataFrame  first col = ID, second col = annot file
    str        path to a Luna sample-list (ID  EDF  annot columns)
               or a glob pattern matched against annotation files
    """
    if isinstance(files, dict):
        return [(str(k), str(v)) for k, v in files.items()]

    if isinstance(files, pd.DataFrame):
        cols = files.columns.tolist()
        return [(str(r[cols[0]]), str(r[cols[1]])) for _, r in files.iterrows()]

    if isinstance(files, str):
        expanded = os.path.expanduser(files)
        if os.path.isfile(expanded):
            # Treat as a Luna sample list: ID \t EDF \t annot ...
            pairs = []
            with open(expanded) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith('%') or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        pairs.append((parts[0], parts[2]))
            if not pairs:
                raise ValueError(
                    f"No ID/annot pairs found in sample list: {files}\n"
                    "Expected tab-delimited columns: ID  EDF  annot-file"
                )
            return pairs
        else:
            # Glob: use filename stem as ID
            found = sorted(glob.glob(expanded))
            if not found:
                raise FileNotFoundError(f"No files matched: {files}")
            return [(Path(f).stem, f) for f in found]

    # iterable of (id, file) pairs or plain file paths
    result = []
    for item in files:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            result.append((str(item[0]), str(item[1])))
        else:
            p = str(item)
            result.append((Path(p).stem, p))
    return result


# ---------------------------------------------------------------------------
# EDF merging / binding
# ---------------------------------------------------------------------------

def merge_edfs(files, edf='merged.edf', id='merged',
               slist=None, fixed=False, luna_bin=None):
    """Concatenate EDFs in time (row-bind).

    Mirrors ``luna --merge``.  EDFs are ordered by their embedded start
    timestamps unless ``fixed=True``, in which case they are concatenated in
    the order supplied.  If there are gaps between recordings the output is
    written as EDF+D (discontinuous).

    Parameters
    ----------
    files : list of str
        EDF file paths to merge.
    edf : str
        Output EDF filename (default ``'merged.edf'``).
    id : str
        EDF record ID for the merged file (default ``'merged'``).
    slist : str, optional
        If given, write a one-row Luna sample-list to this path.
    fixed : bool
        If ``True``, ignore file timestamps and concatenate in list order.
    luna_bin : str, optional
        Path to the ``luna`` binary.  Defaults to searching PATH.

    Returns
    -------
    pathlib.Path
        Path to the written output EDF.

    Examples
    --------
    >>> lp.merge_edfs(['night1.edf', 'night2.edf'], edf='both_nights.edf', id='subj1')
    PosixPath('both_nights.edf')
    """
    luna = _find_luna(luna_bin)
    args = [luna, '--merge'] + [str(f) for f in files]
    args += [f'id={id}', f'edf={edf}']
    if slist:
        args.append(f'slist={slist}')
    if fixed:
        args.append('fixed=T')
    _run_luna(args, '--merge')
    return Path(edf)


def bind_edfs(files, edf='merged.edf', id='merged',
              slist=None, luna_bin=None):
    """Bind EDFs by adding channels (column-bind).

    Mirrors ``luna --bind``.  All EDFs must share the same start time and
    number of records.  Channels may have different sample rates.

    Parameters
    ----------
    files : list of str
        EDF file paths to bind.
    edf : str
        Output EDF filename (default ``'merged.edf'``).
    id : str
        EDF record ID for the bound file (default ``'merged'``).
    slist : str, optional
        If given, write a one-row Luna sample-list to this path.
    luna_bin : str, optional
        Path to the ``luna`` binary.  Defaults to searching PATH.

    Returns
    -------
    pathlib.Path
        Path to the written output EDF.

    Examples
    --------
    >>> lp.bind_edfs(['eeg.edf', 'eog.edf', 'emg.edf'], edf='psg.edf', id='subj1')
    PosixPath('psg.edf')
    """
    luna = _find_luna(luna_bin)
    args = [luna, '--bind'] + [str(f) for f in files]
    args += [f'id={id}', f'edf={edf}']
    if slist:
        args.append(f'slist={slist}')
    _run_luna(args, '--bind')
    return Path(edf)


# ---------------------------------------------------------------------------
# Multi-sample annotation overlap analysis
# ---------------------------------------------------------------------------

def overlap(
    files,
    seed,
    other=None,
    bg=None,
    nreps=1000,
    event_perm=False,
    event_perm_w=None,
    w=None,
    out=None,
    luna_bin=None,
    **kwargs,
):
    """Multi-sample annotation overlap / enrichment analysis.

    Mirrors ``luna --overlap``.  Pools annotation events across individuals
    into a single virtual timeline, then tests whether ``seed`` annotations
    overlap with ``other`` annotations (or themselves) more than expected by
    chance, assessed by permutation.

    Parameters
    ----------
    files : dict, list, DataFrame, or str
        Per-individual annotation files.  Accepted forms:

        ``dict``
            ``{'id1': 'id1.annot', 'id2': 'id2.annot', ...}``
        ``list``
            ``[('id1', 'path'), ('id2', 'path'), ...]``
            or a plain list of annotation file paths (filename stem → ID).
        ``DataFrame``
            Two columns: first = individual ID, second = annotation file.
        ``str``
            Path to a Luna sample-list (tab-delimited ID / EDF / annot)
            or a glob pattern matching annotation files.

    seed : str or list of str
        Annotation class(es) to use as seeds — the events whose enrichment
        is being tested.

    other : str or list of str, optional
        Annotation class(es) to measure overlap against.  Defaults to all
        annotations present other than the seeds.

    bg : str or list of str, optional
        Background annotation class(es) defining the regions within which
        permutations are performed.  Required unless ``event_perm=True``.

    nreps : int
        Number of permutations (default 1000).

    event_perm : bool
        Use event-based permutation (shuffle seed positions) instead of
        background-region shuffling.

    event_perm_w : float, optional
        Neighbourhood window in seconds for event permutation (default 5 s).

    w : float, optional
        Window size in seconds for distance-based calculations.

    out : str, optional
        Path for the output database.  If omitted, a temporary file is used;
        the path is accessible via ``result.files[0]``.

    luna_bin : str, optional
        Path to the ``luna`` binary.  Defaults to searching PATH.

    **kwargs
        Any additional ``luna --overlap`` parameters, e.g.
        ``edges=5``, ``pileup='T'``, ``seed_seed='T'``.

    Returns
    -------
    lp.destrat
        Output database reader.  Use ``.tables()`` to list available outputs
        and ``.get('OVERLAP', r='SEED')`` to extract results.

    Raises
    ------
    ValueError
        If neither ``bg`` nor ``event_perm=True`` is provided.
    FileNotFoundError
        If no annotation files are found or ``luna`` is not on PATH.

    Examples
    --------
    >>> db = lp.overlap(
    ...     {'id1': 'id1.annot', 'id2': 'id2.annot'},
    ...     seed='spindle',
    ...     bg='NREM',
    ...     nreps=1000,
    ... )
    >>> db.tables()
    >>> db.get('OVERLAP', r='SEED')

    >>> # from a sample list
    >>> db = lp.overlap('cohort.lst', seed='spindle', bg='NREM', other='SO')

    >>> # event permutation mode (no bg required)
    >>> db = lp.overlap(files, seed='spindle', event_perm=True, nreps=500)
    """
    from .destrat import destrat

    luna = _find_luna(luna_bin)

    if bg is None and not event_perm:
        raise ValueError(
            "Either bg= (background annotation) or event_perm=True is required.\n"
            "bg= defines the regions in which seed events are shuffled during permutation."
        )

    pairs = _parse_files_arg(files)
    if not pairs:
        raise ValueError("No annotation files resolved from 'files' argument")

    # Output database
    _out_is_tmp = out is None
    if _out_is_tmp:
        _tmpf = tempfile.NamedTemporaryFile(
            suffix='.db', prefix='luna_overlap_', delete=False
        )
        out = _tmpf.name
        _tmpf.close()

    # Working directory for the a-list and merged annotation temp file
    with tempfile.TemporaryDirectory(prefix='luna_overlap_work_') as workdir:
        # Write the a-list file (ID \t annot-path per line)
        alist_path = os.path.join(workdir, 'a-list.txt')
        with open(alist_path, 'w') as fh:
            for id_, afile in pairs:
                fh.write(f'{id_}\t{afile}\n')

        # Base name for the pooled annotation temp file luna will create
        merged_base = os.path.join(workdir, 'merged')

        # Build --options parameters
        opts = [
            f'a-list={alist_path}',
            f'merged={merged_base}',
            f'seed={_str_list(seed)}',
            f'nreps={nreps}',
        ]

        if event_perm:
            if event_perm_w is not None:
                opts.append(f'event-perm={event_perm_w}')
            else:
                opts.append('event-perm')
        else:
            opts.append(f'bg={_str_list(bg)}')

        if other is not None:
            opts.append(f'other={_str_list(other)}')

        if w is not None:
            opts.append(f'w={w}')

        for k, v in kwargs.items():
            # Convert Python booleans to T/F for luna
            if isinstance(v, bool):
                v = 'T' if v else 'F'
            opts.append(f'{k}={v}')

        args = [luna, '--overlap', '-o', out, '--options'] + opts
        _run_luna(args, '--overlap')

    return destrat(out)


__all__ = ['merge_edfs', 'bind_edfs', 'overlap']
