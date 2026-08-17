"""The truncation test: proof that no indicator can see the future.

If a function's value at bar t is computed using ANY data after t, then computing
it on a truncated series will disagree with computing it on the full series and
slicing. That disagreement is the definition of lookahead, and this file detects
it mechanically rather than by inspection.

A backtest built on a leaking indicator produces excellent results and loses
money in live trading. It is the single most expensive class of bug in this
codebase, and the cheapest to prevent.
"""

import numpy as np
import pandas as pd
import pytest

from screener.calc import indicators as ind
from screener.calc import patterns as pat
from screener.calc import relative_strength as rs


@pytest.fixture(scope="module")
def series() -> pd.DataFrame:
    """120 deterministic bars with trend, noise, gaps and volume variation."""
    rng = np.random.default_rng(20260817)
    n = 120
    steps = rng.normal(0.0006, 0.018, n)
    close = 100 * np.exp(np.cumsum(steps))
    spread = np.abs(rng.normal(0.012, 0.006, n)) * close
    open_ = close * (1 + rng.normal(0, 0.006, n))
    high = np.maximum(open_, close) + spread * 0.6
    low = np.minimum(open_, close) - spread * 0.6
    volume = rng.integers(500_000, 5_000_000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.date_range("2024-01-01", periods=n, freq="B"),
    )


INDICATORS = {
    "sma_20": lambda d: ind.sma(d["close"], 20),
    "ema_20": lambda d: ind.ema(d["close"], 20),
    "rma_14": lambda d: ind.rma(d["close"], 14),
    "true_range": ind.true_range,
    "atr_14": lambda d: ind.atr(d, 14),
    "atr_pct_14": lambda d: ind.atr_pct(d, 14),
    "rvol_20": lambda d: ind.rvol(d, 20),
    "ret_21": lambda d: ind.returns(d["close"], 21),
    "realized_vol_21": lambda d: ind.realized_vol(d["close"], 21),
    "clv": ind.clv,
    "pct_from_high_60": lambda d: ind.pct_from_high(d, 60),
    "dollar_volume_50": lambda d: ind.dollar_volume(d, 50),
    "slope_positive_21": lambda d: ind.slope_positive(ind.sma(d["close"], 20), 21),
    "displacement_body": lambda d: pat.displacement_ratio(d, "body", 14),
    "displacement_range": lambda d: pat.displacement_ratio(d, "range", 14),
    "confirmed_swing_low": lambda d: pat.confirmed_swing_low_price(d, 2, 2),
    "liq_ref_prior_day": lambda d: pat.liquidity_reference(d, "prior_day"),
    "liq_ref_prior_week": lambda d: pat.liquidity_reference(d, "prior_week"),
    "liq_ref_10bar": lambda d: pat.liquidity_reference(d, "n_bar", n=10),
    "liq_ref_swing": lambda d: pat.liquidity_reference(d, "swing"),
}


@pytest.mark.parametrize("name", sorted(INDICATORS))
@pytest.mark.parametrize("cut", [70, 95, 119])
def test_indicator_does_not_change_when_future_bars_are_removed(series, name, cut):
    fn = INDICATORS[name]
    full = fn(series).iloc[:cut]
    truncated = fn(series.iloc[:cut])

    full_num = pd.to_numeric(full, errors="coerce").to_numpy(dtype="float64")
    trunc_num = pd.to_numeric(truncated, errors="coerce").to_numpy(dtype="float64")

    both_nan = np.isnan(full_num) & np.isnan(trunc_num)
    mismatch = ~both_nan & ~np.isclose(full_num, trunc_num, rtol=1e-12, atol=1e-12, equal_nan=True)
    bad = np.flatnonzero(mismatch)
    assert bad.size == 0, (
        f"{name} leaks future data at bar(s) {bad[:5].tolist()} when truncated at {cut}: "
        f"full={full_num[bad[:5]]} truncated={trunc_num[bad[:5]]}"
    )


def test_swing_low_pivots_is_documented_as_unsafe():
    """swing_low_pivots marks the pivot bar itself, which is NOT knowable then.

    Constructed deterministically: lows [10, 9, 5, 8, 11] have a pivot at index 2
    with left=right=2. Truncating to the first 4 bars removes the confirmation
    bars, so the pivot cannot yet be seen -- and the two results disagree.

    This test asserts the leak EXISTS. It is the reason trading rules must use
    confirmed_swing_low_price instead. If it ever stops disagreeing, the
    lookahead warning in the docstring needs revisiting.
    """
    df = pd.DataFrame(
        {
            "open":   [10.0,  9.0,  7.0,  7.0, 10.0],
            "high":   [12.0, 10.0,  8.0, 10.0, 13.0],
            "low":    [10.0,  9.0,  5.0,  8.0, 11.0],
            "close":  [11.0,  9.0,  6.0, 10.0, 12.0],
            "volume": [100.0, 100.0, 100.0, 100.0, 100.0],
        }
    )
    cut = 4
    full = pat.swing_low_pivots(df, 2, 2).iloc[:cut].to_numpy()
    truncated = pat.swing_low_pivots(df.iloc[:cut], 2, 2).to_numpy()

    assert full[2] is np.True_ or bool(full[2]), "fixture should contain a pivot at index 2"
    assert not bool(truncated[2]), "pivot cannot be knowable before its confirmation bars"
    assert not np.array_equal(full, truncated)

    # The safe variant must agree under the same truncation.
    safe_full = pat.confirmed_swing_low_price(df, 2, 2).iloc[:cut].to_numpy()
    safe_trunc = pat.confirmed_swing_low_price(df.iloc[:cut], 2, 2).to_numpy()
    both_nan = np.isnan(safe_full) & np.isnan(safe_trunc)
    assert np.all(both_nan | np.isclose(safe_full, safe_trunc, equal_nan=True))


@pytest.mark.parametrize("cut", [70, 95, 119])
def test_relative_strength_does_not_leak(series, cut):
    benchmark = series["close"] * 0.97 + 3.0
    for fn in (rs.relative_strength, rs.relative_strength_adjusted):
        full = fn(series["close"], benchmark, 21).iloc[:cut].to_numpy(dtype="float64")
        trunc = fn(series["close"].iloc[:cut], benchmark.iloc[:cut], 21).to_numpy(dtype="float64")
        both_nan = np.isnan(full) & np.isnan(trunc)
        assert np.all(both_nan | np.isclose(full, trunc, rtol=1e-12, atol=1e-12))


@pytest.mark.parametrize("cut", [70, 95])
def test_signal_events_do_not_appear_retroactively(series, cut):
    """Events detected on truncated data must be a prefix of those on full data.

    Truncation can only remove events near the boundary; it must never change
    the entry bar or stop level of an event that already completed.
    """
    kwargs = dict(retrace_window=10, atr_window=14, displacement_min=None)
    full = [e for e in pat.fvg_entry_events(series, **kwargs) if e.entry_idx < cut]
    trunc = pat.fvg_entry_events(series.iloc[:cut], **kwargs)

    trunc_by_trigger = {e.trigger_idx: e for e in trunc}
    for ev in full:
        match = trunc_by_trigger.get(ev.trigger_idx)
        if match is None:
            continue  # boundary effect: acceptable
        assert match.entry_idx == ev.entry_idx
        assert match.stop_level == pytest.approx(ev.stop_level, rel=1e-12)
        assert match.zone_bottom == pytest.approx(ev.zone_bottom, rel=1e-12)
