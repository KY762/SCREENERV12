"""Split budget enforcement.

The three-way split only works if the budget is enforced by something other
than good intentions. docs/03-HYPOTHESES.md 0.8:

    development   unlimited
    validation    3 configurations per hypothesis
    test          1 configuration per hypothesis, ONCE

Re-running a configuration that has already been recorded costs nothing extra --
it produces the same numbers and is a reproduction, not a new look. Running a
DIFFERENT configuration is a new look, and once the budget for a split is spent
it stays spent.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ResearchRun
from .splits import Split


class BudgetExceeded(RuntimeError):
    """Raised instead of running. The budget is not advisory."""


def config_hash(config: dict[str, Any]) -> str:
    """Stable hash of a configuration dict, key order independent."""
    payload = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class BudgetStatus:
    hypothesis: str
    split: str
    spent: int
    limit: int | None
    already_run: bool

    @property
    def remaining(self) -> int | None:
        return None if self.limit is None else max(self.limit - self.spent, 0)

    def describe(self) -> str:
        if self.limit is None:
            return f"{self.hypothesis} on {self.split}: {self.spent} run(s), unlimited"
        return (
            f"{self.hypothesis} on {self.split}: {self.spent}/{self.limit} "
            f"configuration(s) spent"
        )


def status(
    session: Session, hypothesis: str, split: Split, config: dict[str, Any]
) -> BudgetStatus:
    """How much of this split's budget this hypothesis has already spent."""
    digest = config_hash(config)
    hashes = set(
        session.scalars(
            select(ResearchRun.config_hash).where(
                ResearchRun.hypothesis == hypothesis,
                ResearchRun.split == split.name,
            )
        ).all()
    )
    return BudgetStatus(
        hypothesis=hypothesis,
        split=split.name,
        spent=len(hashes),
        limit=split.config_budget,
        already_run=digest in hashes,
    )


def check(
    session: Session, hypothesis: str, split: Split, config: dict[str, Any]
) -> BudgetStatus:
    """Raise ``BudgetExceeded`` if this run would exceed the split's budget."""
    current = status(session, hypothesis, split, config)
    if current.limit is None or current.already_run:
        return current
    if current.spent >= current.limit:
        raise BudgetExceeded(
            f"{hypothesis} has already spent {current.spent} of "
            f"{current.limit} configuration(s) on the {split.name} split. "
            "This is the pre-registered budget from docs/03-HYPOTHESES.md 0.8. "
            "Running another configuration here would make the result "
            "in-sample without saying so."
        )
    return current


def record(
    session: Session,
    *,
    hypothesis: str,
    split: Split,
    config: dict[str, Any],
    trades: int | None = None,
    expectancy_r: float | None = None,
    profit_factor: float | None = None,
    max_drawdown_pct: float | None = None,
    total_return_pct: float | None = None,
    random_percentile: float | None = None,
    criteria_passed: bool | None = None,
    notes: str | None = None,
) -> ResearchRun:
    """Record a run. Called for every run, including the disappointing ones."""
    run = ResearchRun(
        hypothesis=hypothesis,
        split=split.name,
        config_hash=config_hash(config),
        config_json=json.dumps(config, sort_keys=True, default=str),
        trades=trades,
        expectancy_r=expectancy_r,
        profit_factor=_finite(profit_factor),
        max_drawdown_pct=max_drawdown_pct,
        total_return_pct=total_return_pct,
        random_percentile=random_percentile,
        criteria_passed=criteria_passed,
        notes=notes,
    )
    session.add(run)
    session.flush()
    return run


def _finite(value: float | None) -> float | None:
    """An infinite profit factor is stored as NULL -- 'undefined', not 'huge'."""
    if value is None:
        return None
    return value if value not in (float("inf"), float("-inf")) else None
