"""Can this account actually trade this stock properly?

A stock can be liquid, trending and cheap and still be untradeable at a given
account size, for reasons that have nothing to do with the company. Both
failure modes are arithmetic, and they pull in opposite directions.

TOO FEW SHARES. Position size is risk budget over stop distance. On a $900
stock with a $27 stop and a $100 budget, that is 3 shares. Rounding down to a
whole share throws away a third of the intended risk, and there is no way to
tune a position that granular -- you cannot take "3.6 shares".

THE CONCENTRATION CAP BINDING. A low-volatility stock has a tight stop, so the
same risk buys a large position, which the 25% cap then cuts. The cap is doing
its job, but the consequence is that the trade risks 0.5% when the rule said
1%. Not dangerous -- the opposite -- but the sizing rule is no longer doing
what it says, and a rule that quietly does something else is how a system stops
being understood.

Neither is a reason to fix the risk rules. They are a reason to trade
instruments where the rules work as written, which is a selection problem with
a free solution: trade something else.

Every threshold here scales with equity. A stock untradeable at $10,000 becomes
tradeable at $50,000 without anything else changing, so the verdicts are
recomputed rather than stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from .sizing import RiskLimits, _d

# Below this many shares, whole-share rounding distorts intended risk by more
# than a tenth, and position size can no longer be adjusted meaningfully.
MIN_SHARES_GOOD = 10
MIN_SHARES_MARGINAL = 5

# How close realised risk must come to intended risk. Below this the sizing
# rule is describing something other than what happens.
PRECISION_GOOD = 0.85
PRECISION_MARGINAL = 0.70


@dataclass(frozen=True)
class Tradeability:
    ticker: str
    price: Decimal
    stop_distance: Decimal
    shares: int
    position_value: Decimal
    pct_of_equity: float
    intended_risk_pct: float
    effective_risk_pct: float
    concentration_capped: bool
    verdict: str                       # "good" | "marginal" | "unusable"
    reasons: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """Realised risk as a share of intended risk. 1.0 means the sizing rule
        did exactly what it says."""
        if self.intended_risk_pct <= 0:
            return 0.0
        return self.effective_risk_pct / self.intended_risk_pct

    @property
    def is_tradeable(self) -> bool:
        return self.verdict != "unusable"

    def describe(self) -> str:
        return (
            f"{self.ticker}: {self.shares} shares, "
            f"{self.pct_of_equity:.0%} of equity, "
            f"risking {self.effective_risk_pct:.2%} of {self.intended_risk_pct:.2%} "
            f"intended ({self.verdict})"
        )


def assess(
    ticker: str,
    price: float | Decimal,
    atr: float | Decimal,
    *,
    equity: float | Decimal = 10_000,
    stop_atr: float = 2.0,
    limits: RiskLimits | None = None,
) -> Tradeability:
    """Whether this account can express a normal position in this stock."""
    limits = limits or RiskLimits()
    price_d, atr_d, equity_d = _d(price), _d(atr), _d(equity)
    intended = float(limits.risk_pct_per_trade)
    zero = Decimal("0")

    if price_d <= 0 or atr_d <= 0 or equity_d <= 0:
        return Tradeability(
            ticker, price_d, zero, 0, zero, 0.0, intended, 0.0, False,
            "unusable", ["price, ATR and equity must all be positive"],
        )

    stop_distance = (_d(stop_atr) * atr_d).quantize(Decimal("0.0001"))
    if stop_distance <= 0:
        # A positive ATR can still round to zero here. That means the symbol
        # has no measurable daily range -- repeated identical bars, which is
        # what a halted or delisted ticker looks like once it stops trading.
        # There is no stop to size against, so there is no position.
        return Tradeability(
            ticker, price_d, zero, 0, zero, 0.0, intended, 0.0, False,
            "unusable", ["ATR rounds to zero — no measurable daily range"],
        )
    budget = equity_d * limits.risk_pct_per_trade
    shares = int((budget / stop_distance).to_integral_value(rounding=ROUND_DOWN))

    reasons: list[str] = []
    capped = False
    max_value = equity_d * limits.max_position_pct
    if shares > 0 and shares * price_d > max_value:
        capped = True
        shares = int((max_value / price_d).to_integral_value(rounding=ROUND_DOWN))

    position_value = (shares * price_d).quantize(Decimal("0.01"))
    effective_risk = float((shares * stop_distance) / equity_d) if shares else 0.0
    pct_equity = float(position_value / equity_d)
    precision = effective_risk / intended if intended > 0 else 0.0

    if shares < MIN_SHARES_MARGINAL:
        reasons.append(
            f"only {shares} share(s) at this stop distance — whole-share "
            "rounding dominates the position"
        )
    elif shares < MIN_SHARES_GOOD:
        reasons.append(f"{shares} shares leaves little room to adjust size")

    if capped:
        reasons.append(
            f"the {limits.max_position_pct:.0%} concentration cap binds, so the "
            f"trade risks {effective_risk:.2%} rather than the intended "
            f"{intended:.2%}"
        )

    if shares < MIN_SHARES_MARGINAL or precision < PRECISION_MARGINAL:
        verdict = "unusable"
    elif shares < MIN_SHARES_GOOD or precision < PRECISION_GOOD:
        verdict = "marginal"
    else:
        verdict = "good"

    return Tradeability(
        ticker=ticker,
        price=price_d,
        stop_distance=stop_distance,
        shares=shares,
        position_value=position_value,
        pct_of_equity=pct_equity,
        intended_risk_pct=intended,
        effective_risk_pct=effective_risk,
        concentration_capped=capped,
        verdict=verdict,
        reasons=reasons,
    )


def max_workable_price(
    atr_pct: float,
    *,
    equity: float | Decimal = 10_000,
    stop_atr: float = 2.0,
    limits: RiskLimits | None = None,
    min_shares: int = MIN_SHARES_GOOD,
) -> float:
    """Highest price at which this account still gets ``min_shares``.

    Useful as a screen threshold rather than checking names one at a time:
    shares = budget / (stop_atr x atr% x price), so requiring a share count
    puts a ceiling on price for any given volatility.
    """
    limits = limits or RiskLimits()
    budget = float(_d(equity) * limits.risk_pct_per_trade)
    if atr_pct <= 0 or min_shares <= 0:
        return float("inf")
    return budget / (min_shares * stop_atr * atr_pct)


def min_workable_atr_pct(
    *, equity: float | Decimal = 10_000, stop_atr: float = 2.0,
    limits: RiskLimits | None = None,
) -> float:
    """Lowest ATR% at which the concentration cap does NOT bind.

    Below this, a tight stop buys a position larger than the cap allows, and
    realised risk falls below the intended figure. Independent of price --
    which is why it works as a universe filter.
    """
    limits = limits or RiskLimits()
    return float(limits.risk_pct_per_trade / (_d(stop_atr) * limits.max_position_pct))
