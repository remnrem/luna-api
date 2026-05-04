"""Tests for viz.py helpers — pure Python, no C++ extension required."""

import pytest
import numpy as np
import pandas as pd

from lunapi.viz import stgcol, stgn, default_xy


# ---------------------------------------------------------------------------
# stgcol
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage,expected", [
    ("N1", "#00BEFAFF"),
    ("N2", "#0050C8FF"),
    ("N3", "#000050FF"),
    ("R",  "#FA1432FF"),
    ("W",  "#31AD52FF"),
    ("?",  "#64646464"),
])
def test_stgcol_known_stages(stage, expected):
    assert stgcol([stage]) == [expected]


def test_stgcol_unknown_passthrough():
    assert stgcol(["UNKNOWN"]) == ["UNKNOWN"]


def test_stgcol_none():
    assert stgcol([None]) == ["#00000000"]


def test_stgcol_sequence():
    result = stgcol(["W", "N2", "R"])
    assert len(result) == 3
    assert all(isinstance(c, str) for c in result)


# ---------------------------------------------------------------------------
# stgn
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage,expected", [
    ("N1", -1),
    ("N2", -2),
    ("N3", -3),
    ("R",   0),
    ("W",   1),
    ("?",   2),
    ("L",   2),
])
def test_stgn_known_stages(stage, expected):
    assert stgn([stage]) == [expected]


def test_stgn_unknown_passthrough():
    assert stgn(["DEEP"]) == ["DEEP"]


def test_stgn_none():
    assert stgn([None]) == [2]


def test_stgn_sequence_length():
    result = stgn(["W", "N1", "N2", "N3", "R"])
    assert len(result) == 5


# ---------------------------------------------------------------------------
# default_xy
# ---------------------------------------------------------------------------

def test_default_xy_returns_dataframe():
    df = default_xy()
    assert isinstance(df, pd.DataFrame)


def test_default_xy_columns():
    df = default_xy()
    assert list(df.columns) == ["CH", "X", "Y"]


def test_default_xy_row_count():
    df = default_xy()
    assert len(df) == 64


def test_default_xy_numeric_coordinates():
    df = default_xy()
    assert pd.api.types.is_float_dtype(df["X"])
    assert pd.api.types.is_float_dtype(df["Y"])


def test_default_xy_coordinates_in_range():
    df = default_xy()
    assert df["X"].between(-1, 1).all()
    assert df["Y"].between(-1, 1).all()


def test_default_xy_no_duplicate_channels():
    df = default_xy()
    assert df["CH"].nunique() == len(df)
