"""Effective sample size and the paired exit comparison.

Every standard error in this project divided by the trade count as if trades
were independent draws. These tests pin the measurement of how far that
overstated the evidence.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from screener.backtest.engine import Trade
from screener.diagnostics.sample_size import (
    PREREGISTERED_TRADE_FLOOR,
    clustered_mean,
    paired_difference,
    period_key,
    trade_sample,
)


def trade(ticker: str, entry: date, ret: float) -> Trade:
    entry_price = Decimal("100")
    return Trade(
        ticker=ticker, setup="t", entry_date=entry, entry_price=entry_price,
        shares=1, stop=Decimal("90"), target=None, risk_dollars=Decimal("10"),
        exit_date=entry + timedelta(days=5),
        exit_price=entry_price * (1 + Decimal(str(ret))), bars_held=5,
    )


def test_independent_trades_carry_their_full_count():
    """One trade per period, so there is no within-period correlation to charge
    for and the effective sample is the nominal one."""
    values = [0.01, -0.02, 0.03, -0.01, 0.02, 0.00, -0.03, 0.01]
    got = clustered_mean(values, keys=list(range(len(values))))

    assert got.design_effect == pytest.approx(len(values) / (len(values) - 1), rel=0.2)
    assert got.effective_n == pytest.approx(len(values), rel=0.2)


def test_perfectly_correlated_trades_count_once_per_period():
    """The failure being measured. Ten trades per month that all move
    together are ten copies of one observation, not ten observations."""
    months = [0.02, -0.01, 0.03, -0.02, 0.01, 0.00]
    values = [m for m in months for _ in range(10)]
    keys = [i for i, _ in enumerate(months) for _ in range(10)]

    got = clustered_mean(values, keys)

    assert got.n == 60
    assert got.effective_n == pytest.approx(len(months), rel=0.25)
    assert got.design_effect > 8


def test_effective_n_never_exceeds_nominal():
    """A negative within-period correlation is almost always noise in the
    estimate; letting it inflate the sample would invent evidence."""
    values = [0.05, -0.05] * 20
    keys = [i // 2 for i in range(40)]         # each pair cancels exactly
    got = clustered_mean(values, keys)

    assert got.design_effect < 1
    assert got.effective_n == got.n


def test_trades_needed_scales_the_floor_by_the_design_effect():
    months = [0.02, -0.01, 0.03, -0.02]
    values = [m for m in months for _ in range(5)]
    keys = [i for i, _ in enumerate(months) for _ in range(5)]
    got = clustered_mean(values, keys)

    assert got.trades_needed(PREREGISTERED_TRADE_FLOOR) == pytest.approx(
        PREREGISTERED_TRADE_FLOOR * got.design_effect
    )


def test_a_single_cluster_cannot_estimate_clustering():
    got = clustered_mean([0.01, 0.02, 0.03], keys=["same"] * 3)
    assert math.isnan(got.cluster_se)


def test_period_keys_bucket_by_calendar():
    assert period_key(date(2014, 3, 31), "M") == (2014, 3)
    assert period_key(date(2014, 3, 31), "Q") == (2014, 1)
    assert period_key(date(2014, 4, 1), "Q") == (2014, 2)
    with pytest.raises(ValueError, match="period"):
        period_key(date(2014, 1, 1), "Y")


def test_trade_sample_clusters_by_entry_date():
    trades = [trade("A", date(2014, 1, d), 0.01) for d in (2, 3, 6)] + [
        trade("B", date(2014, 2, d), -0.01) for d in (3, 4)
    ]
    got = trade_sample(trades, "M")

    assert got.n == 5
    assert got.clusters == 2


def test_pairing_removes_the_noise_both_arms_share():
    """The exit-isolated case. Both arms buy the same stock on the same day, so
    most of each trade's return is common to both and cancels in the
    difference. An unpaired test counts that common part as noise; a paired
    test does not. Here the arms differ by exactly 1% on every signal, buried
    in 20% swings -- invisible unpaired, unmistakable paired."""
    days = [date(2014, 1, 1) + timedelta(days=7 * i) for i in range(40)]
    swings = [0.20 if i % 2 else -0.20 for i in range(40)]
    no_stop = [trade("X", d, s + 0.01) for d, s in zip(days, swings, strict=True)]
    stop = [trade("X", d, s) for d, s in zip(days, swings, strict=True)]

    paired = paired_difference(no_stop, stop, "M")

    assert paired.mean == pytest.approx(0.01, abs=1e-9)
    assert paired.iid_se == pytest.approx(0.0, abs=1e-9)


def test_signals_only_one_arm_took_are_not_compared():
    """Those are the isolation divergence, not the exit rule."""
    shared = trade("A", date(2014, 1, 2), 0.05)
    only_a = trade("B", date(2014, 1, 3), 0.50)
    got = paired_difference([shared, only_a], [trade("A", date(2014, 1, 2), 0.02)], "M")

    assert got.n == 1
    assert got.mean == pytest.approx(0.03)
