"""The development-split battery.

Every experiment here is declared BEFORE it runs, with the question it answers
written next to it. That ordering matters: an experiment whose question is
written afterwards is a description of whatever the data happened to show.

Structural questions and parameter questions are kept apart
(docs/03-HYPOTHESES.md 0.7). Parameter questions get a surface and a plateau
test. Structural questions -- does the trend filter help, does displacement
matter, is the stop costing money -- are discrete alternatives, each reported
on its own rather than folded into a grid and maximised over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from ..backtest.runner import RunConfig, _entry_key, build_candidates, evaluate
from ..backtest.splits import Split
from ..backtest.surface import Cell, SurfaceVerdict, analyse, parameter_grid


@dataclass(frozen=True)
class Experiment:
    name: str
    hypothesis: str
    question: str
    vary: dict[str, list[Any]]
    base: dict[str, Any] = field(default_factory=dict)
    kind: str = "parameter"          # "parameter" | "structural"

    @property
    def size(self) -> int:
        return len(parameter_grid(self.vary))


@dataclass
class ExperimentResult:
    experiment: Experiment
    cells: list[Cell]
    verdict: SurfaceVerdict


# --------------------------------------------------------------------------
# The battery
# --------------------------------------------------------------------------

EXIT_SURFACE = {
    "r_multiple": [1.0, 1.5, 2.0, 2.5, 3.0],
    "time_limit": [5, 10, 15, 20],
}

BATTERY: tuple[Experiment, ...] = (
    # -- H1, the control -----------------------------------------------------
    Experiment(
        name="h1_exits",
        hypothesis="h1",
        question="Is there any hold horizon and stop width at which momentum "
                 "rotation is profitable?",
        vary={"hold": [3, 5, 10, 20], "stop_atr": [1.0, 1.5, 2.0, 2.5, 3.0]},
    ),
    Experiment(
        name="h1_no_stop",
        hypothesis="h1",
        question="Is the STOP what loses the money? Same entries, no stop.",
        vary={"hold": [5, 10, 20, 40]},
        base={"use_stop": False},
        kind="structural",
    ),
    Experiment(
        name="h1_selection",
        hypothesis="h1",
        question="Does the momentum lookback or the selection cutoff matter, "
                 "holding exits fixed?",
        vary={"rs_lookback": [21, 63, 126, 252], "top_pct": [0.05, 0.10, 0.20]},
        base={"hold": 20, "stop_atr": 3.0},
    ),
    Experiment(
        name="h1_trend_filter",
        hypothesis="h1",
        question="Does requiring an uptrend help, or is it just fewer trades?",
        vary={"trend_filter": [True, False]},
        base={"hold": 20, "stop_atr": 3.0},
        kind="structural",
    ),

    # -- H2, fair value gap --------------------------------------------------
    Experiment(
        name="h2_exits",
        hypothesis="h2",
        question="Is there a target and holding period at which the FVG "
                 "continuation is profitable?",
        vary=dict(EXIT_SURFACE),
    ),
    Experiment(
        name="h2_no_stop",
        hypothesis="h2",
        question="Same entries with no stop -- entry rule or exit design?",
        vary={"time_limit": [5, 10, 20, 40]},
        base={"use_stop": False, "r_multiple": 0},
        kind="structural",
    ),
    Experiment(
        name="h2_displacement",
        hypothesis="h2",
        question="Does the displacement filter contribute anything? "
                 "'off' is the null the specification leaves live.",
        vary={"displacement": [None, 1.0, 1.5, 2.0]},
        base={"r_multiple": 3.0, "time_limit": 20},
        kind="structural",
    ),

    # -- H3, sweep and reclaim ----------------------------------------------
    Experiment(
        name="h3_exits",
        hypothesis="h3",
        question="Is there a target and holding period at which sweep-reclaim "
                 "is profitable?",
        vary=dict(EXIT_SURFACE),
    ),
    Experiment(
        name="h3_no_stop",
        hypothesis="h3",
        question="Same entries with no stop -- entry rule or exit design?",
        vary={"time_limit": [5, 10, 20, 40]},
        base={"use_stop": False, "r_multiple": 0},
        kind="structural",
    ),
    Experiment(
        name="h3_lookback",
        hypothesis="h3",
        question="Which liquidity reference is swept? Varying the lookback is "
                 "the cheapest version of that question.",
        vary={"sweep_lookback": [5, 10, 20, 40]},
        base={"r_multiple": 3.0, "time_limit": 20},
        kind="structural",
    ),

    # -- Exit design, isolated from portfolio competition --------------------
    # The first live no-stop run looked decisive: H3 went from -0.121R to
    # +0.485R. But its trade count fell from 651 to 203 and cash rejections
    # rose from 239 to 605 -- longer holds occupy the five slots for longer, so
    # the two arms took DIFFERENT signals. That comparison measures exit rule
    # and selection together.
    #
    # These shrink per-trade risk and the concentration cap until nearly every
    # signal fits, so both arms see the same trades and the only difference is
    # the exit.
    #
    # Shrinking risk is necessary, not incidental: at 1% risk with a 2-ATR stop
    # a position is 25-33% of equity on a typical large cap, so the 25%
    # concentration cap binds on almost every trade and four positions exhaust
    # a cash account. Raising the slot count alone changes nothing.
    *[
        Experiment(
            name=f"{h}_exit_isolated",
            hypothesis=h,
            question="With portfolio competition removed so both arms take the "
                     "same signals, does the stop help or cost?",
            vary={"use_stop": [True, False]},
            base={
                "equity": 5_000_000.0,
                "max_positions": 60,
                "max_open_risk_pct": 0.60,
                "risk_pct_per_trade": 0.0005,
                "max_position_pct": 0.015,
                "time_limit": 20,
                "r_multiple": 0,
            },
            kind="structural",
        )
        for h in ("h1", "h2", "h3", "h4")
    ],

    # -- H4, inverse fair value gap -----------------------------------------
    Experiment(
        name="h4_exits",
        hypothesis="h4",
        question="Is there a target and holding period at which the inverted "
                 "gap is profitable?",
        vary=dict(EXIT_SURFACE),
    ),
    Experiment(
        name="h4_no_stop",
        hypothesis="h4",
        question="Same entries with no stop -- entry rule or exit design?",
        vary={"time_limit": [5, 10, 20, 40]},
        base={"use_stop": False, "r_multiple": 0},
        kind="structural",
    ),
)

# --------------------------------------------------------------------------
# Round 2
# --------------------------------------------------------------------------
# Admitted after Round 1 returned no positive configuration in 40 sweeps. Each
# was chosen for having published evidence behind it, NOT for looking promising
# in our own failed results -- picking follow-ups out of a failed search is how
# a null result gets mined into a false positive.
#
# Three hypotheses, not ten. New hypotheses carry their own multiple-comparisons
# cost at the hypothesis level, and testing twenty ideas to report the one that
# survives validation is the same error as testing twenty parameters.

ROUND_2_BATTERY: tuple[Experiment, ...] = (
    Experiment(
        name="h5_momentum_canonical",
        hypothesis="h5",
        question="Does 12-1 momentum -- the version with decades of replication "
                 "-- work where H1's 63-day no-skip variant did not?",
        vary={"hold": [21, 63, 126], "top_pct": [0.05, 0.10, 0.20]},
        base={"stop_atr": 3.0, "monthly_rebalance": True},
    ),
    Experiment(
        name="h5_skip_matters",
        hypothesis="h5",
        question="Is the skip month load-bearing, or decoration? skip=0 is "
                 "H1's formation; skip=21 is the literature's.",
        vary={"mom_skip": [0, 5, 21, 42]},
        base={"hold": 63, "stop_atr": 3.0},
        kind="structural",
    ),
    Experiment(
        name="h5_no_stop",
        hypothesis="h5",
        question="Does momentum survive without a stop, as the literature's "
                 "version has none at all?",
        vary={"hold": [21, 63, 126]},
        base={"use_stop": False, "top_pct": 0.10},
        kind="structural",
    ),
    Experiment(
        name="h5_rebalance",
        hypothesis="h5",
        question="Monthly versus daily rebalancing -- does the documented "
                 "frequency matter, or is it convention?",
        vary={"monthly_rebalance": [True, False]},
        base={"hold": 63, "stop_atr": 3.0},
        kind="structural",
    ),
    Experiment(
        name="h7_squeeze_exits",
        hypothesis="h7",
        question="Is there a target and holding period where range expansion "
                 "after compression is profitable?",
        vary=dict(EXIT_SURFACE),
    ),
    Experiment(
        name="h7_compression_depth",
        hypothesis="h7",
        question="How quiet must it get first? A threshold that only works at "
                 "one depth is a threshold fitted to noise.",
        vary={"squeeze_percentile": [0.10, 0.20, 0.30, 0.40]},
        base={"r_multiple": 3.0, "time_limit": 20},
    ),
    Experiment(
        name="h7_no_stop",
        hypothesis="h7",
        question="Same entries with no stop -- entry rule or exit design?",
        vary={"time_limit": [5, 10, 20, 40]},
        base={"use_stop": False, "r_multiple": 0},
        kind="structural",
    ),
)

# Requires earnings dates, so it is kept separate and skipped when absent
# rather than failing the whole battery.
EARNINGS_BATTERY: tuple[Experiment, ...] = (
    Experiment(
        name="h6_drift_exits",
        hypothesis="h6",
        question="Does price drift after an earnings filing, and over what "
                 "horizon?",
        vary={"time_limit": [5, 10, 20, 40, 60]},
        base={"use_stop": False, "r_multiple": 0},
    ),
    Experiment(
        name="h6_reaction_size",
        hypothesis="h6",
        question="Does the size of the reaction sort the drift? The literature "
                 "sorts on surprise; this substitutes the market's response.",
        vary={"reaction_pct": [0.0, 0.02, 0.03, 0.05, 0.08]},
        base={"time_limit": 40, "use_stop": False, "r_multiple": 0},
    ),
    Experiment(
        name="h6_entry_delay",
        hypothesis="h6",
        question="How much of the drift is gone by the time we could act? "
                 "A day-one edge that vanishes by day three is not tradeable.",
        vary={"entry_delay": [1, 2, 3, 5]},
        base={"time_limit": 40, "use_stop": False, "r_multiple": 0},
    ),
)


ALL_BATTERIES = {
    "round1": BATTERY,
    "round2": ROUND_2_BATTERY,
    "earnings": EARNINGS_BATTERY,
}


def battery_size(battery=BATTERY) -> int:
    return sum(experiment.size for experiment in battery)


def select_battery(name: str) -> tuple[Experiment, ...]:
    key = name.strip().lower()
    if key == "all":
        return BATTERY + ROUND_2_BATTERY + EARNINGS_BATTERY
    if key not in ALL_BATTERIES:
        raise ValueError(
            f"unknown battery {name!r}; expected all, {', '.join(ALL_BATTERIES)}"
        )
    return ALL_BATTERIES[key]


def run_experiment(
    experiment: Experiment,
    bars_by_symbol: dict[str, pd.DataFrame],
    split: Split,
    *,
    equity: float = 10_000.0,
    slippage_bps: float = 5.0,
    universe=None,
    random_iterations: int = 0,
    seed: int = 0,
    events_by_symbol: dict[str, list] | None = None,
    on_cell=None,
) -> ExperimentResult:
    """Run every cell of one experiment.

    Signals depend only on entry-side parameters, so cells sharing them share
    one generation pass -- on an exit-only surface that is a single pass rather
    than one per cell.
    """
    from ..backtest.strategies import always_in_universe

    universe = universe or always_in_universe
    cells: list[Cell] = []
    cache: dict[tuple, list] = {}

    for params in parameter_grid(experiment.vary):
        # base may override the run-wide defaults -- the isolation
        # experiments need a bigger account and more slots than the profile.
        fields = {
            "hypothesis": experiment.hypothesis,
            "equity": equity,
            "slippage_bps": slippage_bps,
            **experiment.base,
            **params,
        }
        config = RunConfig(**fields)
        entry_key = _entry_key(config)
        if entry_key not in cache:
            cache[entry_key] = build_candidates(
                bars_by_symbol, config, universe, events_by_symbol=events_by_symbol
            )

        outcome = evaluate(
            cache[entry_key], bars_by_symbol, config, split,
            random_iterations=random_iterations, seed=seed,
        )
        cells.append(Cell(params=params, outcome=outcome))
        if on_cell is not None:
            on_cell()

    return ExperimentResult(
        experiment=experiment,
        cells=cells,
        verdict=analyse(cells, experiment.vary),
    )


def run_battery(
    session: Session,
    bars_by_symbol: dict[str, pd.DataFrame],
    split: Split,
    *,
    battery=BATTERY,
    record=True,
    **kwargs,
) -> list[ExperimentResult]:
    """Run the whole battery, recording every cell in the research log.

    Recorded even though development runs carry no evidential weight: the log
    of what was explored is what makes the eventual choice reviewable rather
    than a story told afterwards.
    """
    from ..backtest import budget

    results = []
    for experiment in battery:
        result = run_experiment(experiment, bars_by_symbol, split, **kwargs)
        if record:
            for cell in result.cells:
                budget.record(
                    session,
                    hypothesis=experiment.hypothesis,
                    split=split,
                    config=cell.outcome.config.as_dict(),
                    trades=cell.outcome.stats.trades,
                    expectancy_r=cell.outcome.stats.expectancy_r,
                    profit_factor=cell.outcome.stats.profit_factor,
                    max_drawdown_pct=cell.outcome.stats.max_drawdown_pct,
                    total_return_pct=cell.outcome.stats.total_return_pct,
                    random_percentile=cell.outcome.random_percentile,
                    criteria_passed=cell.outcome.passed,
                    notes=f"battery:{experiment.name}",
                )
        results.append(result)
    return results
