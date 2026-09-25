"""Bar-by-bar portfolio simulator.

Design commitments, each of which exists because the opposite is the standard
way a backtest lies:

DECISION AND EXECUTION ARE DIFFERENT BARS.
    A signal completes at the close of bar ``t``. It fills at the OPEN of bar
    ``t+1``. Filling at the close of the bar that produced the signal is the
    single most common lookahead bug, and it is not expressible here: the
    engine takes an entry date, and the signal generators only ever emit
    ``t+1``.

AMBIGUOUS BARS RESOLVE AGAINST US.
    When a bar's range contains both the stop and the target, daily data cannot
    say which came first. The engine assumes the STOP. This understates results
    on those bars, which is the correct direction to be wrong in.

GAPS FILL AT THE OPEN, NOT THE STOP.
    A stop is not a guaranteed price. If a bar opens below the stop, the exit
    fills at that open -- worse than the stop -- because that is what would have
    happened.

COSTS ARE CHARGED BOTH WAYS.
    Slippage is applied on entry and exit, in the adverse direction each time.

SIZING GOES THROUGH THE RISK MANAGER.
    Share counts come from ``calc.sizing.plan_position``, the same function the
    live path uses. A backtest that sizes differently from the live system is
    measuring a strategy nobody can trade.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd

from ..calc.sizing import RiskLimits, plan_position

CENT = Decimal("0.01")


def _money(value: float | int | str | Decimal) -> Decimal:
    return (value if isinstance(value, Decimal) else Decimal(str(value))).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


@dataclass(frozen=True)
class Candidate:
    """A setup that has triggered and is ready to execute on ``entry_date``.

    A stop is expressed one of two ways, and the distinction is not cosmetic:

    ``stop_level``     an absolute price. Correct where the stop IS the setup's
                       geometry -- the far edge of a gap, the low of a sweep.
                       Those levels mean something specific; moving them to
                       follow the fill would discard the reason for the trade.

    ``stop_distance``  a distance below the fill. Correct where the spec says
                       "entry minus k x ATR" (H1), because then the RISK is the
                       constant and the level follows from wherever we filled.

    Using an absolute level where the spec calls for a distance produces a risk
    per share that varies with the overnight gap -- and when a stock opens just
    above its level, a tiny risk per share turns an ordinary day's move into a
    loss of many R.
    """

    ticker: str
    setup: str
    signal_date: date
    entry_date: date
    stop_level: float | None = None
    stop_distance: float | None = None
    atr: float | None = None   # for the minimum-stop-distance guard
    rank: float = 0.0          # higher wins when slots are scarce
    sector: str | None = None

    def __post_init__(self) -> None:
        if (self.stop_level is None) == (self.stop_distance is None):
            raise ValueError(
                "a candidate needs exactly one of stop_level or stop_distance"
            )
        if self.stop_distance is not None and self.stop_distance <= 0:
            raise ValueError("stop_distance must be positive for a long position")

    def stop_for(self, fill: Decimal) -> Decimal:
        if self.stop_distance is not None:
            return _money(fill - Decimal(str(self.stop_distance)))
        return _money(self.stop_level)


@dataclass(frozen=True)
class ExitRule:
    """How a position is closed. At least one of the three must be active."""

    r_multiple: float | None = 2.0     # target at entry + R x initial risk
    time_limit: int | None = 10        # exit at the open this many bars after entry
    use_stop: bool = True
    #: Ratchet the stop up to (highest close since entry) - trail_atr x ATR,
    #: never down. None leaves the stop where it was set at entry.
    #:
    #: This is the mechanism a convex strategy lives on. Selection in small
    #: caps was measured 2026-09-22 to pick VOLATILITY symmetrically -- the top
    #: momentum decile's best 1% runs to +34.9% against the universe's +25.5%,
    #: and its worst 1% to -31.4% against -22.6% -- with a median edge of
    #: +0.05% per 20 days, which is less than the spread costs to trade. So the
    #: selection does not pay. The asymmetry has to be manufactured by cutting
    #: the left tail while leaving the right one alone, and that is what this
    #: does.
    trail_atr: float | None = None

    def __post_init__(self) -> None:
        # A target at 0R sits exactly on the entry price, so the next bar whose
        # high reaches the entry closes the trade at entry minus slippage --
        # every trade a guaranteed small loss, reported as a "target" exit.
        # Eight battery experiments passed r_multiple=0 meaning "no target" and
        # measured that instead, including every *_exit_isolated arm. Negative
        # multiples are equally meaningless: a target below the entry on a long.
        #
        # The value is NOT rewritten to None here. `has_target` is the single
        # predicate that decides whether a target exists, so 0 means "no
        # target" identically in the config that gets logged and in the rule
        # that gets executed. Rewriting it made the two disagree, and a second
        # pass over RunConfig.resolved() then read the resulting None as
        # "unspecified" and handed h2-h4 their 2R default back.
        if not self.use_stop and not self.has_target and not self.has_time_limit:
            raise ValueError("an ExitRule with no stop, no target and no time limit never exits")

    @property
    def has_target(self) -> bool:
        return self.r_multiple is not None and self.r_multiple > 0

    @property
    def has_time_limit(self) -> bool:
        """Zero means NO time exit, exactly as zero means no target.

        The engine tested `time_limit is not None and held >= time_limit`, so a
        time_limit of 0 made `held >= 0` true on the first bar after entry and
        closed every position the next day. Found 2026-09-22 on the first run
        of the trailing-stop strategy: 687 trades, every one exiting on time,
        expectancy -0.011R, and a trailing stop that never fired once.

        This is the same shape as the r_multiple=0 bug that voided eight
        battery experiments, in the other exit parameter, and it survived
        because `resolved()` already treats 0 as "no time exit" -- so the
        config that was logged and the rule that ran disagreed.
        """
        return self.time_limit is not None and self.time_limit > 0


@dataclass(frozen=True)
class CostModel:
    """What a fill gives up, per side, as basis points of the fill price.

    Two modes. With `spreads` absent it charges `slippage_bps` to everything,
    which is what this project did until 2026-09-24 and is wrong in a specific
    direction: 5bp a side is roughly right for a mega cap and roughly a third
    of the truth for the mid and small caps the universe moved to. Measured on
    the development split, the median symbol above the $2M dollar-volume floor
    runs a 27bp round trip against the 10bp this charged.

    With `spreads` supplied -- a ticker-keyed table from
    `calc.spread.spread_table` -- each symbol is charged its OWN measured
    spread as of the fill date, and the flat rate serves only as the fallback
    for symbols the table does not cover.

    HALF the spread per side. The quoted spread spans both sides, so buying at
    the ask and selling at the bid gives up one full spread across the round
    trip, not two. Charging the full figure twice is the usual way this
    arithmetic goes wrong, and it would overstate costs by 2x.
    """

    slippage_bps: float = 5.0
    commission_per_trade: Decimal = Decimal("0")
    #: ticker -> date-indexed trailing spread as a FRACTION (0.004 == 40bp
    #: round trip). Kept out of equality and hashing: a frozen dataclass would
    #: otherwise try to hash a dict of Series and raise.
    spreads: Mapping[str, pd.Series] | None = field(default=None, compare=False)

    def half_spread_bps(self, ticker: str | None, day: pd.Timestamp | None) -> float:
        """Basis points given up crossing ONE side, for this symbol on this day.

        Falls back to the flat rate whenever the table cannot answer: no table,
        no entry for the symbol, or a date before the symbol's estimate begins.
        `Series.asof` takes the last value at or before `day` and never looks
        forward, and the table is already shifted a session, so the figure used
        for a fill at today's open rests only on sessions that have closed.
        """
        if self.spreads is None or ticker is None or day is None:
            return self.slippage_bps
        series = self.spreads.get(ticker)
        if series is None or series.empty:
            return self.slippage_bps
        try:
            spread = series.asof(day)
        except (KeyError, TypeError):
            return self.slippage_bps
        if spread is None or not np.isfinite(spread):
            return self.slippage_bps
        return float(spread) * 10_000.0 / 2.0

    def buy_fill(
        self,
        price: Decimal,
        ticker: str | None = None,
        day: pd.Timestamp | None = None,
    ) -> Decimal:
        bps = Decimal(str(self.half_spread_bps(ticker, day)))
        return _money(price * (Decimal("1") + bps / Decimal("10000")))

    def sell_fill(
        self,
        price: Decimal,
        ticker: str | None = None,
        day: pd.Timestamp | None = None,
    ) -> Decimal:
        bps = Decimal(str(self.half_spread_bps(ticker, day)))
        return _money(price * (Decimal("1") - bps / Decimal("10000")))


@dataclass
class Trade:
    ticker: str
    setup: str
    entry_date: date
    entry_price: Decimal
    shares: int
    stop: Decimal
    target: Decimal | None
    risk_dollars: Decimal
    exit_date: date | None = None
    exit_price: Decimal | None = None
    exit_reason: str | None = None
    bars_held: int = 0

    @property
    def is_open(self) -> bool:
        return self.exit_date is None

    @property
    def pnl(self) -> Decimal:
        if self.exit_price is None:
            return Decimal("0")
        return _money((self.exit_price - self.entry_price) * self.shares)

    @property
    def r_multiple(self) -> float | None:
        """P&L expressed in units of the risk taken. The only comparable unit."""
        if self.exit_price is None or self.risk_dollars <= 0:
            return None
        return float(self.pnl / self.risk_dollars)


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.Series
    starting_equity: Decimal
    ending_equity: Decimal
    rejected: dict[str, int] = field(default_factory=dict)
    entries_without_sector: int = 0

    @property
    def closed_trades(self) -> list[Trade]:
        return [t for t in self.trades if not t.is_open]


@dataclass
class _Position:
    trade: Trade
    entry_bar_index: int
    sector: str | None = None
    #: Highest close seen since entry, and the ATR the stop trails by. Both are
    #: needed only for a trailing exit; `peak_close` starts at the fill so the
    #: stop can never ratchet BELOW where it began.
    peak_close: Decimal = Decimal("0")
    atr: Decimal | None = None


def _bar(frame: pd.DataFrame, day: pd.Timestamp) -> pd.Series | None:
    try:
        return frame.loc[day]
    except KeyError:
        return None


def run_backtest(
    candidates: Sequence[Candidate],
    bars_by_symbol: dict[str, pd.DataFrame],
    *,
    start: date,
    end: date,
    starting_equity: float | Decimal = 10_000,
    exit_rule: ExitRule | None = None,
    limits: RiskLimits | None = None,
    costs: CostModel | None = None,
    min_stop_distance_atr: float = 0.25,
) -> BacktestResult:
    """Simulate ``candidates`` over the window and return trades plus equity.

    The daily sequence is: mark open positions, exit what must exit, then enter
    what is scheduled for today. Exits are processed before entries so that a
    slot freed at today's open is available at today's open -- both happen at
    the same price stamp, so this introduces no lookahead.
    """
    exit_rule = exit_rule or ExitRule()
    limits = limits or RiskLimits()
    costs = costs or CostModel()

    equity = _money(starting_equity)
    cash = equity

    by_entry_date: dict[pd.Timestamp, list[Candidate]] = {}
    for candidate in candidates:
        stamp = pd.Timestamp(candidate.entry_date)
        if start <= candidate.entry_date <= end:
            by_entry_date.setdefault(stamp, []).append(candidate)

    calendar = sorted(
        {
            day
            for frame in bars_by_symbol.values()
            for day in frame.index
            if start <= day.date() <= end
        }
    )
    bar_index = {day: i for i, day in enumerate(calendar)}

    open_positions: dict[str, _Position] = {}
    trades: list[Trade] = []
    entries_without_sector = 0
    rejected: dict[str, int] = {}
    curve: dict[pd.Timestamp, float] = {}

    for i, day in enumerate(calendar):
        # ---- exits ------------------------------------------------------
        for ticker in list(open_positions):
            position = open_positions[ticker]
            frame = bars_by_symbol[ticker]
            row = _bar(frame, day)
            if row is None:
                continue
            if i == position.entry_bar_index:
                continue  # entered at today's open; give it a bar to work

            held = i - position.entry_bar_index
            trade = position.trade
            open_p = Decimal(str(row["open"]))
            low_p = Decimal(str(row["low"]))
            high_p = Decimal(str(row["high"]))

            # Ratchet BEFORE testing exits, using only closes up to YESTERDAY.
            # Raising the stop on today's close and then testing today's low
            # against it would exit on a level the price never traded through
            # while the position was subject to it -- lookahead inside a single
            # bar, and the kind that never shows up as a truncation failure.
            if exit_rule.trail_atr is not None and position.atr is not None:
                distance = Decimal(str(exit_rule.trail_atr)) * position.atr
                raised = _money(position.peak_close - distance)
                if raised > trade.stop:
                    trade.stop = raised

            exit_price: Decimal | None = None
            reason: str | None = None

            # A bar with no volume is not a session the position lived through;
            # it is a security that did not trade. 379 symbols in this database
            # carry 59,524 such bars and 140 are frozen at the END of a series
            # -- acquired or delisted, with the last price repeating forever.
            #
            # Without this, a position held into an acquisition can never
            # leave: the price never moves, so a trailing stop cannot ratchet
            # and a stop can never be hit, and docs/10 specifies no time limit.
            # The backtest then holds it to the end of the split at a frozen
            # mark and reports it as an open position that simply went quiet.
            #
            # It exits at the open, which IS the frozen price, with costs
            # charged. That is not what an acquisition really pays -- cash or
            # stock at terms this database does not record -- but it is the
            # last price at which the position demonstrably could be sold, and
            # by the ambiguity rule the unrecorded half resolves against us.
            #
            # NOT configurable, deliberately. Holding a security that is not
            # trading is not a strategy choice anybody could make; it is a data
            # artifact, and a flag to disable it would only ever be used to
            # make a result look better.
            if "volume" in row.index and float(row["volume"]) <= 0:
                exit_price = costs.sell_fill(open_p, ticker, day)
                reason = "no_volume"
            elif exit_rule.has_time_limit and held >= exit_rule.time_limit:
                # Chronologically first event of the day: fills at the open.
                exit_price = costs.sell_fill(open_p, ticker, day)
                reason = "time"
            elif exit_rule.use_stop and open_p <= trade.stop:
                exit_price = costs.sell_fill(open_p, ticker, day)  # gapped through
                reason = "stop_gap"
            elif exit_rule.use_stop and low_p <= trade.stop:
                exit_price = costs.sell_fill(trade.stop, ticker, day)
                reason = "stop"
            elif trade.target is not None and high_p >= trade.target:
                exit_price = costs.sell_fill(trade.target, ticker, day)
                reason = "target"

            if exit_price is not None:
                trade.exit_date = day.date()
                trade.exit_price = exit_price
                trade.exit_reason = reason
                trade.bars_held = held
                cash = _money(cash + exit_price * trade.shares - costs.commission_per_trade)
                del open_positions[ticker]

        # ---- mark to market ---------------------------------------------
        held_value = Decimal("0")
        for ticker, position in open_positions.items():
            row = _bar(bars_by_symbol[ticker], day)
            if row is not None:
                close_now = Decimal(str(row["close"]))
                if close_now > position.peak_close:
                    position.peak_close = close_now
            price = (
                Decimal(str(row["close"])) if row is not None else position.trade.entry_price
            )
            held_value += price * position.trade.shares
        equity = _money(cash + held_value)

        # ---- entries ----------------------------------------------------
        todays = sorted(by_entry_date.get(day, []), key=lambda c: -c.rank)
        for candidate in todays:
            if candidate.ticker in open_positions:
                rejected["already_open"] = rejected.get("already_open", 0) + 1
                continue
            frame = bars_by_symbol.get(candidate.ticker)
            row = _bar(frame, day) if frame is not None else None
            if row is None:
                rejected["no_bar"] = rejected.get("no_bar", 0) + 1
                continue
            # The same hole on the other side: a security that did not trade
            # cannot be bought either. The universe filter catches most of
            # these, but it drains `dollar_vol_50` over a rolling window, so a
            # frozen symbol stays eligible for ~50 sessions after its last real
            # trade -- DENN for 39 of them. This closes that window.
            if "volume" in row.index and float(row["volume"]) <= 0:
                rejected["no_volume"] = rejected.get("no_volume", 0) + 1
                continue

            fill = costs.buy_fill(Decimal(str(row["open"])), candidate.ticker, day)
            stop = candidate.stop_for(fill)

            # A stop that sits just under the fill makes the R denominator tiny,
            # and an ordinary day's move then reads as a loss of many R. The
            # statistic stops meaning anything before the trade does, so the
            # trade is refused rather than allowed to distort the record.
            if candidate.atr and min_stop_distance_atr > 0:
                floor = Decimal(str(candidate.atr * min_stop_distance_atr))
                if fill - stop < floor:
                    rejected["stop too close after the gap"] = (
                        rejected.get("stop too close after the gap", 0) + 1
                    )
                    continue
            open_risk = sum(
                (p.trade.risk_dollars for p in open_positions.values()), Decimal("0")
            )
            # A symbol with no sector mapping cannot be counted against a
            # sector cap, so the cap simply does not bind for it. Pooling all
            # unmapped names into one bucket would instead cap the whole
            # portfolio at two positions, which is a different rule entirely.
            # The count of such entries is reported so the gap is visible
            # rather than silent.
            if candidate.sector is None:
                sector_count = 0
            else:
                sector_count = sum(
                    1 for p in open_positions.values() if p.sector == candidate.sector
                )

            plan = plan_position(
                equity=equity,
                entry=fill,
                stop=stop,
                limits=limits,
                open_positions=len(open_positions),
                open_risk_pct=(open_risk / equity if equity > 0 else Decimal("0")),
                sector_positions=sector_count,
            )
            if not plan.is_tradeable:
                key = plan.reasons[0] if plan.reasons else "rejected"
                rejected[key] = rejected.get(key, 0) + 1
                continue

            cost = _money(fill * plan.shares + costs.commission_per_trade)
            if cost > cash:
                rejected["insufficient_cash"] = rejected.get("insufficient_cash", 0) + 1
                continue

            target = (
                _money(fill + Decimal(str(exit_rule.r_multiple)) * (fill - stop))
                if exit_rule.has_target
                else None
            )
            trade = Trade(
                ticker=candidate.ticker,
                setup=candidate.setup,
                entry_date=day.date(),
                entry_price=fill,
                shares=plan.shares,
                stop=stop,
                target=target,
                risk_dollars=plan.risk_dollars,
            )
            trades.append(trade)
            if candidate.sector is None:
                entries_without_sector += 1
            open_positions[candidate.ticker] = _Position(
                trade, bar_index[day], candidate.sector,
                peak_close=fill,
                atr=Decimal(str(candidate.atr)) if candidate.atr else None,
            )
            cash = _money(cash - cost)

        held_value = Decimal("0")
        for ticker, position in open_positions.items():
            row = _bar(bars_by_symbol[ticker], day)
            price = (
                Decimal(str(row["close"])) if row is not None else position.trade.entry_price
            )
            held_value += price * position.trade.shares
        equity = _money(cash + held_value)
        curve[day] = float(equity)

    return BacktestResult(
        trades=trades,
        equity_curve=pd.Series(curve, dtype="float64").sort_index(),
        starting_equity=_money(starting_equity),
        ending_equity=equity,
        rejected=rejected,
        entries_without_sector=entries_without_sector,
    )
