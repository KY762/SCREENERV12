"""Data splits and regime buckets.

The three-way split (docs/03-HYPOTHESES.md 0.4) is the mechanism that lets the
specification be explored honestly and confirmed strictly at the same time:

    development   unlimited exploration -- carries NO evidential weight
    validation    3 configurations per hypothesis
    test          1 configuration per hypothesis, ONCE

The dates live here rather than in the caller so that no run can quietly widen
its own window. A backtest asks for a split by name; it does not get to choose
what that name means.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Split:
    name: str
    start: date
    end: date
    config_budget: int | None      # None = unlimited
    carries_evidence: bool

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def describe(self) -> str:
        budget = "unlimited" if self.config_budget is None else f"{self.config_budget} config(s)"
        weight = "evidential" if self.carries_evidence else "exploratory -- proves nothing"
        return f"{self.name}: {self.start} to {self.end}, {budget}, {weight}"


DEVELOPMENT = Split("development", date(2010, 1, 1), date(2015, 12, 31), None, False)
VALIDATION = Split("validation", date(2016, 1, 1), date(2019, 12, 31), 3, True)
TEST = Split("test", date(2020, 1, 1), date(2026, 6, 30), 1, True)

SPLITS: dict[str, Split] = {s.name: s for s in (DEVELOPMENT, VALIDATION, TEST)}


def get_split(name: str) -> Split:
    try:
        return SPLITS[name.strip().lower()]
    except KeyError:
        raise ValueError(
            f"unknown split {name!r}; expected one of {', '.join(SPLITS)}"
        ) from None


# Regime buckets for robustness reporting (docs/03-HYPOTHESES.md 0.4).
# Success requires positive results in at least 3 of 5, none worse than -15%.
@dataclass(frozen=True)
class Regime:
    name: str
    start: date
    end: date


REGIMES: tuple[Regime, ...] = (
    Regime("chop_2011", date(2011, 1, 1), date(2011, 12, 31)),
    Regime("bull_2013_2014", date(2013, 1, 1), date(2014, 12, 31)),
    Regime("chop_2015", date(2015, 1, 1), date(2015, 12, 31)),
    Regime("bull_2017", date(2017, 1, 1), date(2017, 12, 31)),
    Regime("correction_2018q4", date(2018, 10, 1), date(2018, 12, 31)),
    Regime("bull_2019", date(2019, 1, 1), date(2019, 12, 31)),
    Regime("crash_2020", date(2020, 2, 1), date(2020, 4, 30)),
    Regime("bear_2022", date(2022, 1, 1), date(2022, 12, 31)),
    Regime("bull_2023_2024", date(2023, 1, 1), date(2024, 12, 31)),
)


def regime_for(day: date) -> str | None:
    """Name of the regime bucket containing ``day``, if any.

    Buckets do not tile the calendar -- most days belong to no bucket. That is
    intentional: the buckets name periods with a recognised character, and
    inventing a label for every other day would manufacture structure.
    """
    for regime in REGIMES:
        if regime.start <= day <= regime.end:
            return regime.name
    return None
