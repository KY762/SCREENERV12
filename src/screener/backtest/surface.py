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

from dataclasses import dataclass
from itertools import product
from typing import Any

from .runner import Outcome


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


def analyse(cells: list[Cell], varied: dict[str, list[Any]]) -> SurfaceVerdict:
    """Classify the surface and pick a value, per docs/03 0.7.

    ``min_trades`` is not applied here: a cell with too few trades fails the
    pre-registered trade-count criterion on its own, and hiding it would make
    the surface look smoother than it is.
    """
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
