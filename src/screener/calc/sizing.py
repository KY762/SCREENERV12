"""Position sizing and risk constraints.

This module implements the Risk Manager veto conditions from the trader profile
(section 7.1). Those conditions exist because the operator's own journal
documents every loss tracing to a missing stop, a profit quota, divided
attention, or size escalation after a loss.

The design consequence is deliberate and load-bearing:

    A position that does not fit is REDUCED. The stop is never widened.

Widening a stop to accommodate a desired size is the mechanism behind
"I switched to NQ and started balling". There is no parameter here that permits
it, and there is no manual override.

Money is handled as Decimal. Floats are fine for indicators; they are not fine
for the number that determines how many shares get bought.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal


def _d(value: float | int | str | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class RiskLimits:
    """Portfolio risk constraints. Defaults are the approved profile values."""

    risk_pct_per_trade: Decimal = Decimal("0.01")      # 1% of equity
    max_position_pct: Decimal = Decimal("0.25")        # 25% of equity
    max_concurrent_positions: int = 5
    max_total_open_risk_pct: Decimal = Decimal("0.05")  # 5%
    max_positions_per_sector: int = 2


@dataclass(frozen=True)
class PositionPlan:
    """The computed plan for a candidate trade."""

    shares: int
    entry: Decimal
    stop: Decimal
    risk_per_share: Decimal
    risk_dollars: Decimal
    position_value: Decimal
    position_pct_of_equity: Decimal
    r_multiple_to_target: Decimal | None
    rejected: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def is_tradeable(self) -> bool:
        return not self.rejected and self.shares > 0


def plan_position(
    *,
    equity: float | Decimal,
    entry: float | Decimal,
    stop: float | Decimal,
    target: float | Decimal | None = None,
    limits: RiskLimits | None = None,
    open_positions: int = 0,
    open_risk_pct: float | Decimal = Decimal("0"),
    sector_positions: int = 0,
    min_r_multiple: float | Decimal | None = None,
) -> PositionPlan:
    """Compute share count and every constraint check for one candidate.

    Returns a plan even when rejected, with the reasons recorded -- a rejected
    trade is information, and silently returning zero shares would hide it.
    """
    limits = limits or RiskLimits()
    equity_d, entry_d, stop_d = _d(equity), _d(entry), _d(stop)
    reasons: list[str] = []

    if entry_d <= 0:
        reasons.append("entry price must be positive")
    if stop_d <= 0:
        reasons.append("stop price must be positive")
    if stop_d >= entry_d:
        reasons.append("stop must be below entry for a long position")

    zero = Decimal("0")
    if reasons:
        return PositionPlan(0, entry_d, stop_d, zero, zero, zero, zero, None, True, reasons)

    risk_per_share = entry_d - stop_d
    risk_budget = (equity_d * limits.risk_pct_per_trade).quantize(Decimal("0.01"))
    shares = int((risk_budget / risk_per_share).to_integral_value(rounding=ROUND_DOWN))

    # Concentration cap: reduce shares. Never widen the stop.
    max_value = equity_d * limits.max_position_pct
    if shares > 0 and shares * entry_d > max_value:
        shares = int((max_value / entry_d).to_integral_value(rounding=ROUND_DOWN))
        reasons.append(
            f"size reduced to {limits.max_position_pct:%} concentration cap "
            "(stop unchanged by design)"
        )

    if shares <= 0:
        reasons.append("risk budget too small for one share at this stop distance")

    position_value = (shares * entry_d).quantize(Decimal("0.01"))
    actual_risk = (shares * risk_per_share).quantize(Decimal("0.01"))
    position_pct = (position_value / equity_d) if equity_d > 0 else zero

    if open_positions >= limits.max_concurrent_positions:
        reasons.append(
            f"at max concurrent positions ({limits.max_concurrent_positions})"
        )
    if sector_positions >= limits.max_positions_per_sector:
        reasons.append(
            f"at max positions per sector ({limits.max_positions_per_sector})"
        )

    prospective_risk = _d(open_risk_pct) + (actual_risk / equity_d if equity_d > 0 else zero)
    if prospective_risk > limits.max_total_open_risk_pct:
        reasons.append(
            f"total open risk would reach {prospective_risk:.2%}, "
            f"above the {limits.max_total_open_risk_pct:.2%} cap"
        )

    r_multiple = None
    if target is not None:
        target_d = _d(target)
        if target_d <= entry_d:
            reasons.append("target must be above entry for a long position")
        else:
            r_multiple = ((target_d - entry_d) / risk_per_share).quantize(Decimal("0.01"))
            if min_r_multiple is not None and r_multiple < _d(min_r_multiple):
                reasons.append(
                    f"R:R of {r_multiple} is below the {_d(min_r_multiple)} minimum"
                )

    blocking = [
        r for r in reasons
        if "size reduced" not in r
    ]
    return PositionPlan(
        shares=shares,
        entry=entry_d,
        stop=stop_d,
        risk_per_share=risk_per_share,
        risk_dollars=actual_risk,
        position_value=position_value,
        position_pct_of_equity=position_pct,
        r_multiple_to_target=r_multiple,
        rejected=bool(blocking) or shares <= 0,
        reasons=reasons,
    )
