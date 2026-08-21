"""Engine behaviour on hand-built bars.

Each test constructs the smallest price path that isolates one rule, so a
failure names the rule that broke rather than 'the backtest changed'.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from screener.backtest.engine import (
    Candidate,
    CostModel,
    ExitRule,
    run_backtest,
)
from screener.calc.sizing import RiskLimits

NO_COSTS = CostModel(slippage_bps=0.0)


def frame(rows: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    """rows: (iso_date, open, high, low, close). Volume is constant."""
    index = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
            "volume": [1_000_000.0] * len(rows),
        },
        index=index,
    )


def days(start: str, n: int) -> list[str]:
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def run(bars, candidates, **kwargs):
    kwargs.setdefault("costs", NO_COSTS)
    kwargs.setdefault("start", date(2020, 1, 1))
    kwargs.setdefault("end", date(2030, 1, 1))
    return run_backtest(candidates, bars, **kwargs)


# --------------------------------------------------------------------------
# Execution timing
# --------------------------------------------------------------------------

def test_fills_at_the_open_of_the_entry_bar_not_the_signal_close():
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 101, 99, 100),
        (d[1], 100, 101, 99, 100),
        (d[2], 105, 106, 104, 105),   # entry bar: opens at 105
        (d[3], 105, 106, 104, 105),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[1]), date.fromisoformat(d[2]), 95.0)

    result = run(bars, [candidate])

    assert len(result.trades) == 1
    # 105, the open of the entry bar -- not 100, the close of the signal bar.
    assert result.trades[0].entry_price == Decimal("105.00")
    assert result.trades[0].entry_date == date.fromisoformat(d[2])


def test_slippage_is_charged_on_both_sides():
    d = days("2020-01-01", 5)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),
        (d[2], 100, 100, 100, 100),   # entry
        (d[3], 100, 100, 100, 100),
        (d[4], 100, 100, 100, 100),   # time exit
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[1]), date.fromisoformat(d[2]), 90.0)

    result = run(
        bars, [candidate],
        costs=CostModel(slippage_bps=100.0),   # 1% per side, exaggerated for clarity
        exit_rule=ExitRule(r_multiple=None, time_limit=2),
    )

    trade = result.trades[0]
    assert trade.entry_price == Decimal("101.00")   # paid up
    assert trade.exit_price == Decimal("99.00")     # sold down
    assert trade.pnl < 0                             # a flat market still loses to costs


def test_entry_outside_the_window_is_not_taken():
    d = days("2020-01-01", 3)
    bars = {"AAA": frame([(x, 100, 101, 99, 100) for x in d])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[2]), 95.0)

    result = run(bars, [candidate], end=date.fromisoformat(d[1]))

    assert result.trades == []


# --------------------------------------------------------------------------
# Exit resolution
# --------------------------------------------------------------------------

def test_target_exit_fills_at_the_target():
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),   # entry at 100, stop 95 -> risk 5, 2R target = 110
        (d[2], 101, 112, 100, 111),   # high tags 110
        (d[3], 111, 112, 110, 111),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=2.0, time_limit=None))

    trade = result.trades[0]
    assert trade.exit_reason == "target"
    assert trade.exit_price == Decimal("110.00")
    assert trade.r_multiple == pytest.approx(2.0)


def test_stop_exit_fills_at_the_stop():
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),
        (d[2], 99, 100, 94, 96),      # low pierces 95
        (d[3], 96, 97, 95, 96),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=2.0, time_limit=None))

    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.exit_price == Decimal("95.00")
    assert trade.r_multiple == pytest.approx(-1.0)


def test_ambiguous_bar_resolves_to_the_stop():
    """A bar containing both levels cannot say which came first. Assume the
    worse one -- this is the whole reason daily backtests overstate results."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),
        (d[2], 100, 115, 94, 112),    # touches BOTH the 110 target and the 95 stop
        (d[3], 112, 113, 111, 112),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=2.0, time_limit=None))

    assert result.trades[0].exit_reason == "stop"


def test_gap_through_the_stop_fills_at_the_open_not_the_stop():
    """A stop is not a guaranteed price."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),
        (d[2], 88, 90, 87, 89),       # opens 7 below the 95 stop
        (d[3], 89, 90, 88, 89),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=2.0, time_limit=None))

    trade = result.trades[0]
    assert trade.exit_reason == "stop_gap"
    assert trade.exit_price == Decimal("88.00")
    assert trade.r_multiple < -1.0    # worse than the planned risk, as it would be


def test_time_exit_fires_at_the_open_of_the_nth_bar():
    d = days("2020-01-01", 8)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),   # entry
        (d[2], 101, 102, 100, 101),
        (d[3], 102, 103, 101, 102),
        (d[4], 103, 104, 102, 103),   # 3 bars held -> exit at this open
        (d[5], 104, 105, 103, 104),
        (d[6], 105, 106, 104, 105),
        (d[7], 106, 107, 105, 106),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=None, time_limit=3))

    trade = result.trades[0]
    assert trade.exit_reason == "time"
    assert trade.bars_held == 3
    assert trade.exit_price == Decimal("103.00")


def test_position_is_not_exited_on_its_own_entry_bar():
    """The entry bar's range is mostly in the past at the moment of the open
    fill. Letting it trigger the stop would trade on the fill's own future."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 101, 90, 99),     # entry bar dips below the 95 stop
        (d[2], 99, 100, 98, 99),
        (d[3], 99, 100, 98, 99),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=2.0, time_limit=None))

    assert result.trades[0].exit_date != date.fromisoformat(d[1])


# --------------------------------------------------------------------------
# Portfolio constraints
# --------------------------------------------------------------------------

def test_concurrent_position_cap_is_enforced():
    d = days("2020-01-01", 6)
    tickers = [f"S{i}" for i in range(8)]
    bars = {
        t: frame([(x, 100, 101, 99, 100) for x in d]) for t in tickers
    }
    candidates = [
        Candidate(t, "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0, rank=i)
        for i, t in enumerate(tickers)
    ]

    result = run(
        bars, candidates,
        exit_rule=ExitRule(r_multiple=None, time_limit=None, use_stop=True),
        limits=RiskLimits(max_concurrent_positions=3),
    )

    assert len(result.trades) == 3


def test_higher_ranked_candidates_win_scarce_slots():
    d = days("2020-01-01", 4)
    bars = {t: frame([(x, 100, 101, 99, 100) for x in d]) for t in ("LOW", "HIGH")}
    candidates = [
        Candidate(
            "LOW", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0, rank=0.1
        ),
        Candidate(
            "HIGH", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0, rank=9.9
        ),
    ]

    result = run(bars, candidates, limits=RiskLimits(max_concurrent_positions=1))

    assert [t.ticker for t in result.trades] == ["HIGH"]


def test_sector_cap_is_enforced():
    d = days("2020-01-01", 4)
    tickers = ["A", "B", "C"]
    bars = {t: frame([(x, 100, 101, 99, 100) for x in d]) for t in tickers}
    candidates = [
        Candidate(
            t, "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0, sector="tech"
        )
        for t in tickers
    ]

    result = run(bars, candidates, limits=RiskLimits(max_positions_per_sector=2))

    assert len(result.trades) == 2


def test_risk_per_trade_matches_the_sizing_rule():
    """1% of $10,000 is $100. A $5 stop distance buys 20 shares."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([(x, 100, 101, 99, 100) for x in d])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], starting_equity=10_000)

    assert result.trades[0].shares == 20
    assert result.trades[0].risk_dollars == Decimal("100.00")


def test_equity_curve_reflects_realised_and_unrealised_value():
    d = days("2020-01-01", 5)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),   # entry at 100, 20 shares
        (d[2], 100, 105, 100, 105),   # +5/share unrealised = +100
        (d[3], 105, 105, 105, 105),
        (d[4], 105, 105, 105, 105),
    ])}
    candidate = Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0)

    result = run(bars, [candidate], exit_rule=ExitRule(r_multiple=None, time_limit=None))

    assert result.equity_curve.loc[pd.Timestamp(d[1])] == pytest.approx(10_000.0)
    assert result.equity_curve.loc[pd.Timestamp(d[2])] == pytest.approx(10_100.0)


def test_no_duplicate_position_in_the_same_symbol():
    d = days("2020-01-01", 5)
    bars = {"AAA": frame([(x, 100, 101, 99, 100) for x in d])}
    candidates = [
        Candidate("AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]), 95.0),
        Candidate("AAA", "test", date.fromisoformat(d[1]), date.fromisoformat(d[2]), 95.0),
    ]

    result = run(bars, candidates, exit_rule=ExitRule(r_multiple=None, time_limit=None))

    assert len(result.trades) == 1
    assert result.rejected.get("already_open") == 1


def test_exit_rule_that_never_exits_is_rejected():
    with pytest.raises(ValueError, match="never exits"):
        ExitRule(r_multiple=None, time_limit=None, use_stop=False)


# --------------------------------------------------------------------------
# Stop semantics -- found by a live run, not by inspection
# --------------------------------------------------------------------------

def test_entry_relative_stop_is_measured_from_the_fill_not_the_prior_close():
    """docs/03 H1 says "stop at entry - k x ATR". Anchoring to the last close
    instead lets the overnight gap decide how much is risked."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 90, 91, 89, 90),      # gaps down 10 before we fill
        (d[2], 90, 91, 89, 90),
        (d[3], 90, 91, 89, 90),
    ])}
    candidate = Candidate(
        "AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]),
        stop_distance=5.0, atr=2.0,
    )

    result = run(bars, [candidate])

    trade = result.trades[0]
    assert trade.entry_price == Decimal("90.00")
    assert trade.stop == Decimal("85.00"), "5 below the FILL, not 5 below yesterday"


def test_a_gap_down_onto_an_absolute_stop_is_refused_not_traded_at_absurd_risk():
    """The live H1 failure. Filling just above a fixed stop leaves a tiny risk
    per share, and an ordinary day's move then reads as a loss of many R --
    the statistic breaks before the trade does."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 95.1, 96, 94, 95),    # opens a dime above the 95 stop
        (d[2], 95, 96, 94, 95),
        (d[3], 95, 96, 94, 95),
    ])}
    candidate = Candidate(
        "AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]),
        stop_level=95.0, atr=2.0,
    )

    result = run(bars, [candidate])

    assert result.trades == []
    assert result.rejected.get("stop too close after the gap") == 1


def test_a_normal_distance_to_an_absolute_stop_still_trades():
    """The control for the test above: the guard must not reject ordinary
    setups, only degenerate ones."""
    d = days("2020-01-01", 4)
    bars = {"AAA": frame([(x, 100, 101, 99, 100) for x in d])}
    candidate = Candidate(
        "AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]),
        stop_level=95.0, atr=2.0,
    )

    assert len(run(bars, [candidate]).trades) == 1


def test_a_candidate_needs_exactly_one_kind_of_stop():
    args = ("AAA", "test", date(2020, 1, 1), date(2020, 1, 2))
    with pytest.raises(ValueError, match="exactly one"):
        Candidate(*args)
    with pytest.raises(ValueError, match="exactly one"):
        Candidate(*args, stop_level=95.0, stop_distance=5.0)


def test_a_non_positive_stop_distance_is_rejected():
    with pytest.raises(ValueError, match="must be positive"):
        Candidate("AAA", "test", date(2020, 1, 1), date(2020, 1, 2), stop_distance=0.0)


def test_removing_the_stop_lets_a_trade_survive_a_drawdown_it_would_have_lost_to():
    """The diagnostic behind --no-stop: if a losing configuration turns
    profitable without the stop, the entry rule was never the problem."""
    d = days("2020-01-01", 6)
    bars = {"AAA": frame([
        (d[0], 100, 100, 100, 100),
        (d[1], 100, 100, 100, 100),   # entry at 100, stop 95
        (d[2], 99, 100, 90, 98),      # would stop out here
        (d[3], 98, 105, 97, 104),
        (d[4], 104, 112, 103, 111),
        (d[5], 111, 112, 110, 111),
    ])}
    candidate = Candidate(
        "AAA", "test", date.fromisoformat(d[0]), date.fromisoformat(d[1]),
        stop_level=95.0,
    )

    stopped = run(
        bars, [candidate],
        exit_rule=ExitRule(r_multiple=None, time_limit=4, use_stop=True),
    )
    unstopped = run(
        bars, [candidate],
        exit_rule=ExitRule(r_multiple=None, time_limit=4, use_stop=False),
    )

    assert stopped.trades[0].exit_reason == "stop"
    assert stopped.trades[0].pnl < 0
    assert unstopped.trades[0].exit_reason == "time"
    assert unstopped.trades[0].pnl > 0
