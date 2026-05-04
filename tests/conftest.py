"""Shared fixtures for lunapi tests.

Two fixture tracks:
  rec       — in-memory EDF (no file I/O, fast, function-scoped for isolation)
  sl / lp   — file-based sample-list workflow (session-scoped)
"""

import math
import struct
import pytest

SR = 256          # sample rate Hz
N_RECS = 4        # EDF records
REC_DUR = 30      # seconds per record
TOTAL_SAMP = SR * N_RECS * REC_DUR


def _sine(freq_hz, n, sr):
    return [math.sin(2 * math.pi * freq_hz * i / sr) * 200 for i in range(n)]


def _write_edf(path):
    """Write a minimal valid EDF with one EEG channel (10 Hz sine wave)."""
    ns = 1
    n_samp = SR * REC_DUR
    header_bytes = 256 + ns * 256

    def field(value, width):
        return str(value).ljust(width)[:width].encode("ascii")

    buf = bytearray()
    buf += field("0", 8)
    buf += field("X X X X", 80)
    buf += field("Startdate 01-JAN-2020 X X X", 80)
    buf += field("01.01.20", 8)
    buf += field("00.00.00", 8)
    buf += field(header_bytes, 8)
    buf += field("", 44)
    buf += field(N_RECS, 8)
    buf += field(REC_DUR, 8)
    buf += field(ns, 4)
    assert len(buf) == 256
    buf += field("EEG", 16)
    buf += field("", 80)
    buf += field("uV", 8)
    buf += field("-400", 8)
    buf += field("400", 8)
    buf += field("-32768", 8)
    buf += field("32767", 8)
    buf += field("", 80)
    buf += field(n_samp, 8)
    buf += field("", 32)
    assert len(buf) == header_bytes

    scale = 16000
    for r in range(N_RECS):
        off = r * n_samp
        samples = [int(scale * math.sin(2 * math.pi * 10 * (off + i) / SR))
                   for i in range(n_samp)]
        buf += struct.pack(f"<{n_samp}h", *samples)

    path.write_bytes(buf)


def _write_annot(path):
    path.write_text("W\t0\t30\nN1\t30\t60\nN2\t60\t90\nW\t90\t120\n")


def _write_sl(path, edf_path, annot_path):
    path.write_text(f"test_subject\t{edf_path}\t{annot_path}\n")


# ---------------------------------------------------------------------------
# Track 1: in-memory (no files)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def lp():
    from lunapi import proj
    return proj(verbose=False)


@pytest.fixture
def rec(lp):
    """Fresh in-memory EDF instance per test: one EEG channel, 10 Hz sine."""
    r = lp.empty_inst("test", nr=N_RECS, rs=REC_DUR)
    r.insert_signal("EEG", _sine(10, TOTAL_SAMP, SR), SR)
    return r


@pytest.fixture
def rec_annot(lp):
    """Fresh in-memory EDF with EEG signal and sleep-stage annotations."""
    r = lp.empty_inst("test", nr=N_RECS, rs=REC_DUR)
    r.insert_signal("EEG", _sine(10, TOTAL_SAMP, SR), SR)
    r.insert_annot("W",  [(0, 30), (90, 120)])
    r.insert_annot("N1", [(30, 60)])
    r.insert_annot("N2", [(60, 90)])
    return r


# ---------------------------------------------------------------------------
# Track 2: file-based sample list
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tmp_edf(tmp_path_factory):
    p = tmp_path_factory.mktemp("edf") / "test.edf"
    _write_edf(p)
    return p


@pytest.fixture(scope="session")
def tmp_annot(tmp_path_factory):
    p = tmp_path_factory.mktemp("annot") / "test.annot"
    _write_annot(p)
    return p


@pytest.fixture(scope="session")
def tmp_sl(tmp_path_factory, tmp_edf, tmp_annot):
    p = tmp_path_factory.mktemp("sl") / "study.lst"
    _write_sl(p, tmp_edf, tmp_annot)
    return p
