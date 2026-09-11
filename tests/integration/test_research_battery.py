"""The battery, end to end on synthetic data.

Checks the machinery, not the finance: that every declared experiment runs,
that the report contains every one of them including the empty-handed ones,
and that the JSON carries the numbers so they need not be re-typed.
"""

from __future__ import annotations

import json

from screener.backtest.runner import HYPOTHESES
from screener.research.battery import BATTERY, battery_size
from tests.integration.test_backtest_cli import (  # noqa: F401
    cli_env,
    loaded,
    synthetic_frame,
)


def test_every_experiment_declares_its_question():
    """An experiment whose question is written afterwards is a description of
    whatever the data happened to show."""
    for experiment in BATTERY:
        assert "?" in experiment.question, f"{experiment.name} states no question"
        # Checked against the registry rather than a literal, so adding a
        # hypothesis cannot leave this guard quietly describing an older
        # project than the one it is testing.
        assert experiment.hypothesis in HYPOTHESES
        assert experiment.vary, f"{experiment.name} varies nothing"


def test_battery_covers_round_1_and_h5():
    """h6 (earnings drift) and h7 (range expansion) are built and have no
    battery arms yet. Pinned so that stays a visible gap rather than an
    assumption."""
    covered = {e.hypothesis for e in BATTERY}

    assert covered == {"h1", "h2", "h3", "h4", "h5"}
    assert covered < set(HYPOTHESES)
    assert {"h6", "h7"} == set(HYPOTHESES) - covered


def test_every_hypothesis_gets_a_no_stop_diagnostic():
    """The question 'entry rule or exit design?' has to be asked of each."""
    with_stop_test = {
        e.hypothesis for e in BATTERY if e.base.get("use_stop") is False
    }
    assert with_stop_test == {"h1", "h2", "h3", "h4"}


def test_battery_writes_a_report_and_json(loaded, tmp_path):  # noqa: F811
    cli, runner = loaded

    result = runner.invoke(
        cli.app,
        ["research", "explore", "--split", "development",
         "--random-iterations", "0", "--out", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    md = list(tmp_path.glob("*-development-battery.md"))
    js = list(tmp_path.glob("*-development-battery.json"))
    assert len(md) == 1 and len(js) == 1

    text = md[0].read_text()
    for experiment in BATTERY:
        assert experiment.name in text, f"{experiment.name} missing from the report"
        assert experiment.question in text

    payload = json.loads(js[0].read_text())
    assert len(payload["experiments"]) == len(BATTERY)
    assert sum(len(e["cells"]) for e in payload["experiments"]) == battery_size()


def test_report_states_the_development_caveat(loaded, tmp_path):  # noqa: F811
    cli, runner = loaded
    runner.invoke(
        cli.app,
        ["research", "explore", "--split", "development",
         "--random-iterations", "0", "--out", str(tmp_path)],
    )
    text = list(tmp_path.glob("*.md"))[0].read_text()

    assert "no evidential weight" in text
    assert "delisted" in text, "the survivorship caveat must ride along"


def test_battery_is_refused_on_an_evidential_split(loaded, tmp_path):  # noqa: F811
    cli, runner = loaded

    result = runner.invoke(
        cli.app,
        ["research", "explore", "--split", "test", "--out", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "development-split only" in result.output


def test_every_cell_lands_in_the_research_log(loaded, tmp_path):  # noqa: F811
    cli, runner = loaded
    runner.invoke(
        cli.app,
        ["research", "explore", "--split", "development",
         "--random-iterations", "0", "--out", str(tmp_path)],
    )

    from sqlalchemy import func, select

    from screener.db.models import ResearchRun
    from screener.db.session import session_scope

    with session_scope() as session:
        count = session.scalar(
            select(func.count()).select_from(ResearchRun).where(
                ResearchRun.notes.like("battery:%")
            )
        )
    assert count == battery_size()


def test_every_hypothesis_gets_an_isolated_exit_comparison():
    """A stop-vs-no-stop comparison at default portfolio limits measures the
    exit rule AND which signals each arm had room to take. The isolated
    experiments remove the second effect."""
    isolated = {
        e.hypothesis for e in BATTERY if e.name.endswith("_exit_isolated")
    }
    assert isolated == {"h1", "h2", "h3", "h4", "h5"}

    for experiment in BATTERY:
        if not experiment.name.endswith("_exit_isolated"):
            continue
        assert experiment.vary == {"use_stop": [True, False]}
        assert experiment.base["max_positions"] > 5
        assert experiment.base["equity"] > 10_000


def test_h5_exit_isolated_uses_its_own_horizon_not_round_1s():
    """The Round 1 arms pin time_limit at 20. H5's specification is 21 -- a
    month, matching monthly_rebalance. Folding H5 into that loop would have
    run momentum 12-1 on someone else's clock, which is the shared-default
    mistake that voided its first two runs."""
    from screener.research.battery import BATTERY

    arms = {e.name: e for e in BATTERY if e.name.endswith("_exit_isolated")}

    assert set(arms) == {f"h{n}_exit_isolated" for n in range(1, 6)}
    assert arms["h5_exit_isolated"].base["time_limit"] == 21
    for name in ("h1", "h2", "h3", "h4"):
        assert arms[f"{name}_exit_isolated"].base["time_limit"] == 20


def test_every_exit_isolated_arm_shares_the_same_portfolio_settings():
    """The comparison only means something if the arms differ in the exit and
    nothing else. If one arm's slot count or per-trade risk drifts, it stops
    being a controlled experiment and nobody would see it in the output."""
    from screener.research.battery import BATTERY, EXIT_ISOLATED_PORTFOLIO

    for experiment in BATTERY:
        if not experiment.name.endswith("_exit_isolated"):
            continue
        for key, value in EXIT_ISOLATED_PORTFOLIO.items():
            assert experiment.base[key] == value, f"{experiment.name}: {key}"
        assert experiment.vary == {"use_stop": [True, False]}
