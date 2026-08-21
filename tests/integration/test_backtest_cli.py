"""End-to-end: ingest synthetic bars through the real CLI, then backtest them.

The point is not the numbers -- the data is synthetic and the result is
meaningless. The point is that the whole path runs, the budget is enforced
through the real database, and the criteria table appears.
"""

from __future__ import annotations

import importlib
from datetime import date

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from tests.unit.ingest.conftest import FakeProvider


def synthetic_frame(seed: int, n: int, start: date) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(start, periods=n)
    steps = rng.normal(0.0007, 0.02, n)
    close = 100.0 * np.exp(np.cumsum(steps))
    spread = np.abs(rng.normal(0.014, 0.007, n)) * close
    open_ = close * (1.0 + rng.normal(0.0, 0.007, n))
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": rng.uniform(2e6, 9e6, n),
        },
        index=index,
    )


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    db_file = tmp_path / "backtest.db"
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
def loaded(cli_env, monkeypatch):
    """A database holding four symbols of synthetic development-split history."""
    cli = cli_env
    runner = CliRunner()
    runner.invoke(cli.app, ["db", "init"])

    tickers = ["SPY", "AAA", "BBB", "CCC"]
    frames = {
        t: synthetic_frame(i, 900, date(2011, 1, 3)) for i, t in enumerate(tickers)
    }
    monkeypatch.setattr(
        "screener.providers.alpaca.AlpacaProvider",
        lambda *a, **k: FakeProvider(frames),
    )
    result = runner.invoke(
        cli.app,
        ["ingest", "--symbols", ",".join(tickers), "--start", "2011-01-01",
         "--end", "2015-12-31"],
    )
    assert result.exit_code == 0, result.output
    return cli, runner


def test_backtest_runs_on_the_development_split(loaded):
    cli, runner = loaded

    result = runner.invoke(
        cli.app,
        ["backtest", "run", "--hypothesis", "h2", "--split", "development",
         "--random-iterations", "50"],
    )

    assert result.exit_code == 0, result.output
    assert "candidate signal" in result.output
    assert "Pre-registered criteria" in result.output
    assert "proves nothing" in result.output       # development carries no weight


def test_every_hypothesis_runs(loaded):
    cli, runner = loaded
    for hypothesis in ("h1", "h2", "h3", "h4"):
        result = runner.invoke(
            cli.app,
            ["backtest", "run", "--hypothesis", hypothesis, "--split", "development",
             "--random-iterations", "0"],
        )
        assert result.exit_code == 0, f"{hypothesis}: {result.output}"


def test_unknown_hypothesis_is_a_clean_error(loaded):
    cli, runner = loaded
    result = runner.invoke(
        cli.app, ["backtest", "run", "--hypothesis", "h9", "--split", "development"]
    )
    assert result.exit_code == 1
    assert "Unknown hypothesis" in result.output


def test_evidential_split_requires_explicit_confirmation(loaded):
    """Spending budget must be a deliberate act, not a default."""
    cli, runner = loaded
    result = runner.invoke(
        cli.app,
        ["backtest", "run", "--hypothesis", "h2", "--split", "validation",
         "--random-iterations", "0"],
    )
    assert result.exit_code == 1
    assert "--confirm-spend" in result.output


def test_test_split_budget_is_spent_once_and_then_refuses(loaded):
    cli, runner = loaded
    base = ["backtest", "run", "--hypothesis", "h3", "--split", "test",
            "--random-iterations", "0", "--confirm-spend"]

    first = runner.invoke(cli.app, [*base, "--r-multiple", "2.0"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(cli.app, [*base, "--r-multiple", "1.5"])
    assert second.exit_code == 1
    assert "already spent" in second.output


def test_identical_configuration_can_be_reproduced(loaded):
    cli, runner = loaded
    args = ["backtest", "run", "--hypothesis", "h4", "--split", "test",
            "--random-iterations", "0", "--confirm-spend", "--r-multiple", "2.0"]

    assert runner.invoke(cli.app, args).exit_code == 0
    assert runner.invoke(cli.app, args).exit_code == 0, "reproduction must not be blocked"


def test_budget_command_lists_what_was_spent(loaded):
    cli, runner = loaded
    runner.invoke(
        cli.app,
        ["backtest", "run", "--hypothesis", "h2", "--split", "development",
         "--random-iterations", "0"],
    )

    result = runner.invoke(cli.app, ["backtest", "budget"])
    assert result.exit_code == 0, result.output
    assert "h2" in result.output
    assert "development" in result.output


def test_budget_command_is_clear_when_nothing_has_run(cli_env):
    runner = CliRunner()
    runner.invoke(cli_env.app, ["db", "init"])
    result = runner.invoke(cli_env.app, ["backtest", "budget"])
    assert result.exit_code == 0
    assert "No research runs" in result.output


def test_h1_defaults_to_its_specified_exits(loaded):
    """docs/03 H1 exits on TIME or STOP and specifies no profit target.
    Applying the shared 2R default would test something the spec does not
    describe -- and the config is recorded, so the record would be wrong too."""
    cli, runner = loaded
    runner.invoke(
        cli.app,
        ["backtest", "run", "--hypothesis", "h1", "--split", "development",
         "--random-iterations", "0", "--hold", "7"],
    )

    result = runner.invoke(cli.app, ["backtest", "budget", "--hypothesis", "h1"])
    assert result.exit_code == 0, result.output

    from sqlalchemy import select

    from screener.db.models import ResearchRun
    from screener.db.session import session_scope

    with session_scope() as session:
        run = session.scalars(
            select(ResearchRun).where(ResearchRun.hypothesis == "h1")
        ).first()

    import json
    config = json.loads(run.config_json)
    assert config["r_multiple"] is None, "H1 must not carry a profit target by default"
    assert config["time_limit"] == 7, "--hold must drive H1's time exit"


def test_pattern_hypotheses_keep_their_r_target_default(loaded):
    cli, runner = loaded
    runner.invoke(
        cli.app,
        ["backtest", "run", "--hypothesis", "h2", "--split", "development",
         "--random-iterations", "0"],
    )

    import json

    from sqlalchemy import select

    from screener.db.models import ResearchRun
    from screener.db.session import session_scope

    with session_scope() as session:
        run = session.scalars(
            select(ResearchRun).where(ResearchRun.hypothesis == "h2")
        ).first()

    assert json.loads(run.config_json)["r_multiple"] == 2.0


def test_surface_sweeps_and_classifies(loaded):
    cli, runner = loaded

    result = runner.invoke(
        cli.app,
        ["backtest", "surface", "--hypothesis", "h2", "--split", "development",
         "--vary", "r_multiple=1.0,2.0,3.0", "--vary", "time_limit=5,10"],
    )

    assert result.exit_code == 0, result.output
    assert "6 configuration(s)" in result.output
    assert "parameter surface" in result.output
    assert any(word in result.output for word in ("PLATEAU", "SPIKE", "NONE"))


def test_surface_is_refused_on_an_evidential_split(loaded):
    """A sweep would spend a 3-configuration budget in one command, without
    anyone deciding to spend it."""
    cli, runner = loaded

    result = runner.invoke(
        cli.app,
        ["backtest", "surface", "--hypothesis", "h2", "--split", "validation",
         "--vary", "r_multiple=1.0,2.0"],
    )

    assert result.exit_code == 1
    assert "development-split only" in result.output


def test_surface_rejects_an_unknown_parameter(loaded):
    cli, runner = loaded

    result = runner.invoke(
        cli.app,
        ["backtest", "surface", "--hypothesis", "h2",
         "--vary", "sharpe_target=1.0,2.0"],
    )

    assert result.exit_code == 1
    assert "Unknown parameter" in result.output


def test_every_surface_cell_is_recorded_in_the_research_log(loaded):
    """Exploration that leaves no trace is exploration nobody can audit."""
    cli, runner = loaded
    runner.invoke(
        cli.app,
        ["backtest", "surface", "--hypothesis", "h3", "--split", "development",
         "--vary", "r_multiple=1.0,2.0,3.0"],
    )

    from sqlalchemy import func, select

    from screener.db.models import ResearchRun
    from screener.db.session import session_scope

    with session_scope() as session:
        count = session.scalar(
            select(func.count()).select_from(ResearchRun).where(
                ResearchRun.hypothesis == "h3", ResearchRun.notes == "surface sweep"
            )
        )
    assert count == 3
