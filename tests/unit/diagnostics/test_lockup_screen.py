"""H9, the lock-up expiry screen (docs/12): an event's own return after the
engine's rules, against the same-day pool, after costs."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from screener.backtest.splits import get_split
from screener.diagnostics.lockup_screen import _entry_index, judge, measure


def _bars(closes, volumes=None, start="2010-01-04"):
    closes = np.asarray(closes, dtype="float64")
    idx = pd.bdate_range(start, periods=len(closes))
    vol = np.full(len(closes), 1e6) if volumes is None else np.asarray(volumes, dtype="float64")
    return pd.DataFrame({"open": closes, "high": closes, "low": closes,
                         "close": closes, "volume": vol}, index=idx)


def test_entry_index_is_the_bar_on_or_before_expiry():
    bars = _bars(np.arange(1, 20, dtype=float), start="2010-01-04")
    # 2010-01-04 is a Monday; index 5 lands on 2010-01-11.
    expiry = bars.index[5].date()
    assert _entry_index(bars, expiry) == 5


def test_entry_index_falls_back_to_the_nearest_prior_trading_day():
    bars = _bars(np.arange(1, 20, dtype=float), start="2010-01-04")
    # 2010-01-09 is a Saturday -- no bar that day; the nearest PRIOR
    # trading day is Friday 2010-01-08 (index 4).
    assert _entry_index(bars, date(2010, 1, 9)) == 4


def test_entry_index_none_when_expiry_is_the_last_bar():
    bars = _bars([10.0, 11.0])
    assert _entry_index(bars, bars.index[-1].date()) is None


def test_entry_index_none_when_expiry_is_before_the_series_starts():
    bars = _bars([10.0, 11.0], start="2010-06-01")
    assert _entry_index(bars, date(2010, 1, 1)) is None


def _pool_with_one_underperformer(n_pool=60, seed=0):
    """A calm pool drifting up; one name ("EVT") that drops hard right
    after a chosen expiry date -- the signal this screen should catch."""
    rng = np.random.default_rng(seed)
    bars = {}
    for k in range(n_pool):
        r = rng.normal(0.0004, 0.01, 120)
        bars[f"P{k}"] = _bars(20 * np.cumprod(1 + r))

    closes = np.full(120, 20.0)
    drop_at = 40
    closes[drop_at:] = 20.0 * np.cumprod(np.full(120 - drop_at, 0.97))
    bars["EVT"] = _bars(closes)
    expiry = bars["EVT"].index[drop_at - 1].date()
    return bars, expiry


def test_measure_counts_every_resolvable_event_and_catches_the_drop():
    bars, expiry = _pool_with_one_underperformer()
    outcomes = measure(bars, [("EVT", expiry)], spreads={}, horizon=3)
    assert len(outcomes) == 1
    o = outcomes[0]
    assert o.ticker == "EVT"
    assert o.gross < 0
    assert o.gross < o.pool_gross          # underperforms the same-day pool


def test_measure_drops_an_event_whose_ticker_is_not_in_the_universe():
    bars, expiry = _pool_with_one_underperformer()
    outcomes = measure(bars, [("NOPE", expiry), ("EVT", expiry)], spreads={}, horizon=3)
    assert len(outcomes) == 1
    assert outcomes[0].ticker == "EVT"


def test_measure_drops_an_event_too_close_to_the_series_end():
    bars, expiry = _pool_with_one_underperformer()
    last_date = bars["EVT"].index[-1].date()
    outcomes = measure(bars, [("EVT", last_date)], spreads={}, horizon=3)
    assert outcomes == []


def test_judge_reads_a_negative_gap_as_low_one_sided_p():
    """A clearly negative gap should read as strong evidence FOR
    underperformance (small p), not against it."""
    outcomes = []
    from screener.diagnostics.lockup_screen import EventOutcome
    rng = np.random.default_rng(2)
    for i, g in enumerate(rng.normal(-0.02, 0.01, 40)):
        outcomes.append(EventOutcome(
            ticker=f"E{i}", expiry_date=date(2012, 1, 1), entry_date=date(2012, 1, 2),
            gross=g, net=g, pool_gross=0.0, pool_net=0.0, pool_n=100,
        ))
    verdict = judge(outcomes, get_split("development"))
    assert verdict.mean_net_gap < 0
    assert verdict.p_net_one_sided < 0.01


def test_judge_reads_a_positive_gap_as_high_one_sided_p():
    """The mirror case: a clearly POSITIVE gap (outperformance, the wrong
    direction for this hypothesis) must not read as evidence for it."""
    outcomes = []
    from screener.diagnostics.lockup_screen import EventOutcome
    rng = np.random.default_rng(3)
    for i, g in enumerate(rng.normal(0.02, 0.01, 40)):
        outcomes.append(EventOutcome(
            ticker=f"E{i}", expiry_date=date(2012, 1, 1), entry_date=date(2012, 1, 2),
            gross=g, net=g, pool_gross=0.0, pool_net=0.0, pool_n=100,
        ))
    verdict = judge(outcomes, get_split("development"))
    assert verdict.mean_net_gap > 0
    assert verdict.p_net_one_sided > 0.99


def test_passes_development_requires_all_three_legs():
    from screener.diagnostics.lockup_screen import Verdict
    base = dict(events=100, mean_net_gap=-0.01, t_net=-3.0, p_net_one_sided=0.01,
                mean_gross_gap=-0.01, t_gross=-3.0, mean_trimmed_gap=-0.01,
                regimes_negative=2, regimes_total=3, by_regime={})
    assert Verdict(**base).passes_development
    assert not Verdict(**{**base, "p_net_one_sided": 0.2}).passes_development
    assert not Verdict(**{**base, "regimes_negative": 1}).passes_development
    assert not Verdict(**{**base, "mean_trimmed_gap": 0.01}).passes_development
