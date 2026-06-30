"""Tests for lunapi.lwf — .lwf reader (int16 format, phys_min/max in header)."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lunapi.lwf import LWFResult, _read_header, lwf_summary, read_lwf

# ---------------------------------------------------------------------------
# Synthetic .lwf writer (mirrors the C++ write_* functions)
# ---------------------------------------------------------------------------

_MAGIC   = b"LWF1"
_VERSION = 3

def _wu32(v):  return struct.pack('<I', v)
def _wi32(v):  return struct.pack('<i', v)
def _wu64(v):  return struct.pack('<Q', v)
def _wf64(v):  return struct.pack('<d', v)
def _wstr(s):
    b = s.encode('utf-8')
    return _wu32(len(b)) + b

def _encode_int16(values: np.ndarray, phys_min: float, phys_max: float) -> bytes:
    gain   = 65535.0 / (phys_max - phys_min) if phys_max != phys_min else 1.0
    offset = -32768.0 - gain * phys_min
    dv = np.clip(np.round(gain * np.asarray(values, dtype=np.float64) + offset),
                 -32768, 32767).astype(np.int16)
    return dv.tobytes()


def make_lwf(
    path: Path,
    *,
    id_: str = "TEST01",
    tag: str = "test",
    align: str = "mid",
    annots: list | None = None,
    channels: list | None = None,
    waves: list | None = None,
) -> None:
    annots   = annots   or ["SO_neg_pk"]
    channels = channels or [{'label': 'CZ', 'unit': 'uV', 'sr': 128.0,
                              'phys_min': -200.0, 'phys_max': 200.0}]
    waves    = waves    or []

    n_ch = len(channels)
    sample_step_tp = int(round(1e9 / channels[0]['sr']))

    hdr = (
        _MAGIC + _wi32(_VERSION)
        + _wstr(id_) + _wstr("test.edf") + _wstr(str(path))
        + _wstr("01.01.24") + _wstr("00.00.00")
        + _wstr(tag) + _wstr(align)
    )
    hdr += _wi32(len(annots))
    for a in annots:
        hdr += _wstr(a)
    hdr += _wi32(n_ch)
    for ch in channels:
        hdr += (_wstr(ch['label']) + _wstr(ch['unit'])
                + _wu64(sample_step_tp) + _wf64(ch['sr'])
                + _wf64(ch['phys_min']) + _wf64(ch['phys_max']))
    hdr += _wi32(0) + _wi32(len(waves))   # n_features=0, n_waves

    ch_map = {c['label']: c for c in channels}

    # build payload first to compute sizes for offsets
    payloads: list[bytes] = []
    for w in waves:
        p = _wstr(w.get('meta', '')) + _wi32(len(w['blocks']))
        for blk in w['blocks']:
            ch = ch_map[blk['label']]
            p += _encode_int16(blk['values'], ch['phys_min'], ch['phys_max'])
        payloads.append(p)

    # index with real payload offsets
    index = b""
    payload_base = len(hdr)
    # placeholder pass to compute index size
    for w in waves:
        index += (_wstr(w['annot']) + _wstr(w.get('instance', '.'))
                  + _wstr(w.get('annot_ch', '.'))
                  + _wf64(w.get('annot_start_sec', 0.0))
                  + _wf64(w.get('annot_stop_sec',  0.0))
                  + _wf64(w.get('anchor_sec',       0.0))
                  + _wf64(w.get('wave_start_sec',  -1.5))
                  + _wf64(w.get('wave_stop_sec',    1.5))
                  + _wu64(0) + _wi32(len(w['blocks'])))
        for blk in w['blocks']:
            index += _wi32(len(blk['values'])) + _wf64(-1.5) + _wf64(1.5)

    index_size = len(index)
    running = payload_base + index_size

    index = b""
    for i, w in enumerate(waves):
        index += (_wstr(w['annot']) + _wstr(w.get('instance', '.'))
                  + _wstr(w.get('annot_ch', '.'))
                  + _wf64(w.get('annot_start_sec', 0.0))
                  + _wf64(w.get('annot_stop_sec',  0.0))
                  + _wf64(w.get('anchor_sec',       0.0))
                  + _wf64(w.get('wave_start_sec',  -1.5))
                  + _wf64(w.get('wave_stop_sec',    1.5))
                  + _wu64(running) + _wi32(len(w['blocks'])))
        for blk in w['blocks']:
            index += _wi32(len(blk['values'])) + _wf64(-1.5) + _wf64(1.5)
        running += len(payloads[i])

    path.write_bytes(hdr + index + b"".join(payloads))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SR     = 128.0
N_SAMP = 384   # 3 s at 128 Hz

def _wave(amp: float = 50.0, rng=None) -> np.ndarray:
    t = np.linspace(-1.5, 1.5, N_SAMP, endpoint=False)
    w = amp * np.sin(2 * np.pi * t)
    if rng is not None:
        w += rng.normal(0, 5, N_SAMP)
    return w


@pytest.fixture
def two_ch_file(tmp_path) -> Path:
    """Standard mode: 4 waves × 2 channels."""
    rng = np.random.default_rng(0)
    channels = [
        {'label': 'CZ', 'unit': 'uV', 'sr': SR, 'phys_min': -200.0, 'phys_max': 200.0},
        {'label': 'FZ', 'unit': 'uV', 'sr': SR, 'phys_min': -200.0, 'phys_max': 200.0},
    ]
    waves = [
        {'annot': 'SO_neg_pk', 'instance': '.', 'annot_ch': '.',
         'anchor_sec': 100.0 + i * 10,
         'wave_start_sec': 98.5 + i * 10, 'wave_stop_sec': 101.5 + i * 10,
         'meta': f'm{i}',
         'blocks': [{'label': 'CZ', 'values': _wave(rng=rng)},
                    {'label': 'FZ', 'values': _wave(amp=30.0, rng=rng)}]}
        for i in range(4)
    ]
    p = tmp_path / "std.lwf"
    make_lwf(p, channels=channels, waves=waves)
    return p


@pytest.fixture
def annot_ch_file(tmp_path) -> Path:
    """annot-ch-match mode: 6 waves × 1 block (alternating CZ/FZ)."""
    rng = np.random.default_rng(1)
    channels = [
        {'label': 'CZ', 'unit': 'uV', 'sr': SR, 'phys_min': -200.0, 'phys_max': 200.0},
        {'label': 'FZ', 'unit': 'uV', 'sr': SR, 'phys_min': -200.0, 'phys_max': 200.0},
    ]
    waves = []
    for i in range(6):
        ch = 'CZ' if i % 2 == 0 else 'FZ'
        waves.append({
            'annot': 'SO_neg_pk', 'instance': '.', 'annot_ch': ch,
            'anchor_sec': 100.0 + i * 10,
            'wave_start_sec': 98.5 + i * 10, 'wave_stop_sec': 101.5 + i * 10,
            'meta': f'w{i}',
            'blocks': [{'label': ch, 'values': _wave(rng=rng)}],
        })
    p = tmp_path / "acm.lwf"
    make_lwf(p, channels=channels, waves=waves)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReadHeader:
    def test_phys_min_max(self, two_ch_file):
        with open(two_ch_file, 'rb') as f:
            h = _read_header(f)
        cz = next(c for c in h['channels'] if c['label'] == 'CZ')
        assert cz['phys_min'] == pytest.approx(-200.0)
        assert cz['phys_max'] == pytest.approx(200.0)

    def test_n_channels(self, two_ch_file):
        with open(two_ch_file, 'rb') as f:
            h = _read_header(f)
        assert len(h['channels']) == 2

    def test_bad_magic(self, tmp_path):
        p = tmp_path / "bad.lwf"
        p.write_bytes(b"XXXX" + b"\x00" * 100)
        with open(p, 'rb') as f:
            with pytest.raises(ValueError, match="bad magic"):
                _read_header(f)

    def test_bad_version(self, tmp_path):
        p = tmp_path / "ver.lwf"
        p.write_bytes(b"LWF1" + struct.pack('<i', 99) + b"\x00" * 100)
        with open(p, 'rb') as f:
            with pytest.raises(ValueError, match="version"):
                _read_header(f)


class TestLwfSummary:
    def test_returns_dataframe(self, two_ch_file):
        df = lwf_summary(two_ch_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_n_waves(self, two_ch_file):
        df = lwf_summary(two_ch_file)
        assert df['n_waves'].iloc[0] == 4

    def test_channels_field(self, two_ch_file):
        df = lwf_summary(two_ch_file)
        assert df['channels'].iloc[0] == 'CZ,FZ'

    def test_directory_scan(self, tmp_path, two_ch_file, annot_ch_file):
        df = lwf_summary(tmp_path)
        assert len(df) == 2

    def test_no_data_allocated(self, two_ch_file):
        # summary should be fast; just check it doesn't return a data array
        result = lwf_summary(two_ch_file)
        assert 'data' not in result.columns


class TestReadLwfStandard:
    def test_returns_lwfresult(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert isinstance(r, LWFResult)

    def test_data_shape(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert r.data.shape == (4, 2, N_SAMP)

    def test_channels_df(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert list(r.channels['label']) == ['CZ', 'FZ']

    def test_meta_columns(self, two_ch_file):
        r = read_lwf(two_ch_file)
        for col in ('id', 'tag', 'annot', 'annot_ch', 'anchor_sec',
                    'wave_start_sec', 'meta'):
            assert col in r.meta.columns

    def test_meta_length(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert len(r.meta) == 4

    def test_meta_preserved(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert list(r.meta['meta']) == ['m0', 'm1', 'm2', 'm3']

    def test_not_annot_ch_match(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert r.attrs['annot_ch_match'] is False

    def test_sfreq_attr(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert r.attrs['sfreq'] == pytest.approx(SR)

    def test_values_finite(self, two_ch_file):
        r = read_lwf(two_ch_file)
        assert np.all(np.isfinite(r.data))

    def test_int16_precision(self, tmp_path):
        phys_min, phys_max = -100.0, 100.0
        rng = np.random.default_rng(42)
        orig = rng.uniform(phys_min, phys_max, N_SAMP)
        channels = [{'label': 'CZ', 'unit': 'uV', 'sr': SR,
                     'phys_min': phys_min, 'phys_max': phys_max}]
        waves = [{'annot': 'SO_neg_pk', 'instance': '.', 'annot_ch': '.',
                  'anchor_sec': 0.0, 'wave_start_sec': -1.5, 'wave_stop_sec': 1.5,
                  'meta': '', 'blocks': [{'label': 'CZ', 'values': orig}]}]
        p = tmp_path / "prec.lwf"
        make_lwf(p, channels=channels, waves=waves)
        r = read_lwf(p)
        lsb = (phys_max - phys_min) / 65535.0
        assert np.max(np.abs(r.data[0, 0, :] - orig)) <= lsb + 1e-9

    def test_multi_file_concat(self, tmp_path):
        channels = [{'label': 'CZ', 'unit': 'uV', 'sr': SR,
                     'phys_min': -200.0, 'phys_max': 200.0}]
        rng = np.random.default_rng(3)
        for name, n in [("a.lwf", 3), ("b.lwf", 5)]:
            waves = [{'annot': 'SO_neg_pk', 'instance': '.', 'annot_ch': '.',
                      'anchor_sec': float(i), 'wave_start_sec': float(i) - 1.5,
                      'wave_stop_sec': float(i) + 1.5, 'meta': '',
                      'blocks': [{'label': 'CZ', 'values': rng.normal(0, 50, N_SAMP)}]}
                     for i in range(n)]
            make_lwf(tmp_path / name, channels=channels, waves=waves)
        r = read_lwf(tmp_path)
        assert r.data.shape == (8, 1, N_SAMP)
        assert len(r.meta) == 8
        assert len(r.attrs['source_files']) == 2

    def test_channel_mismatch_raises(self, tmp_path):
        for name, label in [("x.lwf", "CZ"), ("y.lwf", "FZ")]:
            ch = [{'label': label, 'unit': 'uV', 'sr': SR,
                   'phys_min': -200.0, 'phys_max': 200.0}]
            waves = [{'annot': 'A', 'instance': '.', 'annot_ch': '.',
                      'anchor_sec': 0.0, 'wave_start_sec': -1.5,
                      'wave_stop_sec': 1.5, 'meta': '',
                      'blocks': [{'label': label,
                                  'values': np.zeros(N_SAMP)}]}]
            make_lwf(tmp_path / name, channels=ch, waves=waves)
        with pytest.raises(ValueError, match="channel mismatch"):
            read_lwf(tmp_path)


class TestReadLwfAnnotChMatch:
    def test_shape(self, annot_ch_file):
        r = read_lwf(annot_ch_file)
        assert r.data.shape == (6, 1, N_SAMP)

    def test_annot_ch_match_flag(self, annot_ch_file):
        r = read_lwf(annot_ch_file)
        assert r.attrs['annot_ch_match'] is True

    def test_annot_ch_per_event(self, annot_ch_file):
        r = read_lwf(annot_ch_file)
        assert list(r.meta['annot_ch']) == ['CZ', 'FZ', 'CZ', 'FZ', 'CZ', 'FZ']

    def test_meta_preserved(self, annot_ch_file):
        r = read_lwf(annot_ch_file)
        assert list(r.meta['meta']) == [f'w{i}' for i in range(6)]

    def test_values_finite(self, annot_ch_file):
        r = read_lwf(annot_ch_file)
        assert np.all(np.isfinite(r.data))

    def test_per_channel_phys_decode(self, tmp_path):
        """CZ and FZ have different physical ranges; decode must use each channel's own."""
        channels = [
            {'label': 'CZ', 'unit': 'uV', 'sr': SR, 'phys_min': -100.0, 'phys_max': 100.0},
            {'label': 'FZ', 'unit': 'uV', 'sr': SR, 'phys_min': -500.0, 'phys_max': 500.0},
        ]
        waves = [
            {'annot': 'SO_neg_pk', 'instance': '.', 'annot_ch': 'CZ',
             'anchor_sec': 0.0, 'wave_start_sec': -1.5, 'wave_stop_sec': 1.5,
             'meta': '', 'blocks': [{'label': 'CZ', 'values': np.full(N_SAMP, 80.0)}]},
            {'annot': 'SO_neg_pk', 'instance': '.', 'annot_ch': 'FZ',
             'anchor_sec': 10.0, 'wave_start_sec': 8.5, 'wave_stop_sec': 11.5,
             'meta': '', 'blocks': [{'label': 'FZ', 'values': np.full(N_SAMP, -400.0)}]},
        ]
        p = tmp_path / "phys.lwf"
        make_lwf(p, channels=channels, waves=waves)
        r = read_lwf(p)
        assert np.max(np.abs(r.data[0, 0, :] -    80.0)) <= 200.0  / 65535.0 + 1e-9
        assert np.max(np.abs(r.data[1, 0, :] - (-400.0))) <= 1000.0 / 65535.0 + 1e-9
