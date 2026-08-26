"""Choosing a contract for a swing plan, and pricing what it costs.

The selection rules exist because the default retail choice -- a cheap
out-of-the-money option near expiry -- is the worst available expression of a
3-15 day directional view. It maximises the two things working against you
(time decay and the share of premium that is pure time value) in exchange for
leverage you do not need at this account size.

Rules, and why each one is here
-------------------------------
EXPIRY AT LEAST 2x THE HOLD. Decay accelerates into expiry. Buying 10 days of
option for a 10-day trade means paying the steepest part of the curve and
having no room if the thesis takes longer than planned -- which it usually does.

DEEP IN THE MONEY, delta around 0.70-0.80. A high-delta call tracks the stock
closely and carries little extrinsic value, so most of what you pay is
intrinsic and cannot decay. It behaves like leveraged stock, which is what a
directional swing view actually wants. Out-of-the-money calls are a bet on
speed as well as direction, and nothing in this project has established any
ability to forecast speed.

NEVER SPANNING EARNINGS UNLESS INTENDED. Two separate reasons: the gap risk
that already vetoes the stock trade, and implied volatility collapsing after
the report, which loses money even when the direction is right.

LIQUIDITY FILTERS. A spread of 8% of premium costs 16% round trip before the
trade is right or wrong. On a $10,000 account that is the difference between a
strategy and a donation.

SIZED ON THE MOVE TO THE STOP, NOT ON THE PREMIUM. If the underlying stop is
honoured, the loss is roughly delta x stop distance, plus the spread and the
decay accrued. That is the number risk should be measured against -- treating
the whole premium as the risk overstates it and leads to positions far too
small to matter, which is its own failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .contracts import OptionContract

SHARES_PER_CONTRACT = 100


@dataclass(frozen=True)
class SelectionRules:
    target_delta: float = 0.75
    min_delta: float = 0.60
    max_delta: float = 0.90
    expiry_multiple: float = 2.0        # of the planned hold
    max_spread_pct: float = 0.05
    min_open_interest: int = 100
    min_volume: int = 0
    max_extrinsic_pct: float = 0.25     # of premium


@dataclass(frozen=True)
class OptionPlan:
    """A contract, sized, with every cost stated."""

    contract: OptionContract
    contracts: int
    premium: float                  # per contract, in dollars
    cost: float                     # total outlay
    stop_loss_estimate: float       # dollars lost if the underlying stop is hit
    spread_cost: float              # round-trip, total
    decay_cost: float               # theta over the planned hold, total
    breakeven: float                # underlying price needed at expiry
    stock_breakeven: float          # what the stock trade needed
    effective_leverage: float | None
    shares_equivalent: int          # what the same risk buys in stock
    rejections: tuple[str, ...] = ()

    @property
    def is_tradeable(self) -> bool:
        return not self.rejections and self.contracts > 0

    @property
    def friction_pct(self) -> float:
        """Spread plus decay as a share of the outlay. What the trade costs
        before direction matters at all."""
        return (self.spread_cost + self.decay_cost) / self.cost if self.cost > 0 else 0.0


def eligible_contracts(
    chain: list[OptionContract],
    *,
    as_of: date,
    hold_days: int,
    earnings_in_days: int | None = None,
    rules: SelectionRules | None = None,
) -> tuple[list[OptionContract], dict[str, int]]:
    """Filter a chain to contracts that can express the plan.

    Returns the survivors and a count of why the others were dropped, because
    "no contract qualified" and "no contract qualified because every spread was
    12% wide" call for different responses.
    """
    rules = rules or SelectionRules()
    minimum_days = int(hold_days * rules.expiry_multiple)
    dropped: dict[str, int] = {}

    def drop(reason: str) -> None:
        dropped[reason] = dropped.get(reason, 0) + 1

    kept: list[OptionContract] = []
    for contract in chain:
        if contract.right != "C":
            drop("not a call")
            continue
        days = contract.days_to_expiry(as_of)
        if days < minimum_days:
            drop(f"expires inside {minimum_days} days")
            continue
        if earnings_in_days is not None and days >= earnings_in_days:
            drop("spans earnings")
            continue
        if contract.bid <= 0 or contract.ask <= 0:
            drop("no two-sided market")
            continue
        spread = contract.spread_pct
        if spread is None or spread > rules.max_spread_pct:
            drop(f"spread wider than {rules.max_spread_pct:.0%}")
            continue
        if contract.open_interest < rules.min_open_interest:
            drop(f"open interest below {rules.min_open_interest}")
            continue
        if contract.volume < rules.min_volume:
            drop("volume too low")
            continue
        if contract.delta is not None and not (
            rules.min_delta <= contract.delta <= rules.max_delta
        ):
            drop("delta outside range")
            continue
        kept.append(contract)

    return kept, dropped


def choose_contract(
    chain: list[OptionContract],
    *,
    as_of: date,
    hold_days: int,
    earnings_in_days: int | None = None,
    rules: SelectionRules | None = None,
) -> OptionContract | None:
    """The eligible contract closest to the target delta, nearest expiry first.

    Nearest expiry among the eligible, not furthest: once the expiry clears the
    hold with margin, additional time is additional premium for nothing.
    """
    rules = rules or SelectionRules()
    kept, _ = eligible_contracts(
        chain, as_of=as_of, hold_days=hold_days,
        earnings_in_days=earnings_in_days, rules=rules,
    )
    if not kept:
        return None

    def score(contract: OptionContract) -> tuple:
        delta_gap = (
            abs(contract.delta - rules.target_delta)
            if contract.delta is not None
            else 1.0
        )
        return (round(delta_gap, 3), contract.days_to_expiry(as_of))

    return min(kept, key=score)


def plan_option_trade(
    contract: OptionContract,
    *,
    underlying_price: float,
    stop_price: float,
    hold_days: int,
    risk_budget: float,
    cash_available: float,
    as_of: date,
    rules: SelectionRules | None = None,
) -> OptionPlan:
    """Size the position and price every cost it carries."""
    rules = rules or SelectionRules()
    premium = contract.mid * SHARES_PER_CONTRACT
    stop_distance = max(underlying_price - stop_price, 0.0)
    delta = contract.delta if contract.delta is not None else 0.75

    # What the underlying stop actually costs in option terms, plus the friction
    # that accrues whether or not the trade works.
    directional_loss = delta * stop_distance * SHARES_PER_CONTRACT
    spread_per_contract = contract.spread * SHARES_PER_CONTRACT
    theta_per_contract = abs(contract.theta or 0.0) * hold_days * SHARES_PER_CONTRACT
    loss_per_contract = directional_loss + spread_per_contract + theta_per_contract

    contracts = int(risk_budget // loss_per_contract) if loss_per_contract > 0 else 0
    if contracts > 0 and contracts * premium > cash_available:
        contracts = int(cash_available // premium)

    rejections: list[str] = []
    if contracts <= 0:
        rejections.append(
            "one contract risks more than the trade's risk budget allows"
        )
    if contract.days_to_expiry(as_of) < hold_days:
        rejections.append("expires before the planned hold ends")
    extrinsic = contract.extrinsic(underlying_price)
    if contract.mid > 0 and extrinsic / contract.mid > rules.max_extrinsic_pct:
        rejections.append(
            f"{extrinsic / contract.mid:.0%} of the premium is time value, "
            f"above the {rules.max_extrinsic_pct:.0%} limit — this is a bet on "
            "speed as much as direction"
        )

    cost = contracts * premium
    return OptionPlan(
        contract=contract,
        contracts=contracts,
        premium=premium,
        cost=cost,
        stop_loss_estimate=contracts * directional_loss,
        spread_cost=contracts * spread_per_contract,
        decay_cost=contracts * theta_per_contract,
        breakeven=contract.strike + contract.mid,
        stock_breakeven=underlying_price,
        effective_leverage=(
            (delta * underlying_price * SHARES_PER_CONTRACT) / premium
            if premium > 0 else None
        ),
        shares_equivalent=(
            int(risk_budget // stop_distance) if stop_distance > 0 else 0
        ),
        rejections=tuple(rejections),
    )
