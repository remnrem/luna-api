import pandas as pd
from pandas.api.types import is_numeric_dtype

from lunapi.destrat import _maybe_numeric


def test_maybe_numeric_converts_numeric_text_and_missing_markers():
    result = _maybe_numeric(pd.Series(["0.5", "10", " NA ", "NaN", None]))

    assert is_numeric_dtype(result.dtype)
    assert result.iloc[0] == 0.5
    assert result.iloc[1] == 10
    assert result.iloc[2:].isna().all()


def test_maybe_numeric_preserves_column_with_non_numeric_text():
    source = pd.Series(["1", "C3", "NA"])

    result = _maybe_numeric(source)

    pd.testing.assert_series_equal(result, source)


def test_maybe_numeric_keeps_existing_numeric_column_numeric():
    source = pd.Series([1.0, 2.5, float("nan")])

    result = _maybe_numeric(source)

    pd.testing.assert_series_equal(result, source)
