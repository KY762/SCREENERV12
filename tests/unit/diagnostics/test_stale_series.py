"""Series that keep trading after the company stopped existing.

Measured on EODHD, 2026-09-19: FRC and SIVB end correctly on the week they
failed; BBBY and SBNY keep printing bars into 2026. A backtest holding SBNY
through 2024 is holding something that did not exist.
"""

from __future__ import annotations

from datetime import date

from screener.diagnostics.stale_series import Series, coverage_gap, find_suspects

AS_OF = date(2026, 9, 19)
DELISTED = {"FRC", "SIVB", "BBBY", "SBNY", "YELL"}


def series(symbol: str, last: date, first: date = date(2009, 1, 2), bars: int = 3000):
    return Series(symbol=symbol, first_bar=first, last_bar=last, bars=bars)


def test_a_dead_company_still_quoting_is_flagged():
    """The SBNY case: Signature Bank failed in March 2023."""
    suspects = find_suspects(
        [series("SBNY", date(2026, 9, 18))], DELISTED, as_of=AS_OF
    )

    assert [s.symbol for s in suspects] == ["SBNY"]
    assert "quoting to 2026-09-18" in suspects[0].reason


def test_a_correctly_truncated_series_is_not_flagged():
    """FRC ends the week First Republic failed. That is the data being right,
    and flagging it would train the reader to ignore the report."""
    assert find_suspects([series("FRC", date(2023, 5, 2))], DELISTED, as_of=AS_OF) == []


def test_a_living_company_is_never_flagged():
    """AAPL quotes to the end of the data because Apple exists."""
    assert find_suspects([series("AAPL", AS_OF)], DELISTED, as_of=AS_OF) == []


def test_staleness_is_judged_against_the_data_not_today():
    """A database loaded a year ago must not report every symbol as stale."""
    loaded_to = date(2024, 1, 5)
    suspects = find_suspects(
        [series("SBNY", date(2024, 1, 4))], DELISTED, as_of=loaded_to
    )
    assert [s.symbol for s in suspects] == ["SBNY"]

    # The same series, judged against data that runs two more years, is old
    # news rather than a live quote.
    assert find_suspects([series("SBNY", date(2024, 1, 4))], DELISTED, as_of=AS_OF) == []


def test_the_window_is_generous_enough_for_an_orderly_delisting():
    """A company that stops trading a fortnight before the data ends is
    plausibly a real delisting in progress, not a reused ticker."""
    suspects = find_suspects(
        [series("YELL", date(2026, 9, 5))], DELISTED, as_of=AS_OF, recent_days=45
    )
    assert [s.symbol for s in suspects] == ["YELL"]


def test_the_coverage_gap_is_what_the_universe_wants_and_the_database_lacks():
    assert coverage_gap(["AAPL", "AAMRQ", "FRC"], ["AAPL", "FRC"]) == ["AAMRQ"]
    assert coverage_gap(["AAPL"], ["AAPL", "MSFT"]) == [], "extras are not a gap"
