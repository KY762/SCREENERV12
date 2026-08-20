"""Verification-comparator tests.

The comparator decides whether Phase 1 passes, so its tolerance behaviour has to
be exactly right. Too strict and it fails on correct data because the free feed
reports IEX volume rather than the consolidated tape; too loose and it waves
through a genuinely wrong price.
"""

from datetime import date

import pytest

from screener.providers.reference import parse_stooq_csv
from screener.validate.verify import compare_bars

D1, D2, D3 = date(2024, 3, 11), date(2024, 3, 12), date(2024, 3, 13)


def _bars(**overrides):
    base = {
        D1: {"open": 100.0, "high": 105.0, "low": 98.0, "close": 103.0, "volume": 1_000_000.0},
        D2: {"open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 1_200_000.0},
    }
    base.update(overrides)
    return base


def test_identical_bars_pass():
    result = compare_bars("SPY", _bars(), _bars())
    assert result.passed
    assert result.dates_compared == 2
    assert "PASS" in result.summary()


def test_sub_cent_rounding_is_tolerated():
    """0.004 is rounding between two feeds, not a disagreement about price."""
    theirs = _bars()
    theirs[D1] = {**theirs[D1], "close": 103.004}
    assert compare_bars("SPY", _bars(), theirs).passed


def test_a_real_price_difference_fails():
    """One cent is a real difference. Everything downstream is built on price."""
    theirs = _bars()
    theirs[D1] = {**theirs[D1], "close": 103.02}
    result = compare_bars("SPY", _bars(), theirs)
    assert not result.passed
    assert len(result.price_mismatches) == 1
    m = result.price_mismatches[0]
    assert (m.field, m.trade_date) == ("close", D1)
    assert m.difference == pytest.approx(-0.02)


def test_volume_difference_does_not_fail_the_gate():
    """The free Alpaca feed is IEX-only, so its volume is a fraction of the
    consolidated tape. Failing on this would fail the gate on correct data."""
    theirs = _bars()
    theirs[D1] = {**theirs[D1], "volume": 8_000_000.0}   # 8x ours
    result = compare_bars("SPY", _bars(), theirs)
    assert result.passed, "volume divergence must not fail the gate"
    assert len(result.volume_differences) == 1


def test_a_session_we_are_missing_fails():
    """The reference has a bar we do not -- a genuine ingestion gap."""
    theirs = _bars()
    theirs[D3] = {"open": 107.0, "high": 110.0, "low": 106.0, "close": 109.0, "volume": 900_000.0}
    result = compare_bars("SPY", _bars(), theirs)
    assert not result.passed
    assert result.missing_from_ours == [D3]


def test_a_session_the_reference_lacks_does_not_fail():
    """Reference sources have their own gaps. Treating them as authoritative
    about which sessions exist would be circular."""
    ours = _bars()
    ours[D3] = {"open": 107.0, "high": 110.0, "low": 106.0, "close": 109.0, "volume": 900_000.0}
    result = compare_bars("SPY", ours, _bars())
    assert result.passed
    assert result.missing_from_reference == [D3]


def test_every_ohlc_field_is_checked_not_just_close():
    theirs = _bars()
    theirs[D2] = {**theirs[D2], "open": 103.5, "high": 108.9, "low": 101.2}
    result = compare_bars("SPY", _bars(), theirs)
    fields = {m.field for m in result.price_mismatches}
    assert fields == {"open", "high", "low"}


def test_no_overlapping_dates_reports_zero_compared():
    """An empty comparison must not masquerade as a pass with real coverage."""
    theirs = {D3: {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0}}
    result = compare_bars("SPY", _bars(), theirs)
    assert result.dates_compared == 0
    assert not result.passed        # D3 is missing from ours
    assert result.missing_from_ours == [D3]


# --- reference CSV parsing -------------------------------------------------

def test_parse_stooq_csv():
    csv_text = """Date,Open,High,Low,Close,Volume
2024-03-11,512.31,514.20,510.70,513.05,45123400
2024-03-12,514.00,517.28,513.44,517.06,51234500
"""
    bars = parse_stooq_csv(csv_text)
    assert len(bars) == 2
    assert bars[0].trade_date == date(2024, 3, 11)
    assert bars[0].close == pytest.approx(513.05)
    assert bars[1].volume == pytest.approx(51_234_500)


def test_parse_stooq_csv_sorts_ascending():
    csv_text = """Date,Open,High,Low,Close,Volume
2024-03-12,514.00,517.28,513.44,517.06,51234500
2024-03-11,512.31,514.20,510.70,513.05,45123400
"""
    bars = parse_stooq_csv(csv_text)
    assert [b.trade_date for b in bars] == [date(2024, 3, 11), date(2024, 3, 12)]


def test_parse_stooq_handles_error_responses_and_junk_rows():
    """Stooq returns plain text on error. Malformed rows are skipped, not fatal --
    a partial reference is still useful for comparison."""
    assert parse_stooq_csv("No data") == []
    assert parse_stooq_csv("") == []

    partial = """Date,Open,High,Low,Close,Volume
2024-03-11,512.31,514.20,510.70,513.05,45123400
2024-03-12,N/A,N/A,N/A,N/A,N/A
"""
    assert len(parse_stooq_csv(partial)) == 1
