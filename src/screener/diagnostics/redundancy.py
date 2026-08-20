"""Indicator redundancy matrix.

From docs/04 section 7. An indicator correlating above the threshold with one
already included contributes a parameter and no information, so it is dropped --
on evidence, not on judgement.

This runs BEFORE any backtest because it is nearly free and can remove
candidates that would otherwise consume variant budget. It can also overrule the
recommendations in docs/04, which is the point: measurement beats opinion.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

DEFAULT_THRESHOLD = 0.85


@dataclass(frozen=True)
class RedundantPair:
    kept: str
    dropped: str
    correlation: float


@dataclass
class RedundancyReport:
    matrix: pd.DataFrame
    threshold: float
    priority: list[str]
    redundant_pairs: list[RedundantPair]
    observations: int

    @property
    def dropped(self) -> list[str]:
        return [p.dropped for p in self.redundant_pairs]

    @property
    def retained(self) -> list[str]:
        return [c for c in self.priority if c not in set(self.dropped)]

    def summary(self) -> str:
        if not self.redundant_pairs:
            return (
                f"No pair exceeds |r| >= {self.threshold:.2f} across "
                f"{self.observations:,} observations; all {len(self.priority)} "
                "indicators retained."
            )
        return (
            f"{len(self.redundant_pairs)} redundant indicator(s) dropped at "
            f"|r| >= {self.threshold:.2f}: " + ", ".join(self.dropped)
        )


def correlation_matrix(frame: pd.DataFrame, method: str = "spearman") -> pd.DataFrame:
    """Pairwise correlation across indicator columns.

    Spearman by default. Indicator distributions are heavily skewed -- RVOL and
    dollar volume especially -- and Pearson on skewed data reports the influence
    of a handful of extreme days rather than the typical relationship.
    """
    numeric = frame.select_dtypes(include=[np.number])
    return numeric.corr(method=method, min_periods=30)


def find_redundant(
    frame: pd.DataFrame,
    priority: list[str] | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    method: str = "spearman",
) -> RedundancyReport:
    """Drop indicators that duplicate a higher-priority one.

    ``priority`` is the keep-order: when two indicators are redundant the
    earlier one survives. Declaring it explicitly matters -- without it the
    survivor would depend on column ordering, which is not a decision anyone
    made.
    """
    matrix = correlation_matrix(frame, method=method)
    columns = priority or list(matrix.columns)
    columns = [c for c in columns if c in matrix.columns]

    pairs: list[RedundantPair] = []
    dropped: set[str] = set()

    for i, kept in enumerate(columns):
        if kept in dropped:
            continue
        for candidate in columns[i + 1 :]:
            if candidate in dropped:
                continue
            r = matrix.loc[kept, candidate]
            if pd.notna(r) and abs(r) >= threshold:
                pairs.append(RedundantPair(kept, candidate, float(r)))
                dropped.add(candidate)

    observations = int(
        frame[columns].notna().all(axis=1).sum() if columns else 0
    )
    return RedundancyReport(
        matrix=matrix,
        threshold=threshold,
        priority=columns,
        redundant_pairs=pairs,
        observations=observations,
    )
