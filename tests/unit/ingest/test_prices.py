"""Ingestion tests.

The headline requirement is idempotency: a missed nightly run must be
recoverable by simply running it again. The platform lives on a laptop that is
not always awake, so this is not a theoretical concern.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select

from screener.db.models import DataQualityLog, IngestionRun, PriceDaily, Symbol
from screener.ingest.prices import get_or_create_symbol, ingest_daily_bars

from .conftest import CLEAN_ROWS, FakeProvider, make_bars


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_first_ingestion_writes_all_bars(session, clean_provider, window):
    summary = ingest_daily_bars(session, clean_provider, ["SPY"], *window)
    assert summary.status == "succeeded"
    assert summary.rows_written == 4
    assert _count(session, PriceDaily) == 4


def test_ingestion_is_idempotent(session, clean_provider, window):
    """Re-running the same range must converge, not duplicate.

    The second run writes zero rows because every value already matches --
    that is the signal that a re-run is safe and cheap.
    """
    first = ingest_daily_bars(session, clean_provider, ["SPY"], *window)
    second = ingest_daily_bars(session, clean_provider, ["SPY"], *window)

    assert first.rows_written == 4
    assert second.rows_written == 0, "unchanged bars should not be rewritten"
    assert _count(session, PriceDaily) == 4, "re-running must not duplicate rows"
    assert second.status == "succeeded"


def test_corrected_data_updates_the_existing_row(session, window):
    """Providers do restate bars. A correction must overwrite in place, keeping
    one row per (symbol, date)."""
    provider = FakeProvider({"SPY": make_bars(CLEAN_ROWS)})
    ingest_daily_bars(session, provider, ["SPY"], *window)

    corrected = [list(r) for r in CLEAN_ROWS]
    corrected[2][3] = 106.5  # close revised from 105
    provider.frames["SPY"] = make_bars(corrected)

    summary = ingest_daily_bars(session, provider, ["SPY"], *window)
    assert summary.rows_written == 1, "only the changed bar should be touched"
    assert _count(session, PriceDaily) == 4

    row = session.scalar(
        select(PriceDaily).where(PriceDaily.date == pd.Timestamp("2024-01-04").date())
    )
    assert row.close == Decimal("106.500000")


def test_prices_are_stored_as_decimal_not_float(session, clean_provider, window):
    """Money is Decimal. A float here is a rounding error waiting to become a
    wrong position size."""
    ingest_daily_bars(session, clean_provider, ["SPY"], *window)
    row = session.scalars(select(PriceDaily)).first()
    assert isinstance(row.close, Decimal)
    assert isinstance(row.volume, int)


def test_bad_bars_are_quarantined_and_logged(session, window):
    """A negative low must never reach price_daily -- and must not vanish
    silently either. It goes to data_quality_log so it is auditable."""
    rows = [*CLEAN_ROWS, [110, 115, -1, 112, 800_000]]
    provider = FakeProvider({"SPY": make_bars(rows)})

    summary = ingest_daily_bars(session, provider, ["SPY"], *window)

    assert _count(session, PriceDaily) == 4, "the bad bar must not be written"
    assert summary.results[0].rows_quarantined == 1
    errors = session.scalars(
        select(DataQualityLog).where(DataQualityLog.severity == "error")
    ).all()
    assert errors and errors[0].rule == "positive_prices"


def test_warnings_do_not_block_ingestion(session, window):
    """A zero-volume bar is suspicious, not unusable. It is stored AND flagged."""
    rows = [*CLEAN_ROWS, [111, 113, 109, 112, 0]]
    provider = FakeProvider({"SPY": make_bars(rows)})

    ingest_daily_bars(session, provider, ["SPY"], *window)

    assert _count(session, PriceDaily) == 5, "warning-level bars are still usable"
    warnings = session.scalars(
        select(DataQualityLog).where(DataQualityLog.severity == "warning")
    ).all()
    assert any(w.rule == "zero_volume" for w in warnings)


def test_one_failing_symbol_does_not_abort_the_run(session, window):
    """A nightly job must not die because one ticker returned nothing."""
    provider = FakeProvider({"SPY": make_bars(CLEAN_ROWS)})  # QQQ absent
    summary = ingest_daily_bars(session, provider, ["SPY", "QQQ"], *window)

    assert summary.status == "partial"
    assert [r.ticker for r in summary.succeeded] == ["SPY"]
    assert [r.ticker for r in summary.failed] == ["QQQ"]
    assert _count(session, PriceDaily) == 4


def test_provider_outage_is_recorded_not_raised(session, window):
    provider = FakeProvider(raises="upstream 503")
    summary = ingest_daily_bars(session, provider, ["SPY", "QQQ"], *window)

    assert summary.status == "failed"
    assert len(summary.failed) == 2
    run = session.scalars(select(IngestionRun)).one()
    assert run.status == "failed"
    assert "503" in run.error


def test_run_bookkeeping_records_what_happened(session, clean_provider, window):
    """Without this, a silent failure looks identical to a quiet market day."""
    ingest_daily_bars(session, clean_provider, ["SPY"], *window)
    run = session.scalars(select(IngestionRun)).one()

    assert run.job == "daily_bars"
    assert run.provider == "fake"
    assert (run.symbols_requested, run.symbols_ok, run.symbols_failed) == (1, 1, 0)
    assert run.rows_written == 4
    assert run.status == "succeeded"
    assert run.finished_at is not None


def test_symbol_date_span_tracks_stored_data(session, clean_provider, window):
    ingest_daily_bars(session, clean_provider, ["SPY"], *window)
    symbol = session.scalar(select(Symbol).where(Symbol.ticker == "SPY"))
    assert symbol.first_date == pd.Timestamp("2024-01-02").date()
    assert symbol.last_date == pd.Timestamp("2024-01-05").date()


def test_get_or_create_symbol_is_stable_and_normalizes_case(session):
    a = get_or_create_symbol(session, "spy")
    b = get_or_create_symbol(session, "SPY")
    c = get_or_create_symbol(session, "  SPY  ")
    assert a.id == b.id == c.id
    assert a.ticker == "SPY"
    assert _count(session, Symbol) == 1


def test_calendar_gaps_are_reported_when_a_session_list_is_supplied(
    session, clean_provider, window
):
    expected = pd.date_range("2024-01-02", periods=6, freq="B")
    ingest_daily_bars(session, clean_provider, ["SPY"], *window, expected_sessions=expected)

    gaps = session.scalars(
        select(DataQualityLog).where(DataQualityLog.rule == "calendar_gap")
    ).all()
    assert len(gaps) == 2


def test_multiple_symbols_are_kept_separate(session, window):
    provider = FakeProvider(
        {
            "SPY": make_bars(CLEAN_ROWS),
            "QQQ": make_bars([[r * 2 for r in row] for row in CLEAN_ROWS]),
        }
    )
    ingest_daily_bars(session, provider, ["SPY", "QQQ"], *window)

    spy = session.scalar(select(Symbol).where(Symbol.ticker == "SPY"))
    qqq = session.scalar(select(Symbol).where(Symbol.ticker == "QQQ"))
    spy_close = session.scalar(
        select(PriceDaily.close).where(PriceDaily.symbol_id == spy.id).limit(1)
    )
    qqq_close = session.scalar(
        select(PriceDaily.close).where(PriceDaily.symbol_id == qqq.id).limit(1)
    )
    assert qqq_close == spy_close * 2
    assert _count(session, PriceDaily) == 8


def test_provider_is_asked_for_raw_unadjusted_bars(session, clean_provider, window):
    """Storing pre-adjusted prices makes history mutate under you. The request
    must always be raw; adjustments are derived from corporate actions."""
    ingest_daily_bars(session, clean_provider, ["SPY"], *window)
    assert clean_provider.calls[0].adjustment == "raw"
