"""The Phase 1 gate, exercised through the real CLI.

These exist because of a live failure: every symbol was skipped when the
reference source returned 404, and the command printed

    Phase 1 gate: PASSED -- stored prices match an independent source.

Nothing had been compared. The skip lines scrolled past above the verdict. A
gate that reports success when it examined nothing is worse than no gate, so
each outcome is pinned here.
"""

from __future__ import annotations

import importlib
from datetime import date

import httpx
import pytest
from typer.testing import CliRunner

from screener.providers.reference import ReferenceBar, ReferenceUnavailable
from tests.unit.ingest.conftest import CLEAN_ROWS, FakeProvider, make_bars


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    db_file = tmp_path / "verify.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("ALPACA_API_KEY_ID", "k")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "s")

    from screener import config
    from screener.db import session as db_session

    config.get_settings.cache_clear()
    db_session._engine = None
    db_session._SessionFactory = None

    from screener import cli
    importlib.reload(cli)
    yield cli

    config.get_settings.cache_clear()
    db_session._engine = None
    db_session._SessionFactory = None


@pytest.fixture
def ingested(cli_env, monkeypatch):
    cli = cli_env
    runner = CliRunner()
    runner.invoke(cli.app, ["db", "init"])
    monkeypatch.setattr(
        "screener.providers.alpaca.AlpacaProvider",
        lambda *a, **k: FakeProvider({"SPY": make_bars(CLEAN_ROWS, start="2024-01-02")}),
    )
    result = runner.invoke(
        cli.app, ["ingest", "--symbols", "SPY", "--start", "2024-01-01", "--end", "2024-01-31"]
    )
    assert result.exit_code == 0, result.output
    return cli, runner


class StubReference:
    """Stands in for Stooq. ``bars`` None means the source is unreachable."""

    name = "stub"

    def __init__(self, bars=None, raises=None):
        self._bars = bars
        self._raises = raises

    def get_bars(self, ticker, start, end):
        if self._raises is not None:
            raise self._raises
        return self._bars or []

    def close(self):
        pass


MATCHING = [
    ReferenceBar(date(2024, 1, 2), 100.0, 105.0, 98.0, 103.0, 1_000_000.0),
    ReferenceBar(date(2024, 1, 3), 103.0, 108.0, 102.0, 107.0, 1_200_000.0),
    ReferenceBar(date(2024, 1, 4), 107.0, 110.0, 104.0, 105.0, 900_000.0),
    ReferenceBar(date(2024, 1, 5), 105.0, 112.0, 103.0, 111.0, 1_500_000.0),
]


def use(monkeypatch, reference):
    """Substitute the whole reference factory.

    Patching a single source class would leave the other one in the chain
    making real HTTP requests, so a test could pass by falling back to the
    stub after a genuine network round trip.
    """
    monkeypatch.setattr(
        "screener.providers.reference.build_reference", lambda *a, **k: reference
    )


def test_unreachable_reference_is_inconclusive_not_passed(ingested, monkeypatch):
    """The exact live failure: 404 for every symbol."""
    cli, runner = ingested
    use(monkeypatch, StubReference(raises=ReferenceUnavailable("404 for every host")))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY"])

    assert result.exit_code == 1
    assert "INCONCLUSIVE" in result.output
    assert "NOTHING WAS COMPARED" in result.output
    assert "PASSED" not in result.output


def test_http_error_from_the_reference_is_also_inconclusive(ingested, monkeypatch):
    cli, runner = ingested
    use(monkeypatch, StubReference(raises=httpx.ConnectError("no route to host")))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY"])

    assert result.exit_code == 1
    assert "INCONCLUSIVE" in result.output


def test_reference_with_no_overlapping_dates_is_inconclusive(ingested, monkeypatch):
    """Reachable, returned rows, but for entirely different sessions."""
    cli, runner = ingested
    use(monkeypatch, StubReference([
        ReferenceBar(date(2020, 6, 1), 1.0, 1.0, 1.0, 1.0, 1.0),
    ]))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY"])

    assert result.exit_code == 1
    assert "INCONCLUSIVE" in result.output


def test_matching_prices_pass(ingested, monkeypatch):
    cli, runner = ingested
    use(monkeypatch, StubReference(MATCHING))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY"])

    assert result.exit_code == 0, result.output
    assert "PASSED" in result.output


def test_a_wrong_price_fails_the_gate(ingested, monkeypatch):
    cli, runner = ingested
    wrong = [
        ReferenceBar(date(2024, 1, 2), 100.0, 105.0, 98.0, 999.0, 1_000_000.0),
        *MATCHING[1:],
    ]
    use(monkeypatch, StubReference(wrong))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY"])

    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_some_verified_and_some_skipped_is_partial_not_passed(ingested, monkeypatch):
    """SPY verifies; QQQ was never ingested. Partial coverage is not the gate."""
    cli, runner = ingested
    use(monkeypatch, StubReference(MATCHING))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY,QQQ"])

    assert result.exit_code == 1
    assert "PARTIAL" in result.output


def test_volume_differences_alone_do_not_fail_the_gate(ingested, monkeypatch):
    """The free feed is IEX-only, so its volume legitimately differs from the
    consolidated tape. Prices are what must agree."""
    cli, runner = ingested
    volume_only = [
        ReferenceBar(b.trade_date, b.open, b.high, b.low, b.close, b.volume * 3)
        for b in MATCHING
    ]
    use(monkeypatch, StubReference(volume_only))

    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY"])

    assert result.exit_code == 0, result.output
    assert "PASSED" in result.output


def test_an_unknown_reference_name_is_a_clean_error(ingested):
    cli, runner = ingested
    result = runner.invoke(cli.app, ["verify", "--symbols", "SPY", "--reference", "nope"])
    assert result.exit_code == 1
    assert "unknown reference" in result.output
