"""Validation tests.

The point of this layer is that bad data fails loudly instead of quietly
becoming a wrong indicator, a wrong signal, and a backtest edge that never
existed.
"""

from datetime import date

import pandas as pd
import pytest

from screener.validate.rules import Severity, validate_bars


def _bars(rows, start="2024-01-02"):
    idx = pd.to_datetime([r[0] for r in rows]) if isinstance(rows[0][0], str) else None
    data = [r[1:] if idx is not None else r for r in rows]
    if idx is None:
        idx = pd.date_range(start, periods=len(rows), freq="B")
    return pd.DataFrame(
        data, columns=["open", "high", "low", "close", "volume"], index=idx
    ).astype(float)


GOOD = [
    [100, 105, 98, 103, 1_000_000],
    [103, 108, 102, 107, 1_200_000],
    [107, 110, 104, 105, 900_000],
]


def test_clean_data_produces_no_violations():
    report = validate_bars("SPY", _bars(GOOD))
    assert report.violations == []
    assert report.is_usable


def test_empty_frame_is_an_error_not_a_silent_pass():
    report = validate_bars("SPY", _bars(GOOD).iloc[:0])
    assert not report.is_usable
    assert report.errors[0].rule == "empty_frame"


def test_negative_price_is_quarantined():
    rows = [*GOOD, [105, 108, -1, 106, 500_000]]
    report = validate_bars("SPY", _bars(rows))
    assert not report.is_usable
    assert any(v.rule == "positive_prices" for v in report.errors)
    assert len(report.quarantined_dates) == 1


def test_high_below_close_is_caught():
    """A feed reporting high < close is internally inconsistent. Every
    range-based indicator downstream would silently be wrong."""
    rows = [*GOOD, [105, 106, 104, 110, 500_000]]
    report = validate_bars("SPY", _bars(rows))
    assert any(v.rule == "ohlc_ordering" for v in report.errors)


def test_low_above_open_is_caught():
    rows = [*GOOD, [105, 112, 108, 110, 500_000]]
    report = validate_bars("SPY", _bars(rows))
    assert any(v.rule == "ohlc_ordering" for v in report.errors)


def test_negative_volume_is_an_error_and_zero_volume_is_a_warning():
    neg = validate_bars("SPY", _bars([*GOOD, [105, 108, 104, 106, -5]]))
    assert any(v.rule == "non_negative_volume" for v in neg.errors)

    zero = validate_bars("SPY", _bars([*GOOD, [105, 108, 104, 106, 0]]))
    assert zero.is_usable, "a zero-volume bar is suspicious, not unusable"
    assert any(v.rule == "zero_volume" for v in zero.warnings)


def test_duplicate_dates_are_an_error():
    df = _bars(GOOD)
    dup = pd.concat([df, df.iloc[[1]]]).sort_index()
    report = validate_bars("SPY", dup)
    assert any(v.rule == "duplicate_dates" for v in report.errors)


def test_unsorted_dates_are_an_error():
    df = _bars(GOOD).iloc[::-1]
    report = validate_bars("SPY", df)
    assert any(v.rule == "monotonic_dates" for v in report.errors)


def test_extreme_move_is_flagged_as_a_warning_not_deleted():
    """Real 50% moves happen -- biotech readouts, buyouts. The system flags them
    for a human rather than destroying genuine history."""
    rows = [*GOOD, [105, 210, 104, 205, 900_000]]
    report = validate_bars("SPY", _bars(rows))
    assert report.is_usable
    assert any(v.rule == "extreme_move" for v in report.warnings)


def test_extreme_move_is_exempt_on_a_known_corporate_action_date():
    """This is the payoff for storing corporate actions separately instead of
    baking adjustments into prices: a 2-for-1 split is explainable, not an alert."""
    rows = [*GOOD, [52, 55, 50, 52, 1_800_000]]
    df = _bars(rows)
    action_date = df.index[-1].date()

    noisy = validate_bars("SPY", df)
    assert any(v.rule == "extreme_move" for v in noisy.warnings)

    quiet = validate_bars("SPY", df, known_action_dates=frozenset({action_date}))
    assert not any(v.rule == "extreme_move" for v in quiet.warnings)


def test_calendar_gap_detected_against_a_real_session_list():
    """Expected sessions must come from a trading calendar, never from the data
    itself -- a self-derived expectation can never find a missing day."""
    df = _bars(GOOD)
    expected = pd.date_range(df.index[0], periods=5, freq="B")
    report = validate_bars("SPY", df, expected_sessions=expected)
    gaps = [v for v in report.warnings if v.rule == "calendar_gap"]
    assert len(gaps) == 2
    assert report.is_usable


def test_report_summary_counts_both_severities():
    rows = [*GOOD, [105, 108, -1, 106, 0]]
    report = validate_bars("SPY", _bars(rows))
    assert "error" in report.summary()
    assert report.errors and report.warnings
