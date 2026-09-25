"""Is our stored series actually the prices of the ticker's previous owner?"""

from __future__ import annotations

import pandas as pd
import pytest

from screener.diagnostics.stale_series import twin_overlap


def _closes(start: str, values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)))


def test_identical_prices_over_the_shared_window_means_contaminated():
    """The definitive case: our JAVA is Sun's prices, so JAVA is not the
    company the universe thinks it is."""
    theirs = _closes("2012-01-02", [10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.1])
    ours = theirs.copy()
    out = twin_overlap("JAVA", "JAVA_OLD", ours, theirs)
    assert out.verdict == "contaminated"
    assert out.match_rate == 1.0


def test_different_prices_over_the_same_dates_means_two_securities():
    """GM: new GM listed while old GM's shell still traded. Dates overlap and
    the data is fine, so a date-based test would wrongly quarantine it."""
    theirs = _closes("2012-01-02", [1.0, 1.1, 0.9, 1.0, 1.2, 0.8, 1.1])
    ours = _closes("2012-01-02", [34.0, 34.8, 35.1, 34.2, 35.9, 36.0, 35.5])
    out = twin_overlap("GM", "GM_OLD", ours, theirs)
    assert out.verdict == "separate"
    assert out.matching_days == 0


def test_a_twin_that_ended_before_our_series_began_shares_nothing():
    theirs = _closes("2005-01-03", [5.0] * 10)
    ours = _closes("2012-01-02", [50.0] * 10)
    out = twin_overlap("X", "X_OLD", ours, theirs)
    assert out.verdict == "insufficient"
    assert out.shared_days == 0


def test_a_tiny_overlap_is_not_enough_to_judge():
    theirs = _closes("2012-01-02", [10.0, 10.5, 11.0])
    ours = _closes("2012-01-02", [10.0, 10.5, 11.0])
    out = twin_overlap("X", "X_OLD", ours, theirs, min_shared_days=5)
    assert out.verdict == "insufficient"


def test_rounding_differences_still_count_as_the_same_price():
    """Exact equality would report a contaminated symbol as clean, which is the
    expensive direction to be wrong in."""
    theirs = _closes("2012-01-02", [10.00, 10.50, 11.00, 10.80, 11.20, 11.50])
    ours = _closes("2012-01-02", [10.001, 10.499, 11.002, 10.799, 11.201, 11.498])
    assert twin_overlap("X", "X_OLD", ours, theirs).verdict == "contaminated"


def test_a_partial_match_below_the_threshold_is_separate():
    theirs = _closes("2012-01-02", [10.0] * 10)
    ours = _closes("2012-01-02", [10.0] * 5 + [99.0] * 5)
    out = twin_overlap("X", "X_OLD", ours, theirs)
    assert out.match_rate == pytest.approx(0.5)
    assert out.verdict == "separate"


def test_a_zero_price_in_the_twin_never_counts_as_a_match():
    """Dividing by zero must not produce a match. The dead-bar symbols in this
    database make zero and repeated prices common."""
    theirs = _closes("2012-01-02", [0.0] * 8)
    ours = _closes("2012-01-02", [0.0] * 8)
    assert twin_overlap("X", "X_OLD", ours, theirs).verdict == "separate"
