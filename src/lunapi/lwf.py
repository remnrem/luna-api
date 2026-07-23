#    --------------------------------------------------------------------
#
#    This file is part of Luna.
#
#    LUNA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    LUNA is distributed in the hope that it will be useful,
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

"""Reader for Luna's .lwf (Luna Waveform) binary format.

Public functions
----------------
lwf_summary(paths, *, recur=False) -> pd.DataFrame
    Scan one or more .lwf files and return a per-file summary without loading
    any signal data.

read_lwf(paths, *, recur=False) -> LWFResult
    Load one or more .lwf files into a single result object containing a numpy
    array of signal data, a per-event metadata DataFrame, and a per-channel
    metadata DataFrame.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Iterable, NamedTuple, Union

import numpy as np
import pandas as pd

_LWF_MAGIC   = b"LWF1"
_LWF_VERSION = 3

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class LWFResult(NamedTuple):
    """Return value of :func:`read_lwf`.

    Attributes
    ----------
    data : np.ndarray, shape (n_waves, n_channels, n_samples)
        Signal data decoded to physical units (µV etc.).  When the file was
        written with ``annot-ch-match=T``, ``n_channels`` is 1 and the
        detecting channel for each event is in ``meta['annot_ch']``.
    meta : pd.DataFrame, shape (n_waves, ...)
        Per-event metadata columns: ``id``, ``tag``, ``file``, ``annot``,
        ``instance``, ``annot_ch``, ``meta``, ``anchor_sec``,
        ``annot_start_sec``, ``annot_stop_sec``, ``wave_start_sec``,
        ``wave_stop_sec``.
    channels : pd.DataFrame, shape (n_channels, ...)
        Per-channel metadata: ``label``, ``unit``, ``sr``, ``phys_min``,
        ``phys_max``.  In annot-ch-match mode this has a single placeholder
        row; consult ``meta['annot_ch']`` for the actual channel per event.
    attrs : dict
        File-level attributes: ``sfreq``, ``align``, ``source_files``,
        ``annot_ch_match``.
    """
    data:     np.ndarray
    meta:     pd.DataFrame
    channels: pd.DataFrame
    attrs:    dict


# ---------------------------------------------------------------------------
# Binary primitives
# ---------------------------------------------------------------------------

def _ru32(f) -> int:
    return struct.unpack('<I', f.read(4))[0]

def _ri32(f) -> int:
    return struct.unpack('<i', f.read(4))[0]

def _ru64(f) -> int:
    return struct.unpack('<Q', f.read(8))[0]

def _rf64(f) -> float:
    return struct.unpack('<d', f.read(8))[0]

def _rstr(f) -> str:
    n = _ru32(f)
    return f.read(n).decode('utf-8') if n else ''

def _decode_int16(raw: bytes, phys_min: float, phys_max: float) -> np.ndarray:
    digital = np.frombuffer(raw, dtype='<i2').astype(np.float64)
    return (digital + 32768.0) * (phys_max - phys_min) / 65535.0 + phys_min


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _resolve(paths: Union[str, Path, Iterable], recur: bool) -> list[Path]:
    if isinstance(paths, (str, Path)):
        paths = [paths]
    out: list[Path] = []
    for p in paths:
        p = Path(p).expanduser()
        if p.is_dir():
            out.extend(sorted(p.glob('**/*.lwf' if recur else '*.lwf')))
        else:
            out.append(p)
    if not out:
        raise ValueError("no .lwf files found")
    return out


# ---------------------------------------------------------------------------
# Header reader
# ---------------------------------------------------------------------------

def _read_header(f) -> dict:
    magic = f.read(4)
    if magic != _LWF_MAGIC:
        raise ValueError(f"not a valid .lwf file (bad magic: {magic!r})")
    version = _ri32(f)
    if version != _LWF_VERSION:
        raise ValueError(f"unsupported .lwf version {version} (expected {_LWF_VERSION})")

    id_  = _rstr(f)
    _rstr(f)              # edf path
    _rstr(f)              # stored output filename
    startdate = _rstr(f)
    starttime = _rstr(f)
    tag   = _rstr(f)
    align = _rstr(f)

    n_annots = _ri32(f)
    annots = [_rstr(f) for _ in range(n_annots)]

    n_ch = _ri32(f)
    channels = []
    for _ in range(n_ch):
        label    = _rstr(f)
        unit     = _rstr(f)
        _ru64(f)           # sample_step_tp
        sr       = _rf64(f)
        phys_min = _rf64(f)
        phys_max = _rf64(f)
        channels.append({'label': label, 'unit': unit, 'sr': sr,
                         'phys_min': phys_min, 'phys_max': phys_max})

    n_features = _ri32(f)
    feature_names = [_rstr(f) for _ in range(n_features)]
    n_waves = _ri32(f)

    return {
        'id': id_, 'startdate': startdate, 'starttime': starttime,
        'tag': tag, 'align': align, 'annots': annots,
        'channels': channels, 'feature_names': feature_names,
        'n_waves': n_waves,
    }


# ---------------------------------------------------------------------------
# Events reader (index then payload, single sequential pass)
# ---------------------------------------------------------------------------

def _read_events(f, header: dict):
    n_waves    = header['n_waves']
    n_ch       = len(header['channels'])
    n_features = len(header['feature_names'])
    ch_phys    = {c['label']: (c['phys_min'], c['phys_max'])
                  for c in header['channels']}

    # --- index pass ---
    index_rows: list[dict] = []
    expected_n: int | None = None
    annot_ch_match = False

    for w in range(n_waves):
        annot    = _rstr(f)
        instance = _rstr(f)
        annot_ch = _rstr(f)
        annot_start = _rf64(f)
        annot_stop  = _rf64(f)
        anchor      = _rf64(f)
        wave_start  = _rf64(f)
        wave_stop   = _rf64(f)
        _ru64(f)              # payload_offset

        n_blocks = _ri32(f)
        if n_blocks < n_ch:
            annot_ch_match = True

        ns_list: list[int] = []
        for _ in range(n_blocks):
            ns = _ri32(f)
            _rf64(f)          # data_start_sec
            _rf64(f)          # data_stop_sec
            ns_list.append(ns)

        ns = ns_list[0] if ns_list else 0
        if expected_n is None:
            expected_n = ns
        elif ns != expected_n:
            raise ValueError(
                f"event {w}: non-uniform waveform length "
                f"({ns} samples, expected {expected_n})"
            )

        index_rows.append({
            'annot': annot, 'instance': instance, 'annot_ch': annot_ch,
            'annot_start_sec': annot_start, 'annot_stop_sec': annot_stop,
            'anchor_sec': anchor, 'wave_start_sec': wave_start,
            'wave_stop_sec': wave_stop, 'n_blocks': n_blocks,
        })

    if expected_n is None:
        expected_n = 0

    # --- payload pass ---
    out_n_ch = 1 if annot_ch_match else n_ch
    data = np.full((n_waves, out_n_ch, expected_n), np.nan, dtype=np.float64)
    meta_col: list[str] = []

    for w in range(n_waves):
        meta_col.append(_rstr(f))
        n_blocks = _ri32(f)

        for b in range(n_blocks):
            if n_features > 0:
                f.read(4 + n_features * 8)   # feature_qc + feature values

            raw = f.read(expected_n * 2)      # int16

            if annot_ch_match:
                label = index_rows[w]['annot_ch']
            else:
                label = header['channels'][b]['label']

            phys_min, phys_max = ch_phys.get(label, (0.0, 1.0))
            data[w, b, :] = _decode_int16(raw, phys_min, phys_max)

    event_meta = pd.DataFrame(index_rows).drop(columns=['n_blocks'])
    event_meta['meta'] = meta_col
    return data, event_meta, annot_ch_match


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lwf_summary(
    paths: Union[str, Path, Iterable],
    *,
    recur: bool = False,
) -> pd.DataFrame:
    """Summarise one or more .lwf files without loading signal data.

    Parameters
    ----------
    paths:
        A .lwf file, a directory, or a list of either.
    recur:
        Recurse into subdirectories when *paths* is a directory.

    Returns
    -------
    pd.DataFrame with one row per file and columns:
    ``file``, ``id``, ``tag``, ``startdate``, ``starttime``, ``align``,
    ``annots``, ``n_waves``, ``n_channels``, ``channels``, ``srs``,
    ``n_features``.
    """
    rows = []
    for p in _resolve(paths, recur):
        with open(p, 'rb') as f:
            h = _read_header(f)
        rows.append({
            'file':       str(p),
            'id':         h['id'],
            'tag':        h['tag'],
            'startdate':  h['startdate'],
            'starttime':  h['starttime'],
            'align':      h['align'],
            'annots':     ','.join(h['annots']),
            'n_waves':    h['n_waves'],
            'n_channels': len(h['channels']),
            'channels':   ','.join(c['label'] for c in h['channels']),
            'srs':        ','.join(str(c['sr'])  for c in h['channels']),
            'n_features': len(h['feature_names']),
        })
    return pd.DataFrame(rows)


def read_lwf(
    paths: Union[str, Path, Iterable],
    *,
    recur: bool = False,
) -> LWFResult:
    """Load one or more .lwf files into an :class:`LWFResult`.

    All files must share the same channel labels and sample rates.
    All waveform events must have the same number of samples.

    Parameters
    ----------
    paths:
        A .lwf file, a directory, or a list of either.
    recur:
        Recurse into subdirectories when *paths* is a directory.

    Returns
    -------
    LWFResult
        Named tuple with fields ``data``, ``meta``, ``channels``, ``attrs``.
        ``data`` has shape ``(n_waves, n_channels, n_samples)`` with values
        in physical units.  When written with ``annot-ch-match=T``,
        ``n_channels`` is 1 and each event's channel is in
        ``meta['annot_ch']``.
    """
    files = _resolve(paths, recur)

    headers: list[dict] = []
    for p in files:
        with open(p, 'rb') as f:
            h = _read_header(f)
        h['_path'] = p
        headers.append(h)

    ref_ch  = headers[0]['channels']
    ref_sig = [(c['label'], c['sr']) for c in ref_ch]
    for h in headers[1:]:
        sig = [(c['label'], c['sr']) for c in h['channels']]
        if sig != ref_sig:
            raise ValueError(
                f"channel mismatch between files:\n"
                f"  {headers[0]['_path']}: {ref_sig}\n"
                f"  {h['_path']}: {sig}"
            )

    all_srs = [c['sr'] for c in ref_ch]
    if len(set(all_srs)) > 1:
        raise ValueError(f"channels have mixed sample rates: {all_srs}")
    sr = all_srs[0]

    all_data: list[np.ndarray] = []
    all_meta: list[pd.DataFrame] = []
    expected_n: int | None = None
    detected_annot_ch_match: bool | None = None

    for h in headers:
        with open(h['_path'], 'rb') as f:
            _read_header(f)
            data, event_meta, annot_ch_match = _read_events(f, h)

        if detected_annot_ch_match is None:
            detected_annot_ch_match = annot_ch_match
        elif annot_ch_match != detected_annot_ch_match:
            raise ValueError(
                f"mixed annot-ch-match modes across files: {h['_path']}"
            )

        ns = data.shape[2]
        if expected_n is None:
            expected_n = ns
        elif ns != expected_n:
            raise ValueError(
                f"sample count mismatch: expected {expected_n}, "
                f"got {ns} in {h['_path']}"
            )

        event_meta.insert(0, 'file', str(h['_path']))
        event_meta.insert(0, 'tag',  h['tag'])
        event_meta.insert(0, 'id',   h['id'])
        all_data.append(data)
        all_meta.append(event_meta)

    if expected_n is None:
        expected_n = 0
    if detected_annot_ch_match is None:
        detected_annot_ch_match = False

    data = np.concatenate(all_data, axis=0)
    meta = pd.concat(all_meta, ignore_index=True)

    col_order = [
        'id', 'tag', 'file',
        'annot', 'instance', 'annot_ch', 'meta',
        'anchor_sec', 'annot_start_sec', 'annot_stop_sec',
        'wave_start_sec', 'wave_stop_sec',
    ]
    meta = meta[col_order].reset_index(drop=True)

    channels = pd.DataFrame(ref_ch)

    attrs = {
        'sfreq':          sr,
        'align':          headers[0]['align'],
        'source_files':   [str(h['_path']) for h in headers],
        'annot_ch_match': detected_annot_ch_match,
    }

    return LWFResult(data=data, meta=meta, channels=channels, attrs=attrs)
