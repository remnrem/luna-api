"""Tests for gpa.py pure-Python helpers — no C++ extension required."""

import pytest
import pandas as pd

from lunapi.gpa import _parse_tsv, _join


# ---------------------------------------------------------------------------
# _parse_tsv
# ---------------------------------------------------------------------------

def test_parse_tsv_basic():
    text = "A\tB\tC\n1\t2\t3\n4\t5\t6"
    df = _parse_tsv(text)
    assert list(df.columns) == ["A", "B", "C"]
    assert len(df) == 2
    assert df.iloc[0]["A"] == "1"


def test_parse_tsv_empty():
    df = _parse_tsv("")
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_parse_tsv_single_row():
    text = "ID\tVAL\ns1\t99"
    df = _parse_tsv(text)
    assert len(df) == 1
    assert df.iloc[0]["VAL"] == "99"


# ---------------------------------------------------------------------------
# _join
# ---------------------------------------------------------------------------

def test_join_list():
    assert _join(["a", "b", "c"]) == "a,b,c"


def test_join_single_string():
    assert _join("EEG") == "EEG"


def test_join_none():
    assert _join(None) is None


def test_join_empty_list():
    assert _join([]) == ""
