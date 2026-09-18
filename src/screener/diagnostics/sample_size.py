"""Effective sample size: how many independent observations a backtest holds.

Every standard error in this project once divided by the number of trades, as
if each were an independent draw. Positions run at the same time in correlated
large caps, so a market-wide week moves many of them together; nominal N
overstates the evidence, and the pre-registered floor of 200 trades inherits the
overstatement.

Trades are grouped by the calendar period they were entered in and two variances
of the mean compared -- iid, and cluster-robust. Their ratio is the DESIGN
EFFECT; N divided by it is the effective sample. Month and quarter are both
reported, because a design effect that keeps growing as clusters widen means the
correlation reaches further and the coarser figure is the honest one.

Clustering by ENTRY period charges for trades opened together. Trades opened in
different months that are held through the same stretch also correlate, and
that is not charged -- so these design effects are, if anything, understated.

The arithmetic lives in backtest/inference.py, which scoring also uses. This
module adapts engine Trades to it and holds the reporting-side constant.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..backtest.benchmarks import trade_return
from ..backtest.engine import Trade
from ..backtest.inference import (
    ClusteredMean,
    TradeRecord,
    clustered_mean,
    paired,
    period_key,
    sample,
)

__all__ = [
    "ClusteredMean", "PREREGISTERED_TRADE_FLOOR", "clustered_mean",
    "paired_difference", "period_key", "records", "trade_sample",
]

# The nominal floor the pre-registered criteria apply today. Held here only so
# the "trades needed" column can express it in EFFECTIVE terms; the criterion
# itself lives in backtest/performance.py and is not changed by this module.
PREREGISTERED_TRADE_FLOOR = 200


def records(trades: Sequence[Trade]) -> list[TradeRecord]:
    """(ticker, entry date, return) for every closed trade."""
    out: list[TradeRecord] = []
    for t in trades:
        r = trade_return(t)
        if r is not None:
            out.append((t.ticker, t.entry_date, r))
    return out


def trade_sample(trades: Sequence[Trade], period: str) -> ClusteredMean:
    """Clustered mean per-trade return for one configuration's closed trades."""
    return sample(records(trades), period)


def paired_difference(
    trades_a: Sequence[Trade], trades_b: Sequence[Trade], period: str
) -> ClusteredMean:
    """Mean per-signal return difference, A minus B, over signals both took."""
    return paired(records(trades_a), records(trades_b), period)
