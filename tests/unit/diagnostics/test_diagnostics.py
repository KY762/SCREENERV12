"""Diagnostics tests.

These run before any P&L, and either can invalidate a specification: frequency
answers "does this setup select anything", overlap answers "are these separate
hypotheses or one hypothesis under three names".
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.calc.patterns import SignalEvent
from screener.diagnostics.redundancy import correlation_matrix, find_redundant
from screener.diagnostics.signals import frequency_report, overlap, overlap_matrix

# --- redundancy ------------------------------------------------------------

def _indicator_frame(n=300, seed=11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 1, n)
    return pd.DataFrame(
        {
            "ret_63": base,
            "ret_63_copy": base * 2.0 + 0.001,        # monotone transform -> r = 1
            "rvol_20": rng.normal(0, 1, n),
            "clv": rng.normal(0, 1, n),
        }
    )


def test_perfectly_correlated_indicator_is_dropped():
    """A monotone transform carries no additional information -- only a
    parameter."""
    report = find_redundant(_indicator_frame(), priority=["ret_63", "ret_63_copy",
                                                          "rvol_20", "clv"])
    assert report.dropped == ["ret_63_copy"]
    assert set(report.retained) == {"ret_63", "rvol_20", "clv"}


def test_independent_indicators_are_all_retained():
    rng = np.random.default_rng(5)
    frame = pd.DataFrame({c: rng.normal(0, 1, 400) for c in ("a", "b", "c")})
    report = find_redundant(frame)
    assert report.redundant_pairs == []
    assert set(report.retained) == {"a", "b", "c"}
    assert "all 3 indicators retained" in report.summary()


def test_priority_decides_which_of_a_redundant_pair_survives():
    """Without an explicit keep-order the survivor would depend on column
    ordering, which is not a decision anyone made."""
    frame = _indicator_frame()
    first = find_redundant(frame, priority=["ret_63", "ret_63_copy"])
    second = find_redundant(frame, priority=["ret_63_copy", "ret_63"])

    assert first.dropped == ["ret_63_copy"]
    assert second.dropped == ["ret_63"]


def test_strong_negative_correlation_also_counts_as_redundant():
    """An inverted duplicate is still a duplicate -- magnitude is what matters."""
    rng = np.random.default_rng(3)
    base = rng.normal(0, 1, 300)
    frame = pd.DataFrame({"a": base, "b": -base})
    report = find_redundant(frame, priority=["a", "b"])
    assert report.dropped == ["b"]
    assert report.redundant_pairs[0].correlation < -0.99


def test_threshold_is_respected():
    frame = _indicator_frame()
    assert find_redundant(frame, threshold=0.99).dropped == ["ret_63_copy"]
    strict = find_redundant(frame, threshold=1.01)
    assert strict.dropped == []


def test_spearman_is_the_default_because_indicators_are_skewed():
    """Pearson on a heavy-tailed indicator reports the influence of a few
    extreme days rather than the typical relationship."""
    rng = np.random.default_rng(9)
    x = rng.normal(0, 1, 500)
    frame = pd.DataFrame({"x": x, "x_cubed": x**3})   # monotone, not linear

    spearman = correlation_matrix(frame, "spearman").loc["x", "x_cubed"]
    pearson = correlation_matrix(frame, "pearson").loc["x", "x_cubed"]
    assert spearman > 0.999
    assert pearson < spearman


# --- signal frequency ------------------------------------------------------

def _bars(n: int, start="2020-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        index=pd.date_range(start, periods=n, freq="B"),
    )


def _events(indices, setup="x") -> list[SignalEvent]:
    return [
        SignalEvent(setup, i, i, i + 1, 0.0, 0.0, 0.0) for i in indices
    ]


def test_frequency_flags_a_setup_that_fires_too_often():
    """A rule firing on 40% of bars is not a signal, it is a description of the
    market -- exactly the risk with H2's displacement filter disabled."""
    bars = _bars(1000)
    events = _events(range(0, 1000, 2))          # every other bar
    report = frequency_report("fvg_no_filter", {"SPY": events}, {"SPY": bars})

    assert report.signals_per_bar == pytest.approx(0.5)
    assert report.verdict == "too frequent -- not selective"


def test_frequency_flags_a_setup_too_rare_to_reach_the_sample_minimum():
    bars = _bars(2000)
    report = frequency_report("rare", {"SPY": _events(range(0, 2000, 200))},
                              {"SPY": bars})
    assert report.total_signals == 10
    assert "below the 200-trade minimum" in report.verdict


def test_frequency_accepts_a_usable_rate():
    bars = _bars(5000)
    report = frequency_report("ok", {"SPY": _events(range(0, 5000, 10))},
                              {"SPY": bars})
    assert report.total_signals == 500
    assert report.verdict == "usable frequency"


def test_frequency_breaks_down_by_year():
    """Concentration in one year is itself a finding -- a setup that only fired
    in 2020 has no evidence across regimes."""
    bars = _bars(800, start="2020-01-01")
    report = frequency_report("x", {"SPY": _events([0, 1, 300, 301, 302])},
                              {"SPY": bars})
    assert sum(report.per_year.values()) == 5
    assert len(report.per_year) >= 2


def test_frequency_aggregates_across_symbols():
    bars = {"SPY": _bars(500), "QQQ": _bars(500)}
    events = {"SPY": _events(range(0, 500, 5)), "QQQ": _events(range(0, 500, 5))}
    report = frequency_report("x", events, bars)

    assert report.symbols == 2
    assert report.total_bars == 1000
    assert report.total_signals == 200


# --- overlap ---------------------------------------------------------------

def test_identical_setups_overlap_completely():
    events = {"SPY": _events([10, 20, 30])}
    result = overlap("a", events, "b", events)

    assert result.shared == 3
    assert result.jaccard == pytest.approx(1.0)
    assert "FOLD" in result.verdict


def test_disjoint_setups_are_distinct():
    result = overlap("a", {"SPY": _events([1, 2, 3])},
                     "b", {"SPY": _events([50, 51, 52])})
    assert result.shared == 0
    assert result.verdict == "distinct"


def test_containment_is_caught_even_when_jaccard_looks_modest():
    """H4 firing 20 times, all of which H3 also produces, is fully contained.
    Jaccard alone would report 20% and hide it -- which is why the asymmetric
    view exists."""
    big = {"SPY": _events(range(0, 100))}
    small = {"SPY": _events(range(0, 20))}
    result = overlap("h3_sweep", big, "h4_ifvg", small)

    assert result.jaccard == pytest.approx(0.2)
    assert result.overlap_of_smaller == pytest.approx(1.0)
    assert "FOLD" in result.verdict


def test_partial_overlap_is_reported_jointly():
    result = overlap("a", {"SPY": _events(range(0, 100))},
                     "b", {"SPY": _events(range(60, 160))})
    assert 0.30 <= result.overlap_of_smaller < 0.60
    assert "report results jointly" in result.verdict


def test_overlap_uses_entry_bar_not_trigger_bar():
    """Two setups triggering on different bars but entering the same day put you
    in the same position -- evidentially the same trade."""
    a = {"SPY": [SignalEvent("a", 5, 5, 6, 0, 0, 0)]}
    b = {"SPY": [SignalEvent("b", 3, 5, 6, 0, 0, 0)]}
    assert overlap("a", a, "b", b).shared == 1


def test_same_bar_on_different_symbols_is_not_shared():
    a = {"SPY": _events([10])}
    b = {"QQQ": _events([10])}
    assert overlap("a", a, "b", b).shared == 0


def test_overlap_matrix_covers_every_pair():
    setups = {
        "h2": {"SPY": _events([1, 2])},
        "h3": {"SPY": _events([2, 3])},
        "h4": {"SPY": _events([3, 4])},
    }
    results = overlap_matrix(setups)
    assert len(results) == 3
    assert {(r.setup_a, r.setup_b) for r in results} == {
        ("h2", "h3"), ("h2", "h4"), ("h3", "h4")
    }
