"""The null has to be a real null.

A permutation that quietly preserved the ordering, or produced bars a strategy
could reject as malformed, would let a broken engine pass the one check aimed
at catching it -- the vacuous-verification failure from the bug log, rebuilt in
a new place.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.backtest.noise import permute_bars, permute_universe


@pytest.fixture
def long_bars() -> pd.DataFrame:
    """Sixty bars, so a permutation has room to be visibly different."""
    rng = np.random.default_rng(11)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, 60)))
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.02,
            "low": close * 0.97,
            "close": close,
            "volume": rng.integers(500, 5000, 60).astype("float64"),
        },
        index=pd.date_range("2024-01-02", periods=60, freq="B"),
    )


def _log_returns(frame: pd.DataFrame) -> np.ndarray:
    return np.diff(np.log(frame["close"].to_numpy(dtype="float64")))


def test_the_multiset_of_returns_is_preserved(long_bars):
    """If permutation changed the returns themselves, a strategy failing on the
    null would prove nothing -- the null would be a different market, not the
    same market with its order removed."""
    original = np.sort(_log_returns(long_bars))
    permuted = np.sort(_log_returns(permute_bars(long_bars, seed=1)))
    np.testing.assert_allclose(original, permuted, rtol=1e-12, atol=1e-12)


def test_the_order_actually_changes(long_bars):
    """A no-op permutation would hand back the real series, so every strategy
    would 'pass' the null by reproducing its real result."""
    permuted = permute_bars(long_bars, seed=1)
    assert not np.allclose(_log_returns(long_bars), _log_returns(permuted))


def test_bars_stay_well_formed(long_bars):
    """Malformed bars (high below close, negative prices) get rejected by the
    engine rather than traded, so the null would silently test nothing."""
    permuted = permute_bars(long_bars, seed=2)
    assert (permuted[["open", "high", "low", "close"]] > 0).all().all()
    assert (permuted["high"] >= permuted[["open", "close"]].max(axis=1)).all()
    assert (permuted["low"] <= permuted[["open", "close"]].min(axis=1)).all()
    assert (permuted["high"] >= permuted["low"]).all()


def test_same_seed_reproduces_and_different_seeds_diverge(long_bars):
    """An unreproducible null cannot be re-derived later, so a result on it
    would have to be taken on trust -- the thing this project refuses."""
    a = permute_bars(long_bars, seed=7)
    b = permute_bars(long_bars, seed=7)
    c = permute_bars(long_bars, seed=8)
    pd.testing.assert_frame_equal(a, b)
    assert not np.allclose(a["close"].to_numpy(), c["close"].to_numpy())


def test_calendar_and_anchor_are_preserved(long_bars):
    """The index is the real trading calendar; if it moved, holding periods and
    the split boundaries would mean something different on the null than on the
    real data, and the comparison would stop being like-for-like."""
    permuted = permute_bars(long_bars, seed=3)
    pd.testing.assert_index_equal(permuted.index, long_bars.index)
    assert permuted["close"].iloc[0] == pytest.approx(long_bars["close"].iloc[0])
    assert list(permuted.columns) == list(long_bars.columns)


def test_volume_travels_with_its_own_bar(long_bars):
    """Volume detached from its bar would break any volume-aware rule on the
    null only, making the null harder than reality instead of equal to it."""
    permuted = permute_bars(long_bars, seed=4)
    assert sorted(permuted["volume"].tolist()) == sorted(long_bars["volume"].tolist())


def test_frames_too_short_to_permute_come_back_unchanged(bars):
    """Two bars carry one return, and permuting one item is the identity.
    Returning a 'shuffled' frame that is not shuffled would be a lie the
    caller cannot detect."""
    short = bars.head(2)
    pd.testing.assert_frame_equal(permute_bars(short, seed=1), short)


def test_non_positive_close_is_rejected(long_bars):
    """log() of a non-positive price yields nan and the whole rebuilt series
    becomes nan, which downstream reads as 'no data' rather than as an error."""
    broken = long_bars.copy()
    broken.loc[broken.index[5], "close"] = 0.0
    with pytest.raises(ValueError, match="positive"):
        permute_bars(broken, seed=1)


def test_missing_columns_are_rejected(long_bars):
    """Silently permuting a frame without a close would produce a frame of
    nans that still has the right shape."""
    with pytest.raises(ValueError, match="missing"):
        permute_bars(long_bars.drop(columns=["close"]), seed=1)


def test_each_symbol_gets_its_own_permutation(long_bars):
    """One shared permutation moves every symbol the same way on the same day,
    leaving the cross-section intact -- and the cross-section is what H1 and H5
    rank on. That null would be trivially passable by exactly the strategies it
    most needs to test."""
    universe = {"AAA": long_bars.copy(), "BBB": long_bars.copy()}
    permuted = permute_universe(universe, seed=5)
    assert not np.allclose(
        permuted["AAA"]["close"].to_numpy(), permuted["BBB"]["close"].to_numpy()
    )


def test_universe_permutation_is_reproducible(long_bars):
    """Same integer, same universe -- otherwise a null result cannot be
    re-derived from what gets written into the research log."""
    universe = {"AAA": long_bars.copy(), "BBB": long_bars.copy()}
    first = permute_universe(universe, seed=9)
    second = permute_universe(universe, seed=9)
    for ticker in first:
        pd.testing.assert_frame_equal(first[ticker], second[ticker])


# --------------------------------------------------------------------------
# Does the null have teeth? A check that has never rejected anything is the
# vacuous verification from the bug log wearing a new name.
# --------------------------------------------------------------------------


def _trending_bars(n: int = 2000, seed: int = 21) -> pd.DataFrame:
    """A series with deliberate momentum: each return carries part of the last.

    Real predictability, built in on purpose, so its removal is measurable
    rather than assumed.
    """
    rng = np.random.default_rng(seed)
    shocks = rng.normal(0.0, 0.015, n)
    returns = np.empty(n)
    returns[0] = shocks[0]
    for i in range(1, n):
        returns[i] = 0.45 * returns[i - 1] + shocks[i]
    close = 100.0 * np.exp(np.cumsum(returns))
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=pd.date_range("2016-01-04", periods=n, freq="B"),
    )


def test_built_in_predictability_is_actually_destroyed():
    """The whole premise. If permutation left autocorrelation behind, a
    momentum rule could pass the null by finding the same structure it finds
    in reality, and the check would certify a strategy it never tested."""
    real = _trending_bars()
    permuted = permute_bars(real, seed=1)

    before = np.corrcoef(_log_returns(real)[:-1], _log_returns(real)[1:])[0, 1]
    after = np.corrcoef(_log_returns(permuted)[:-1], _log_returns(permuted)[1:])[0, 1]

    assert before > 0.35, f"fixture is not actually trending: {before:.3f}"
    assert abs(after) < 0.06, f"permutation left autocorrelation behind: {after:.3f}"


def test_a_lookahead_rule_still_scores_on_the_null():
    """The reason this module exists.

    Permutation removes edge that comes from the market. It cannot remove edge
    that comes from the machinery, because a rule reading a bar it should not
    have seen reads the permuted bar just as happily. So a strategy that keeps
    its edge on the null has a bug, and this asserts the null exposes that
    rather than hiding it -- which is exactly the class the zero-R target and
    the wrongly-anchored stop belonged to.
    """
    permuted = permute_bars(_trending_bars(), seed=2)
    close = permuted["close"].to_numpy()
    forward = close[5:] / close[:-5] - 1.0

    # Causal: the trailing 20 bars were up. Reads only the past.
    causal = (close[19:-5] / close[:-24] - 1.0) > 0
    # Lookahead: the next bar closes higher. Reads one bar into the future.
    cheating = (close[20:-4] / close[19:-5] - 1.0) > 0
    horizon = forward[19:]

    # Every 5th sample, so the 5-day forward windows do not overlap. Sampling
    # them daily shares four days out of five between neighbours, and the
    # standard error of the mean then assumes an independence that is not
    # there -- it comes out about sqrt(5) too small and the test rejects a
    # result that is well inside the noise. That is the inflated-significance
    # error this project's evidence rules exist to prevent, so the fix is
    # non-overlapping samples rather than a fudged tolerance.
    step = 5
    causal, cheating, horizon = causal[::step], cheating[::step], horizon[::step]

    causal_edge = horizon[causal].mean()
    cheating_edge = horizon[cheating].mean()
    tolerance = 3.0 * horizon.std(ddof=1) / np.sqrt(causal.sum())

    assert abs(causal_edge) < tolerance, (
        f"causal rule found {causal_edge:+.4f} on data with no structure "
        f"(3 SE = {tolerance:.4f}) -- the permutation is incomplete"
    )
    assert cheating_edge > tolerance, (
        f"lookahead rule scored only {cheating_edge:+.4f} against 3 SE of "
        f"{tolerance:.4f}; the null cannot expose a machinery artefact, "
        "which is its whole purpose"
    )
