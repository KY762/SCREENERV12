"""Surface classification.

The rule being enforced (docs/03 0.7) is counterintuitive and easy to quietly
abandon: the value chosen is the CENTRE of a plateau, deliberately not the
best-performing cell. These tests exist to make abandoning it noisy.
"""

from __future__ import annotations

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
