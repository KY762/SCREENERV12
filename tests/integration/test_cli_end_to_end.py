"""End-to-end test: CLI -> ingestion -> validation -> database -> CLI readback.

Exercises the real command surface against a real (SQLite) database with a fake
provider substituted at the seam. Everything between the provider boundary and
the terminal output is the production path.
"""

from __future__ import annotations

import importlib

import pytest
from typer.testing import CliRunner

from tests.unit.ingest.conftest import CLEAN_ROWS, FakeProvider, make_bars


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Point the app at a temporary SQLite file and reset cached singletons."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("ALPACA_API_KEY_ID", "test-key-id")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "test-secret")

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
def runner() -> CliRunner:
    return CliRunner()


def test_full_pipeline(cli_env, runner, monkeypatch):
    """db init -> ingest -> show -> runs -> quality -> freshness."""
    cli = cli_env

    result = runner.invoke(cli.app, ["db", "init"])
    assert result.exit_code == 0, result.output
    assert "Schema ready" in result.output

    # Substitute the provider at the boundary; everything downstream is real.
    rows = [*CLEAN_ROWS, [111, 113, 109, 112, 0]]          # trailing zero-volume warning
    fake = FakeProvider({"SPY": make_bars(rows, start="2024-01-02")})
    monkeypatch.setattr(
        "screener.providers.alpaca.AlpacaProvider", lambda *a, **k: fake
    )

    result = runner.invoke(
        cli.app, ["ingest", "--symbols", "SPY", "--start", "2024-01-01", "--end", "2024-01-31"]
    )
    assert result.exit_code == 0, result.output
    assert "succeeded" in result.output
    assert "5 rows written" in result.output

    # Re-run: idempotent, nothing rewritten.
    result = runner.invoke(
        cli.app, ["ingest", "--symbols", "SPY", "--start", "2024-01-01", "--end", "2024-01-31"]
    )
    assert result.exit_code == 0, result.output
    assert "0 rows written" in result.output

    result = runner.invoke(cli.app, ["db", "status"])
    assert result.exit_code == 0
    assert "SPY" in result.output

    result = runner.invoke(cli.app, ["show", "SPY", "--tail", "3"])
    assert result.exit_code == 0, result.output
    assert "raw, unadjusted" in result.output

    result = runner.invoke(cli.app, ["runs"])
    assert result.exit_code == 0
    assert "succeeded" in result.output

    result = runner.invoke(cli.app, ["quality"])
    assert result.exit_code == 0
    assert "zero_volume" in result.output

    # 2024 bars are long stale relative to today -- freshness must fail loudly.
    result = runner.invoke(cli.app, ["freshness"])
    assert result.exit_code == 1, "stale data must exit non-zero"
    assert "stale" in result.output


def test_ingest_without_credentials_fails_clearly(cli_env, runner, monkeypatch):
    """A missing key should produce an actionable message, not a stack trace."""
    cli = cli_env
    monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)

    from screener import config
    config.get_settings.cache_clear()

    runner.invoke(cli.app, ["db", "init"])
    result = runner.invoke(
        cli.app, ["ingest", "--symbols", "SPY", "--start", "2024-01-01"]
    )
    assert result.exit_code == 1
    assert "credentials missing" in result.output
    assert ".env.example" in result.output


def test_show_unknown_symbol_is_a_clean_error(cli_env, runner):
    cli = cli_env
    runner.invoke(cli.app, ["db", "init"])
    result = runner.invoke(cli.app, ["show", "NOPE"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_config_reports_a_configured_provider(cli_env, runner):
    """'Is my key being read?' must be answerable without guessing."""
    result = runner.invoke(cli_env.app, ["config"])

    assert result.exit_code == 0, result.output
    assert "ALPACA" in result.output
    assert "TIINGO" in result.output


def test_config_names_which_provider_ingest_will_use(cli_env, runner, monkeypatch):
    """A key that is present but unread looks identical to one never pasted."""
    monkeypatch.setenv("TIINGO_API_KEY", "test-token")
    from screener import config
    config.get_settings.cache_clear()

    result = runner.invoke(cli_env.app, ["config"])

    assert "will use Tiingo" in result.output


def test_config_warns_when_only_alpaca_is_available(cli_env, runner, monkeypatch):
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    from screener import config
    config.get_settings.cache_clear()

    result = runner.invoke(cli_env.app, ["config"])

    assert "will use Alpaca" in result.output
    assert "2020-07-27" in result.output, "the measured limit should be stated, not implied"


def test_config_never_prints_a_secret(cli_env, runner, monkeypatch):
    monkeypatch.setenv("TIINGO_API_KEY", "super-secret-token-value")
    monkeypatch.setenv("ALPACA_API_KEY_ID", "another-secret-value")
    from screener import config
    config.get_settings.cache_clear()

    result = runner.invoke(cli_env.app, ["config"])

    assert "super-secret-token-value" not in result.output
    assert "another-secret-value" not in result.output
