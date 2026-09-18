"""Standard errors that do not assume trades are independent.

Positions run concurrently in correlated large caps, so a market-wide week moves
many of them together. Dividing by the trade count as if each trade were an
independent draw overstates the evidence. Everything here clusters by the
calendar period a trade was entered in, which charges for that correlation.

Lives in backtest/ rather than diagnostics/ because scoring uses it: the
two-arm verdict needs a noise estimate, and the engine should not depend on the
diagnostics package to get one.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from datetime import date

# The clustering scoring uses. Monthly: trades entered in the same month share
# most of their market path. `screener diagnose sample-size` reports quarterly
# alongside it; with only ~21 quarters in a six-year split, the quarterly
# estimate rests on too few clusters to be the default.
SCORING_PERIOD = "M"


def period_key(day: date, period: str) -> Hashable:
    """The calendar bucket a trade's entry falls in."""
    if period == "M":
        return (day.year, day.month)
    if period == "Q":
        return (day.year, (day.month - 1) // 3 + 1)
    if period == "W":
        iso = day.isocalendar()
        return (iso[0], iso[1])
    raise ValueError(f"unknown period {period!r}; expected W, M or Q")


@dataclass(frozen=True)
class ClusteredMean:
    """A mean with two standard errors: naive, and robust to clustering."""

    n: int
    clusters: int
    mean: float
    iid_se: float
    cluster_se: float

    @property
    def design_effect(self) -> float:
        if not self.iid_se or math.isnan(self.iid_se) or math.isnan(self.cluster_se):
            return float("nan")
        return (self.cluster_se / self.iid_se) ** 2

    @property
    def effective_n(self) -> float:
        de = self.design_effect
        if math.isnan(de):
            return float("nan")
        # A design effect below 1 is almost always noise in the estimate.
        # Capping here errs toward less evidence, never more.
        return self.n / max(de, 1.0)

    @property
    def z_iid(self) -> float:
        return self.mean / self.iid_se if self.iid_se else float("nan")

    @property
    def z_cluster(self) -> float:
        return self.mean / self.cluster_se if self.cluster_se else float("nan")

    @property
    def se(self) -> float:
        """The standard error to use: clustered where it can be estimated."""
        return self.cluster_se if not math.isnan(self.cluster_se) else self.iid_se

    def trades_needed(self, effective: int) -> float:
        """Nominal trades required for `effective` independent observations."""
        de = self.design_effect
        return float("nan") if math.isnan(de) else effective * max(de, 1.0)


def clustered_mean(values: Sequence[float], keys: Sequence[Hashable]) -> ClusteredMean:
    """Mean of `values`, with iid and cluster-robust standard errors.

    Cluster-robust variance of a mean is the CR1 sandwich with one regressor:
    the squared SUM of residuals within each cluster, summed across clusters,
    scaled by G/(G-1). A cluster whose trades all miss in the same direction
    contributes the square of their combined miss rather than the sum of their
    individual squares, which is exactly the correlation being charged for.
    """
    if len(values) != len(keys):
        raise ValueError("values and keys must be the same length")
    n = len(values)
    if n == 0:
        return ClusteredMean(0, 0, float("nan"), float("nan"), float("nan"))
    mean = sum(values) / n
    if n < 2:
        # A mean exists; a spread around it does not.
        return ClusteredMean(n, len(set(keys)), mean, float("nan"), float("nan"))

    resid = [v - mean for v in values]
    iid_var = sum(e * e for e in resid) / (n - 1) / n

    sums: dict[Hashable, float] = defaultdict(float)
    for e, k in zip(resid, keys, strict=True):
        sums[k] += e
    g = len(sums)
    if g < 2:
        cluster_se = float("nan")
    else:
        cluster_var = (g / (g - 1)) * sum(s * s for s in sums.values()) / (n * n)
        cluster_se = math.sqrt(cluster_var)

    return ClusteredMean(n, g, mean, math.sqrt(iid_var), cluster_se)


# One closed trade, reduced to what inference needs: which stock, which day,
# what it returned. The signal identity (ticker, entry_date) is what pairing
# matches on.
TradeRecord = tuple[str, date, float]


def sample(records: Sequence[TradeRecord], period: str = SCORING_PERIOD) -> ClusteredMean:
    """Clustered mean per-trade return."""
    return clustered_mean(
        [r for _, _, r in records],
        [period_key(d, period) for _, d, _ in records],
    )


def paired(
    a: Sequence[TradeRecord], b: Sequence[TradeRecord], period: str = SCORING_PERIOD
) -> ClusteredMean:
    """Mean per-signal return difference, A minus B, over signals both took.

    Matched on (ticker, entry date): the same stock bought the same day, which
    is what "both arms took the same signal" means. Signals only one arm took
    are excluded -- they are the isolation divergence, not the exit rule.

    Pairing removes the component the two trades share -- the stock's own
    move that day -- which an unpaired test counts as noise. For the exit-
    isolated arms that component dominates, and ignoring it put h1's no-stop
    advantage at 1.1 SE when the paired, clustered figure is 2.9.
    """
    by_a = {(t, d): r for t, d, r in a}
    by_b = {(t, d): r for t, d, r in b}
    shared = sorted(set(by_a) & set(by_b), key=lambda s: (s[1], s[0]))
    return clustered_mean(
        [by_a[s] - by_b[s] for s in shared],
        [period_key(s[1], period) for s in shared],
    )
