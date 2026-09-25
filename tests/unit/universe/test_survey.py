"""The market survey: what gets stored, and on whose authority.

A symbol this survey excludes can never be reconsidered without running
another one, so the floors that produced a candidate file have to stay
visible in what it reports.
"""

from __future__ import annotations

from datetime import date

import pytest

from screener.universe.survey import (
    MIN_DOLLAR_VOLUME,
    MIN_PRICE,
    SurveyResult,
    eligible,
)

ALLOWED = {"AAA": "NYSE", "BBB": "NASDAQ"}


def _row(code: str, close: float, volume: float) -> dict:
    return {"code": code, "close": close, "volume": volume}


def test_default_floors_are_unchanged():
    """These decide what the project stores. A silent edit would re-scope every
    result built afterwards, so the values are pinned."""
    assert MIN_DOLLAR_VOLUME == 2_000_000.0
    assert MIN_PRICE == 5.0


def test_a_thin_name_fails_the_default_floor_and_passes_a_lowered_one():
    row = _row("AAA", close=10.0, volume=50_000)      # $500,000 a day
    assert eligible(row, ALLOWED) is None
    assert eligible(row, ALLOWED, min_dollar_volume=250_000.0) == ("AAA", 500_000.0)


def test_the_price_floor_is_independent_of_the_volume_floor():
    row = _row("AAA", close=2.0, volume=1_000_000)    # $2m a day, $2 a share
    assert eligible(row, ALLOWED) is None
    assert eligible(row, ALLOWED, min_price=1.0) is not None


def test_a_symbol_off_the_venue_list_is_excluded_at_any_floor():
    assert eligible(_row("ZZZ", 50.0, 1_000_000), ALLOWED,
                    min_dollar_volume=0.0, min_price=0.0) is None


def test_summary_reports_the_floors_actually_used_not_the_defaults():
    """The bug this pins: `summary()` read the module constants, so a survey
    run with an overridden floor announced itself as a $2,000,000 sweep. The
    file it wrote was then indistinguishable from a default one except by
    length. Found 2026-09-24 on the first run with a non-default floor.
    """
    thin = SurveyResult(dates_sampled=71, min_dollar_volume=250_000.0)
    thin.eligible_symbols = {"AAA", "BBB"}
    assert "$250,000/day" in thin.summary()
    assert "$2,000,000" not in thin.summary()

    default = SurveyResult(dates_sampled=71)
    default.eligible_symbols = {"AAA"}
    assert "$2,000,000/day" in default.summary()


def test_a_result_defaults_to_the_module_floors():
    r = SurveyResult()
    assert r.min_dollar_volume == MIN_DOLLAR_VOLUME
    assert r.min_price == MIN_PRICE


@pytest.mark.parametrize("close,volume", [(0.0, 1e6), (10.0, 0.0), (10.0, -5)])
def test_a_row_that_did_not_trade_is_never_eligible(close, volume):
    assert eligible(_row("AAA", close, volume), ALLOWED,
                    min_dollar_volume=0.0, min_price=0.0) is None
