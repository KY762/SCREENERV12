"""Golden-value tests. Every expected number is computed by hand in the docstring.

If one of these fails, the indicator is wrong -- not the test. Update an expected
value only after re-deriving it on paper.
"""

import numpy as np
import pandas as pd
import pytest

from screener.calc import indicators as ind

APPROX = dict(rel=1e-9)


def test_sma_golden(bars):
    """close = [103,107,105,111,110,112]
    SMA(3)[2] = (103+107+105)/3 = 105
    SMA(3)[3] = (107+105+111)/3 = 107.666666...
    SMA(3)[5] = (111+110+112)/3 = 111
    """
    out = ind.sma(bars["close"], 3)
    assert out.iloc[:2].isna().all(), "warmup must be NaN, not filled"
    assert out.iloc[2] == pytest.approx(105.0, **APPROX)
    assert out.iloc[3] == pytest.approx(323 / 3, **APPROX)
    assert out.iloc[5] == pytest.approx(111.0, **APPROX)


def test_true_range_golden(bars):
    """t0: H-L = 105-98 = 7 (no prior close)
    t1: max(108-102=6, |108-103|=5, |102-103|=1) = 6
    t2: max(110-104=6, |110-107|=3, |104-107|=3) = 6
    t3: max(112-103=9, |112-105|=7, |103-105|=2) = 9
    t4: max(115-109=6, |115-111|=4, |109-111|=2) = 6
    t5: max(113-106=7, |113-110|=3, |106-110|=4) = 7
    """
    tr = ind.true_range(bars)
    assert list(tr) == [7.0, 6.0, 6.0, 9.0, 6.0, 7.0]


def test_atr_wilder_golden(bars):
    """Wilder's RMA, window=3, seeded on the SMA of the first 3 true ranges.
    seed[2] = (7+6+6)/3          = 6.3333333...
    [3]     = (6.333333*2 + 9)/3 = 7.2222222...
    [4]     = (7.222222*2 + 6)/3 = 6.8148148...
    [5]     = (6.814815*2 + 7)/3 = 6.8765432...
    """
    a = ind.atr(bars, 3)
    assert a.iloc[:2].isna().all()
    assert a.iloc[2] == pytest.approx(19 / 3, **APPROX)
    assert a.iloc[3] == pytest.approx(65 / 9, **APPROX)
    assert a.iloc[4] == pytest.approx(184 / 27, **APPROX)
    assert a.iloc[5] == pytest.approx(557 / 81, **APPROX)


def test_atr_is_wilder_not_simple_mean(bars):
    """Guards the documented smoothing choice. A simple mean of TR over the last
    3 bars at t=5 would be (9+6+7)/3 = 7.333..., which is NOT Wilder's answer."""
    a = ind.atr(bars, 3)
    simple_mean_at_5 = (9 + 6 + 7) / 3
    assert a.iloc[5] != pytest.approx(simple_mean_at_5, rel=1e-6)


def test_clv_golden(bars):
    """CLV = ((C-L)-(H-C))/(H-L)
    t0: ((103-98)-(105-103))/7 = (5-2)/7  =  3/7
    t2: ((105-104)-(110-105))/6 = (1-5)/6 = -4/6
    t5: ((112-106)-(113-112))/7 = (6-1)/7 =  5/7
    """
    c = ind.clv(bars)
    assert c.iloc[0] == pytest.approx(3 / 7, **APPROX)
    assert c.iloc[2] == pytest.approx(-4 / 6, **APPROX)
    assert c.iloc[5] == pytest.approx(5 / 7, **APPROX)
    assert (c.abs() <= 1.0).all(), "CLV must stay within [-1, 1]"


def test_clv_zero_range_bar_returns_zero():
    """A bar with no range had no contest, so neither side won. 0.0, not NaN."""
    flat = pd.DataFrame(
        {"open": [50.0], "high": [50.0], "low": [50.0], "close": [50.0], "volume": [10.0]}
    )
    assert ind.clv(flat).iloc[0] == 0.0


def test_rvol_excludes_current_bar(bars):
    """volume = [1000,1200,800,1500,900,1100]; window=3
    baseline[3] = mean(1000,1200,800) = 1000      -> rvol = 1500/1000 = 1.5
    baseline[4] = mean(1200,800,1500) = 1166.666  -> rvol = 900/1166.666
    baseline[5] = mean(800,1500,900)  = 1066.666  -> rvol = 1100/1066.666
    A baseline that included the current bar would mute the very spike being measured.
    """
    r = ind.rvol(bars, 3)
    assert r.iloc[:3].isna().all()
    assert r.iloc[3] == pytest.approx(1.5, **APPROX)
    assert r.iloc[4] == pytest.approx(900 / (3500 / 3), **APPROX)
    assert r.iloc[5] == pytest.approx(1100 / (3200 / 3), **APPROX)


def test_returns_golden(bars):
    """ret_2[2] = 105/103 - 1 ; ret_2[5] = 112/111 - 1"""
    r = ind.returns(bars["close"], 2)
    assert r.iloc[:2].isna().all()
    assert r.iloc[2] == pytest.approx(105 / 103 - 1, **APPROX)
    assert r.iloc[5] == pytest.approx(112 / 111 - 1, **APPROX)


def test_pct_from_high_golden(bars):
    """window=3, INCLUDING the current bar.
    t2: max high(105,108,110)=110, close 105 -> (105-110)/110
    t5: max high(112,115,113)=115, close 112 -> (112-115)/115
    """
    p = ind.pct_from_high(bars, 3)
    assert p.iloc[2] == pytest.approx(-5 / 110, **APPROX)
    assert p.iloc[5] == pytest.approx(-3 / 115, **APPROX)
    assert (p.dropna() <= 0).all(), "close cannot exceed the rolling high"


def test_pct_from_high_is_zero_at_a_new_high():
    df = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [10.0, 11.0, 12.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.0, 11.0, 12.0],
            "volume": [1.0, 1.0, 1.0],
        }
    )
    assert ind.pct_from_high(df, 3).iloc[2] == pytest.approx(0.0, abs=1e-12)


def test_realized_vol_matches_sample_stdev(bars):
    v = ind.realized_vol(bars["close"], 3)
    daily = bars["close"].pct_change(fill_method=None)
    assert v.iloc[3] == pytest.approx(daily.iloc[1:4].std(ddof=1), **APPROX)


def test_slope_positive_is_nullable_boolean(bars):
    """close = [103,107,105,111,110,112]
    lookback=2 at t4: 110 > close[2]=105 -> True
    lookback=1 at t2: 105 > close[1]=107 -> False
    """
    two = ind.slope_positive(bars["close"], 2)
    assert str(two.dtype) == "boolean"
    assert pd.isna(two.iloc[0]), "warmup must be NA, distinguishable from False"
    assert pd.isna(two.iloc[1])
    assert bool(two.iloc[2]) is True    # 105 > 103
    assert bool(two.iloc[4]) is True    # 110 > 105

    one = ind.slope_positive(bars["close"], 1)
    assert bool(one.iloc[2]) is False   # 105 < 107
    assert bool(one.iloc[3]) is True    # 111 > 105


def test_missing_column_raises_clearly(bars):
    with pytest.raises(ValueError, match="missing required column"):
        ind.clv(bars.drop(columns=["high"]))


def test_warmup_never_silently_filled(bars):
    """A filled warmup value is fabricated history. Every indicator must leave it NaN."""
    for series in (
        ind.sma(bars["close"], 4),
        ind.atr(bars, 4),
        ind.rvol(bars, 4),
        ind.realized_vol(bars["close"], 4),
        ind.dollar_volume(bars, 4),
    ):
        assert series.iloc[0] != series.iloc[0] or np.isnan(series.iloc[0])
