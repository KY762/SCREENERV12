"""Surface classification.

The rule being enforced (docs/03 0.7) is counterintuitive and easy to quietly
abandon: the value chosen is the CENTRE of a plateau, deliberately not the
best-performing cell. These tests exist to make abandoning it noisy.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from screener.backtest.performance import Stats
from screener.backtest.runner import Outcome, RunConfig
from screener.backtest.surface import (
    Cell,
    analyse,
    parameter_grid,
    parse_vary,
)


def cell(expectancy: float, **params) -> Cell:
    stats = Stats(
        trades=250, wins=100, losses=150, win_rate=0.4,
        expectancy_r=expectancy, expectancy_dollars=expectancy * 100,
        profit_factor=1.3 if expectancy > 0 else 0.8,
        gross_profit=1.0, gross_loss=1.0, max_drawdown_pct=0.1,
        total_return_pct=expectancy, avg_bars_held=6.0, exits={},
    )
    outcome = Outcome(
        config=RunConfig(hypothesis="h2"), stats=stats, regimes={},
        candidates=1000, rejected={}, random_percentile=80.0,
    )
    return Cell(params=params, outcome=outcome)


# -- parsing ----------------------------------------------------------------

def test_vary_specs_are_parsed_and_typed():
    varied = parse_vary(["r_multiple=1.0,1.5,2.0", "time_limit=5,10"])

    assert varied == {"r_multiple": [1.0, 1.5, 2.0], "time_limit": [5, 10]}


def test_off_parses_to_none_so_a_filter_can_be_disabled_on_the_surface():
    """'Does displacement matter at all?' needs the OFF case on the grid."""
    assert parse_vary(["displacement=off,1.0,1.5"])["displacement"] == [None, 1.0, 1.5]


def test_a_malformed_spec_is_rejected():
    with pytest.raises(ValueError, match="expected name="):
        parse_vary(["r_multiple"])


def test_grid_is_the_cartesian_product():
    grid = parameter_grid({"a": [1, 2, 3], "b": [10, 20]})
    assert len(grid) == 6
    assert {"a": 2, "b": 20} in grid


# -- classification ---------------------------------------------------------

def test_a_broad_positive_region_is_a_plateau():
    varied = {"r": [1.0, 1.5, 2.0, 2.5, 3.0]}
    cells = [
        cell(-0.05, r=1.0), cell(0.10, r=1.5), cell(0.12, r=2.0),
        cell(0.11, r=2.5), cell(-0.02, r=3.0),
    ]

    verdict = analyse(cells, varied)

    assert verdict.shape == "plateau"
    assert verdict.positive_cells == 3


def test_the_plateau_centre_is_chosen_over_the_peak():
    """The peak's margin over its neighbours is the part least likely to
    survive out of sample. Selecting it is fitting to noise by construction."""
    varied = {"r": [1.0, 1.5, 2.0, 2.5, 3.0]}
    cells = [
        cell(-0.05, r=1.0), cell(0.10, r=1.5), cell(0.12, r=2.0),
        cell(0.30, r=2.5), cell(-0.02, r=3.0),      # 2.5 is the peak
    ]

    verdict = analyse(cells, varied)

    assert verdict.best.params == {"r": 2.5}
    assert verdict.recommended.params == {"r": 2.0}, "centre, not peak"


def test_one_good_value_with_failing_neighbours_is_a_spike():
    varied = {"r": [1.0, 1.5, 2.0, 2.5, 3.0]}
    cells = [
        cell(-0.05, r=1.0), cell(-0.03, r=1.5), cell(0.40, r=2.0),
        cell(-0.04, r=2.5), cell(-0.02, r=3.0),
    ]

    verdict = analyse(cells, varied)

    assert verdict.shape == "spike"
    assert verdict.recommended is None, "a spike must not be selectable"
    assert "noise" in verdict.detail


def test_nothing_positive_is_reported_as_evidence_against():
    varied = {"r": [1.0, 1.5, 2.0]}
    cells = [cell(-0.05, r=1.0), cell(-0.12, r=1.5), cell(-0.09, r=2.0)]

    verdict = analyse(cells, varied)

    assert verdict.shape == "none"
    assert verdict.recommended is None
    assert "evidence against" in verdict.detail
    assert verdict.best.params == {"r": 1.0}, "the least-bad cell is still reported"


def test_a_two_dimensional_plateau_is_found():
    varied = {"r": [1.0, 2.0, 3.0], "t": [5, 10, 15]}
    cells = []
    for r in varied["r"]:
        for t in varied["t"]:
            middle = r == 2.0 and t == 10
            edge = r in (1.0, 3.0) or t in (5, 15)
            cells.append(cell(0.15 if middle else (-0.05 if edge else 0.10), r=r, t=t))

    verdict = analyse(cells, varied)

    assert verdict.shape == "spike", (
        "a single positive cell ringed by negatives is a spike even in 2D"
    )


def test_the_number_of_configurations_tested_is_reported():
    """docs/03 0.7 rule 5: a result selected from 50 trials is weaker evidence
    than the same result from 3, and the reader is entitled to know."""
    varied = {"r": [1.0, 1.5, 2.0]}
    cells = [cell(0.1, r=1.0), cell(0.1, r=1.5), cell(0.1, r=2.0)]

    assert analyse(cells, varied).total_cells == 3


def test_a_configuration_with_no_stop_still_needs_an_exit():
    """Removing the stop is a diagnostic, not a way to hold forever."""
    with pytest.raises(ValueError, match="needs a time limit"):
        RunConfig(hypothesis="h1", use_stop=False, time_limit=0)


# --------------------------------------------------------------------------
# Two-cell questions
#
# The plateau test asks whether a positive cell has positive NEIGHBOURS. Across
# two cells a winner's only neighbour is the loser, so SPIKE came back whenever
# the A/B separated -- which is what an A/B is for. Every *_exit_isolated arm
# except h5's was unselectable by construction rather than by evidence.
# --------------------------------------------------------------------------

def arm(expectancy: float, matched: float | None, se: float = 0.0002,
        mean_return: float | None = None, trades: int = 250, **params) -> Cell:
    """An arm with a noise estimate. `se` defaults small so the separation test
    passes unless a test is specifically about a thin gap."""
    c = cell(expectancy, **params)
    c.outcome.date_matched_percentile = matched
    c.outcome.mean_return = expectancy / 100 if mean_return is None else mean_return
    c.outcome.mean_return_se = se
    c.outcome.stats = replace(c.outcome.stats, trades=trades)
    return c


def test_a_separating_ab_is_no_longer_reported_as_noise():
    verdict = analyse(
        [arm(0.249, 73.0, use_stop=False), arm(0.126, 55.0, use_stop=True)],
        {"use_stop": [True, False]},
    )

    assert verdict.shape == "separated"
    assert verdict.recommended.params == {"use_stop": False}
    assert "+0.123R" in verdict.detail, "the gap between the arms is the finding"


def test_beating_the_other_arm_is_not_enough_when_both_lose_to_random():
    """h4_exit_isolated: +0.294R, the largest no-stop result in the battery,
    at the 11th percentile. Winning an A/B where both arms lose to a coin toss
    is not evidence of an edge."""
    verdict = analyse(
        [arm(0.294, 11.0, use_stop=False), arm(-0.105, 4.0, use_stop=True)],
        {"use_stop": [True, False]},
    )

    assert verdict.shape == "indistinct"
    assert verdict.recommended is None
    assert "11th percentile" in verdict.detail


def test_two_negative_arms_select_nothing():
    verdict = analyse(
        [arm(-0.041, 60.0, use_stop=False), arm(-0.193, 30.0, use_stop=True)],
        {"use_stop": [True, False]},
    )

    assert verdict.shape == "none"
    assert verdict.recommended is None


def test_the_date_matched_rank_is_what_decides_it():
    """The uniform percentile lets the benchmark choose its own entry dates, so
    it scores timing too. Where the two disagree, the matched one governs."""
    flattered = analyse(
        [arm(0.20, 20.0, use_stop=False), arm(0.05, 15.0, use_stop=True)],
        {"use_stop": [True, False]},
    )
    assert flattered.shape == "indistinct", "uniform rank is 80 but matched is 20"


def test_it_falls_back_to_the_uniform_rank_when_unmatched():
    verdict = analyse(
        [arm(0.20, None, use_stop=False), arm(0.05, None, use_stop=True)],
        {"use_stop": [True, False]},
    )
    assert verdict.shape == "separated", "cell() sets uniform percentile to 80"


def test_a_three_cell_grid_still_gets_the_plateau_test():
    """The fix is scoped to two cells. An ordered axis with three or more
    levels has real neighbours and docs/03 0.7 still applies."""
    verdict = analyse(
        [cell(0.1, hold=5), cell(0.2, hold=10), cell(0.15, hold=20)],
        {"hold": [5, 10, 20]},
    )
    assert verdict.shape in {"plateau", "spike", "none"}


def test_a_gap_smaller_than_its_own_noise_is_not_separated():
    """h1_trend_filter came back SEPARATED on +0.004R because the winning arm
    ranked 89th against random. Rank says an arm beat random; it says nothing
    about whether it beat the OTHER arm."""
    verdict = analyse(
        [arm(0.073, 89.0, se=0.004, mean_return=0.0073, trend_filter=False),
         arm(0.069, 89.0, se=0.004, mean_return=0.0069, trend_filter=True)],
        {"trend_filter": [True, False]},
    )

    assert verdict.shape == "indistinct"
    assert verdict.recommended is None
    assert "standard error" in verdict.detail


def test_failed_isolation_vetoes_selection_however_large_the_gap():
    """h2_exit_isolated: a +0.262R gap and a 57th-percentile winner, on arms
    whose trade counts differ by 27%. They did not take the same signals, so
    the gap is not attributable to the exit rule."""
    verdict = analyse(
        [arm(0.150, 57.0, trades=3980, use_stop=False),
         arm(-0.112, 20.0, trades=5475, use_stop=True)],
        {"use_stop": [True, False]},
    )

    assert verdict.shape == "indistinct"
    assert verdict.recommended is None
    assert "did not take the same signals" in verdict.detail


def test_isolation_that_held_does_not_veto():
    verdict = analyse(
        [arm(0.249, 87.0, trades=355, use_stop=False),
         arm(0.126, 60.0, trades=371, use_stop=True)],
        {"use_stop": [True, False]},
    )

    assert verdict.shape == "separated"
    assert verdict.recommended.params == {"use_stop": False}


def test_the_veto_only_applies_to_use_stop_comparisons():
    """A parameter A/B is expected to change trade counts; that is not a
    confound, it is the parameter working."""
    verdict = analyse(
        [arm(0.20, 80.0, trades=100, monthly_rebalance=False),
         arm(0.05, 60.0, trades=900, monthly_rebalance=True)],
        {"monthly_rebalance": [True, False]},
    )

    assert verdict.shape == "separated"
