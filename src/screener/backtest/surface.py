"""Parameter surfaces and plateau detection.

Implements the method in docs/03-HYPOTHESES.md 0.7, which exists because the
obvious alternative -- test the range, keep the best value -- fits noise by
construction:

    PLATEAU   a broad contiguous region of positive expectancy
              -> consistent with a real effect; take the CENTRE, not the peak

    SPIKE     one value works, its neighbours do not
              -> consistent with noise; reject the parameter AND question the
                 hypothesis

    NO REGION no positive cell at all
              -> evidence against the hypothesis, not an invitation to search
                 a wider range

The centre of a plateau is deliberately worse in-sample than the peak. That is
the point: the peak's advantage over its neighbours is the part most likely to
be noise, and it is exactly the part that does not survive out of sample.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from typing import Any

from . import inference
from .runner import Outcome

# Pre-registered constants, not arguments (non-negotiable #4).
#
# How many standard errors the gap between two arms must clear before either is
# selectable. 2.0 is the conventional two-sided 95% bar; it is stated here so
# moving it after seeing a number is a visible edit rather than a keyword.
SEPARATION_Z = 2.0
# Divergence in trade count above which a use_stop comparison is measuring
# selection as well as exit design. Mirrors report.py, which prints the warning.
ISOLATION_TOLERANCE = 0.25


@dataclass(frozen=True)
class Cell:
    """One configuration's place on the surface."""

    params: dict[str, Any]
    outcome: Outcome

    @property
    def expectancy(self) -> float:
        return self.outcome.stats.expectancy_r

    @property
    def key(self) -> tuple:
        return tuple(sorted(self.params.items()))


def parameter_grid(varied: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Cartesian product of the varied parameters, in a stable order."""
    if not varied:
        return [{}]
    names = sorted(varied)
    return [
        dict(zip(names, values, strict=True))
        for values in product(*(varied[name] for name in names))
    ]


@dataclass
class SurfaceVerdict:
    shape: str                     # "plateau" | "spike" | "none"
    best: Cell | None
    recommended: Cell | None       # plateau centre -- NOT the best cell
    positive_cells: int
    total_cells: int
    detail: str

    def describe(self) -> str:
        return f"{self.shape.upper()}: {self.detail}"


def _neighbours(
    params: dict[str, Any], varied: dict[str, list[Any]]
) -> list[dict[str, Any]]:
    """Configurations one step away along exactly one varied axis."""
    out = []
    for name, values in varied.items():
        index = values.index(params[name])
        for step in (-1, 1):
            j = index + step
            if 0 <= j < len(values):
                out.append({**params, name: values[j]})
    return out


def _compare_arms(cells: list[Cell]) -> SurfaceVerdict:
    """Verdict for a two-arm structural question.

    REPLACEMENT CRITERION, pending operator sign-off. Three things must hold
    before one arm is selectable over the other:

    1. The winner is positive.
    2. The gap between the arms is larger than the noise in the gap. The random
       benchmark cannot supply this -- it says whether an ARM beats random, not
       whether one arm beats THE OTHER. Resting on it alone called a +0.004R
       h1_trend_filter difference "separated". The test is on mean per-trade
       return with month-clustered standard errors, and it is PAIRED where the
       arms took the same signals (use_stop comparisons) -- see below.
    3. The winner also beats random selection on its own entry dates, so the
       gap is not two arms being equally bad in a rising market.

    Plus a veto: a use_stop comparison whose arms took materially different
    trade counts is not an exit-rule comparison at all, and no amount of
    separation rescues it. Without the veto h2_exit_isolated came back
    selectable at 27.3% divergence.

    Clustering by entry month charges for trades opened together, not for
    trades opened apart and held through the same stretch, so the standard
    errors may still be somewhat optimistic. On the development split this is
    a reason to pre-register a test, never a result.
    """
    ranked = sorted(cells, key=lambda c: -c.expectancy)
    best, other = ranked[0], ranked[1]

    def rank_of(cell: Cell) -> float | None:
        pct = getattr(cell.outcome, "date_matched_percentile", None)
        return pct if pct is not None else cell.outcome.random_percentile

    def arm(cell: Cell) -> str:
        return ", ".join(f"{k}={v}" for k, v in sorted(cell.params.items())) or "arm"

    best_rank, delta = rank_of(best), best.expectancy - other.expectancy
    positive = sum(1 for c in cells if c.expectancy > 0)
    margin = (
        f"{arm(best)} at {best.expectancy:+.3f}R versus "
        f"{arm(other)} at {other.expectancy:+.3f}R, a gap of {delta:+.3f}R"
    )

    def verdict(shape: str, recommended: Cell | None, detail: str) -> SurfaceVerdict:
        return SurfaceVerdict(
            shape=shape, best=best, recommended=recommended,
            positive_cells=positive, total_cells=2, detail=detail,
        )

    if best.expectancy <= 0:
        return verdict("none", None, (
            f"neither arm produced positive expectancy -- {margin}. The "
            "comparison still says which is less bad, but nothing here is "
            "selectable."
        ))

    # Veto: arms that did not take the same trades are not an exit comparison.
    if set(best.params) == {"use_stop"}:
        counts = [c.outcome.stats.trades for c in cells]
        if min(counts) > 0:
            spread = (max(counts) - min(counts)) / max(counts)
            if spread > ISOLATION_TOLERANCE:
                return verdict("indistinct", None, (
                    f"{margin}, but the arms differ by {spread:.1%} in trade "
                    f"count ({min(counts):,} vs {max(counts):,}). They did not "
                    "take the same signals, so this measures exit design and "
                    "selection together and the gap is not attributable to the "
                    "exit rule."
                ))

    # Is the gap bigger than the noise in the gap?
    #
    # Exit arms took the same signals, so they are compared PAIRED: each
    # no-stop trade against its stop twin, same stock, same day. Most of a
    # trade's return is the stock's own move, which both twins share; an
    # unpaired test counts that as noise and put h1's exit gap at 1.1 SE when
    # the paired figure is 2.9. Arms that took different signals -- a filter on
    # or off, a different rebalance -- have no twins, so they are compared as
    # two independent means. Both use month-clustered standard errors.
    z, test = None, None
    log_best = getattr(best.outcome, "trade_log", ())
    log_other = getattr(other.outcome, "trade_log", ())
    if set(best.params) == {"use_stop"} and log_best and log_other:
        diff = inference.paired(log_best, log_other)
        if diff.n >= 2 and not math.isnan(diff.se):
            # A zero SE means every pair differed by the same amount: perfectly
            # consistent, not unmeasured. Treating 0 as missing once dropped
            # this through to the unpaired test, which answered the opposite.
            if diff.se == 0:
                z = math.copysign(math.inf, diff.mean) if diff.mean else 0.0
            else:
                z = diff.mean / diff.se
            test = f"paired over {diff.n:,} shared signals"
    if z is None:
        se_best = getattr(best.outcome, "mean_return_se", None)
        se_other = getattr(other.outcome, "mean_return_se", None)
        mu_best = getattr(best.outcome, "mean_return", None)
        mu_other = getattr(other.outcome, "mean_return", None)
        if None not in (se_best, se_other, mu_best, mu_other):
            se_gap = math.hypot(se_best, se_other)
            if se_gap > 0:
                z, test = (mu_best - mu_other) / se_gap, "unpaired"

    if z is not None and z < SEPARATION_Z:
        return verdict("indistinct", None, (
            f"{margin}, but that gap is {z:.1f} standard errors on mean "
            f"per-trade return ({test}, month-clustered) -- under the "
            f"{SEPARATION_Z:.0f} required."
        ))

    if best_rank is None or best_rank < 50:
        rank_txt = (
            "was not ranked" if best_rank is None
            else f"sits at the {best_rank:.0f}th percentile"
        )
        return verdict("indistinct", None, (
            f"{margin}. But the winning arm {rank_txt} against random selection "
            "on its own entry dates, so beating the other arm is not evidence "
            "of an edge -- both are losing to a coin toss and one loses by less."
        ))

    strength = f" at {z:.1f} standard errors ({test}, month-clustered)" if z is not None else ""
    return verdict("separated", best, (
        f"{margin}{strength}, and the winning arm beats random selection on its "
        f"own entry dates at the {best_rank:.0f}th percentile. Development "
        "split: a question worth pre-registering, not a settled result."
    ))


def analyse(cells: list[Cell], varied: dict[str, list[Any]]) -> SurfaceVerdict:
    """Classify the surface and pick a value, per docs/03 0.7.

    ``min_trades`` is not applied here: a cell with too few trades fails the
    pre-registered trade-count criterion on its own, and hiding it would make
    the surface look smoother than it is.
    """
    # A two-cell grid is an A/B, not a surface. The plateau test asks whether a
    # positive cell has positive NEIGHBOURS, and across two cells the only
    # neighbour a winner has is the loser -- so SPIKE is returned whenever the
    # comparison separates at all, which is the thing an A/B is for. Every
    # *_exit_isolated arm except h5's was unselectable by construction rather
    # than by evidence. Rule below; docs/03 0.7 rules 3 and 4 do not apply here.
    if len(cells) == 2:
        return _compare_arms(cells)

    by_key = {cell.key: cell for cell in cells}
    positive = [c for c in cells if c.expectancy > 0]

    if not positive:
        return SurfaceVerdict(
            shape="none",
            best=max(cells, key=lambda c: c.expectancy) if cells else None,
            recommended=None,
            positive_cells=0,
            total_cells=len(cells),
            detail=(
                f"no configuration of {len(cells)} produced positive expectancy. "
                "Per docs/03 0.7 rule 4 this is evidence against the hypothesis, "
                "not an invitation to widen the search."
            ),
        )

    best = max(cells, key=lambda c: c.expectancy)

    # A plateau is a positive cell whose neighbours are also positive.
    plateau_members = []
    for cell in positive:
        neighbours = _neighbours(cell.params, varied)
        if not neighbours:
            continue
        found = [
            by_key.get(tuple(sorted(n.items()))) for n in neighbours
        ]
        found = [c for c in found if c is not None]
        if found and all(c.expectancy > 0 for c in found):
            plateau_members.append(cell)

    if not plateau_members:
        return SurfaceVerdict(
            shape="spike",
            best=best,
            recommended=None,
            positive_cells=len(positive),
            total_cells=len(cells),
            detail=(
                f"{len(positive)} of {len(cells)} cells positive, but no positive cell "
                "has positive neighbours. One value working while its neighbours fail "
                "is what noise looks like. Per docs/03 0.7 rule 3, the peak is not "
                "selectable."
            ),
        )

    # Centre of the plateau: the member with the most positive neighbours, ties
    # broken toward the middle of each varied range rather than toward the peak.
    def centrality(cell: Cell) -> tuple:
        neighbours = [
            by_key.get(tuple(sorted(n.items())))
            for n in _neighbours(cell.params, varied)
        ]
        supported = sum(1 for c in neighbours if c is not None and c.expectancy > 0)
        distance_from_middle = sum(
            abs(values.index(cell.params[name]) - (len(values) - 1) / 2)
            for name, values in varied.items()
        )
        return (supported, -distance_from_middle)

    centre = max(plateau_members, key=centrality)
    return SurfaceVerdict(
        shape="plateau",
        best=best,
        recommended=centre,
        positive_cells=len(positive),
        total_cells=len(cells),
        detail=(
            f"{len(plateau_members)} of {len(positive)} positive cells sit inside a "
            f"positive neighbourhood. Selected the plateau centre "
            f"({_format(centre.params)}, {centre.expectancy:+.3f}R) rather than the "
            f"peak ({_format(best.params)}, {best.expectancy:+.3f}R) -- the peak's "
            "margin over its neighbours is the part least likely to survive."
        ),
    )


def _format(params: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(params.items()))


def parse_vary(specs: list[str]) -> dict[str, list[Any]]:
    """Parse ``--vary name=1,2,3`` into typed value lists."""
    varied: dict[str, list[Any]] = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"expected name=v1,v2,...  got {spec!r}")
        name, raw = spec.split("=", 1)
        values: list[Any] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            values.append(_coerce(token))
        if not values:
            raise ValueError(f"no values given for {name!r}")
        varied[name.strip()] = values
    return varied


def _coerce(token: str) -> Any:
    if token.lower() in {"none", "off", "null"}:
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token
