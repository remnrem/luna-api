"""Core lunapi workflow tests.

Tests the primary use-case chain:
  create instance → inspect headers/channels → attach annotations →
  run proc()/eval() → retrieve output tables → extract signal data

Uses two fixture tracks:
  rec / rec_annot  — in-memory EDF, no file I/O required
  lp + tmp_sl      — file-based sample-list workflow
"""

import pytest
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Channel / header inspection
# ---------------------------------------------------------------------------

def test_chs_returns_dataframe(rec):
    chs = rec.chs()
    assert isinstance(chs, pd.DataFrame)


def test_chs_contains_eeg(rec):
    assert "EEG" in rec.chs()["Channels"].values


def test_stat_returns_dataframe(rec):
    df = rec.stat()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_headers_command(rec):
    result = rec.proc("HEADERS")
    assert "HEADERS: CH" in result
    df = result["HEADERS: CH"]
    assert "CH" in df.columns
    assert "EEG" in df["CH"].values


def test_headers_sample_rate(rec):
    result = rec.proc("HEADERS")
    df = result["HEADERS: CH"]
    sr = float(df.loc[df["CH"] == "EEG", "SR"].iloc[0])
    assert sr == 256.0


# ---------------------------------------------------------------------------
# Luna command execution and output tables
# ---------------------------------------------------------------------------

def test_proc_returns_dict(rec):
    result = rec.proc("HEADERS")
    assert isinstance(result, dict)
    assert len(result) > 0


def test_psd_via_proc(rec):
    result = rec.proc("EPOCH len=30\nPSD sig=EEG dB=T spectrum=T")
    assert "PSD: CH_F" in result
    df = result["PSD: CH_F"]
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "PSD" in df.columns


def test_psd_has_10hz_peak(rec):
    result = rec.proc("EPOCH len=30\nPSD sig=EEG dB=T spectrum=T")
    df = result["PSD: CH_F"]
    df["F"]   = pd.to_numeric(df["F"])
    df["PSD"] = pd.to_numeric(df["PSD"])
    peak_f = float(df.loc[df["PSD"].idxmax(), "F"])
    # Fixture signal is a 10 Hz sine — PSD peak should be exactly 10 Hz
    assert abs(peak_f - 10.0) < 0.5


def test_eval_and_table(rec):
    rec.eval("EPOCH len=30\nPSD sig=EEG dB=T spectrum=T")
    df = rec.table("PSD", "CH_F")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "PSD" in df.columns


def test_epoch_command(rec):
    result = rec.proc("EPOCH len=30")
    assert any("EPOCH" in k for k in result)


# ---------------------------------------------------------------------------
# Raw signal extraction
# ---------------------------------------------------------------------------

def test_data_extraction_shape(rec):
    cols, matrix = rec.data(["EEG"])
    assert "EEG" in cols
    arr = np.asarray(matrix)
    assert arr.ndim == 2
    assert arr.shape[0] > 0   # samples
    assert arr.shape[1] == 1  # one channel


def test_data_is_finite(rec):
    cols, matrix = rec.data(["EEG"])
    assert np.isfinite(np.asarray(matrix, dtype=float)).all()


# ---------------------------------------------------------------------------
# Annotation workflow
# ---------------------------------------------------------------------------

def test_annots_dataframe(rec_annot):
    anns = rec_annot.annots()
    assert isinstance(anns, pd.DataFrame)
    assert not anns.empty


def test_annot_classes(rec_annot):
    classes = set(rec_annot.annots()["Annotations"].values)
    assert {"W", "N1", "N2"}.issubset(classes)


def test_fetch_annots_intervals(rec_annot):
    df = rec_annot.fetch_annots("W")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert set(df.columns) >= {"Class", "Start", "Stop"}
    assert (df["Class"] == "W").all()
    assert len(df) == 2   # W appears at 0-30 and 90-120


def test_fetch_annots_timing(rec_annot):
    df = rec_annot.fetch_annots("N2")
    row = df.iloc[0]
    assert float(row["Start"]) == pytest.approx(60.0)
    assert float(row["Stop"])  == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# File-based sample-list workflow
# ---------------------------------------------------------------------------

def test_sample_list_loads(lp, tmp_sl):
    lp.sample_list(str(tmp_sl))
    sl = lp.sample_list()
    assert isinstance(sl, pd.DataFrame)
    assert len(sl) == 1
    assert sl.iloc[0]["ID"] == "test_subject"


def test_proj_inst_from_sample_list(lp, tmp_sl):
    lp.sample_list(str(tmp_sl))
    rec = lp.inst(1)
    assert rec is not None
    assert "EEG" in rec.chs()["Channels"].values


def test_proj_proc_across_cohort(lp, tmp_sl):
    lp.sample_list(str(tmp_sl))
    results = lp.proc("HEADERS")
    assert isinstance(results, dict)
    assert any("HEADERS" in k for k in results)
