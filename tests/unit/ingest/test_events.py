"""Earnings ingestion: idempotent, and one bad symbol never stops the run."""

from __future__ import annotations

from datetime import date

from screener.db.models import EarningsEvent, Symbol
from screener.ingest.events import earnings_dates, ingest_earnings
from screener.providers.base import ProviderError
from screener.providers.edgar import Filing
from tests.unit.ingest.conftest import session  # noqa: F401


class FakeEdgar:
    name = "edgar"

    def __init__(self, filings=None, raises=None):
        self.filings = filings or {}
        self.raises = raises
        self.calls = []

    def get_earnings_dates(self, ticker, start, end):
        self.calls.append(ticker)
        if self.raises and ticker in self.raises:
            raise ProviderError(self.raises[ticker])
        return self.filings.get(ticker, [])


def filing(day: str, form: str = "8-K", period: str | None = None) -> Filing:
    return Filing(
        symbol="AAA", filed=date.fromisoformat(day), form=form,
        period=date.fromisoformat(period) if period else None,
        accession=f"acc-{day}",
    )


def add_symbol(session, ticker: str) -> Symbol:  # noqa: F811
    symbol = Symbol(ticker=ticker, name=ticker, asset_type="equity")
    session.add(symbol)
    session.flush()
    return symbol


def test_events_are_stored(session):  # noqa: F811
    symbol = add_symbol(session, "AAA")
    provider = FakeEdgar({"AAA": [filing("2024-02-01"), filing("2024-05-02")]})

    summary = ingest_earnings(session, provider, ["AAA"], date(2024, 1, 1), date(2024, 12, 31))

    assert summary.written == 2
    assert earnings_dates(session, symbol.id) == [date(2024, 2, 1), date(2024, 5, 2)]


def test_reingesting_writes_nothing_new(session):  # noqa: F811
    add_symbol(session, "AAA")
    provider = FakeEdgar({"AAA": [filing("2024-02-01")]})
    args = (["AAA"], date(2024, 1, 1), date(2024, 12, 31))

    first = ingest_earnings(session, provider, *args)
    second = ingest_earnings(session, provider, *args)

    assert first.written == 1
    assert second.written == 0
    assert second.results[0].skipped == 1


def test_one_failing_symbol_does_not_stop_the_others(session):  # noqa: F811
    add_symbol(session, "AAA")
    add_symbol(session, "BBB")
    provider = FakeEdgar(
        {"BBB": [filing("2024-02-01")]},
        raises={"AAA": "EDGAR does not list a CIK"},
    )

    summary = ingest_earnings(
        session, provider, ["AAA", "BBB"], date(2024, 1, 1), date(2024, 12, 31)
    )

    assert summary.written == 1
    assert [f.ticker for f in summary.failed] == ["AAA"]
    assert provider.calls == ["AAA", "BBB"]


def test_an_unknown_symbol_is_reported_not_skipped_silently(session):  # noqa: F811
    summary = ingest_earnings(
        session, FakeEdgar(), ["NOPE"], date(2024, 1, 1), date(2024, 12, 31)
    )

    assert summary.written == 0
    assert "not ingested" in summary.failed[0].error


def test_the_form_is_recorded_so_the_proxy_stays_visible(session):  # noqa: F811
    """A filing date is not an announcement date. Which form supplied it has to
    survive into analysis rather than being averaged away."""
    symbol = add_symbol(session, "AAA")
    provider = FakeEdgar({"AAA": [filing("2024-02-01", "8-K"), filing("2024-08-01", "10-Q")]})

    ingest_earnings(session, provider, ["AAA"], date(2024, 1, 1), date(2024, 12, 31))

    forms = sorted(
        row.form for row in session.query(EarningsEvent).filter_by(symbol_id=symbol.id)
    )
    assert forms == ["10-Q", "8-K"]
