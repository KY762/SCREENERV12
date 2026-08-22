"""The battery, end to end on synthetic data.

Checks the machinery, not the finance: that every declared experiment runs,
that the report contains every one of them including the empty-handed ones,
and that the JSON carries the numbers so they need not be re-typed.
"""

from __future__ import annotations

import json

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
        assert experiment.hypothesis in {"h1", "h2", "h3", "h4"}
        assert experiment.vary, f"{experiment.name} varies nothing"


def test_battery_covers_all_four_hypotheses():
    assert {e.hypothesis for e in BATTERY} == {"h1", "h2", "h3", "h4"}


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
    assert isolated == {"h1", "h2", "h3", "h4"}

    for experiment in BATTERY:
        if not experiment.name.endswith("_exit_isolated"):
            continue
        assert experiment.vary == {"use_stop": [True, False]}
        assert experiment.base["max_positions"] > 5
        assert experiment.base["equity"] > 10_000
