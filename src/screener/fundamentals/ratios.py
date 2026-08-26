"""Value and quality ratios, computed from point-in-time facts.

Each takes the facts that were public on a date plus the price that day, and
returns None when an input is missing. None propagates: a company that did not
report current assets is excluded from a net-net screen rather than ranked with
a zero.

Every ratio here is parameter-free. That is the point -- docs/04 §2 argues that
computational complexity is cheap and PARAMETRIC complexity is what overfits,
so a screen with nothing to tune is the cheapest possible thing to test and
there is nothing to adjust afterwards if results disappoint.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pit import Reported


def _value(facts: dict[str, Reported], concept: str) -> float | None:
    reported = facts.get(concept)
    return None if reported is None else reported.value


def book_value(facts: dict[str, Reported]) -> float | None:
    """Shareholders' equity. Falls back to assets minus liabilities."""
    equity = _value(facts, "equity")
    if equity is not None:
        return equity
    assets, liabilities = _value(facts, "assets"), _value(facts, "liabilities")
    if assets is None or liabilities is None:
        return None
    return assets - liabilities


def price_to_book(facts: dict[str, Reported], price: float) -> float | None:
    shares = _value(facts, "shares_outstanding")
    equity = book_value(facts)
    if not shares or equity is None or equity <= 0:
        return None
    return price / (equity / shares)


def net_current_asset_value(facts: dict[str, Reported]) -> float | None:
    """Graham's NCAV: current assets minus TOTAL liabilities.

    Total, not current. The conservatism is deliberate -- it asks what would be
    left for shareholders if the company liquidated its current assets at book
    and settled everything it owes.
    """
    current_assets = _value(facts, "assets_current")
    liabilities = _value(facts, "liabilities")
    if current_assets is None or liabilities is None:
        return None
    return current_assets - liabilities


def ncav_per_share(facts: dict[str, Reported]) -> float | None:
    shares = _value(facts, "shares_outstanding")
    ncav = net_current_asset_value(facts)
    if not shares or ncav is None:
        return None
    return ncav / shares


def net_cash(facts: dict[str, Reported]) -> float | None:
    """Cash minus total liabilities. A company below this is priced under the
    money in its own account, which is rare and usually distressed."""
    cash, liabilities = _value(facts, "cash"), _value(facts, "liabilities")
    if cash is None or liabilities is None:
        return None
    return cash - liabilities


def gross_profitability(facts: dict[str, Reported]) -> float | None:
    """Gross profit over total assets (Novy-Marx 2013).

    Gross profit rather than net income on purpose: it sits above the line
    where accounting discretion -- depreciation policy, write-offs, one-off
    charges -- does most of its work, so it is harder to manage.
    """
    assets = _value(facts, "assets")
    if not assets or assets <= 0:
        return None

    gross = _value(facts, "gross_profit")
    if gross is None:
        revenue, cost = _value(facts, "revenue"), _value(facts, "cost_of_revenue")
        if revenue is None or cost is None:
            return None
        gross = revenue - cost
    return gross / assets


def return_on_assets(facts: dict[str, Reported]) -> float | None:
    net_income, assets = _value(facts, "net_income"), _value(facts, "assets")
    if net_income is None or not assets or assets <= 0:
        return None
    return net_income / assets


def accrual_ratio(facts: dict[str, Reported]) -> float | None:
    """(Net income − operating cash flow) / assets.

    Positive means earnings exceed the cash actually collected. One of
    Piotroski's nine tests, and the intuition behind the accruals anomaly:
    profit you have not been paid for is lower quality profit.
    """
    net_income = _value(facts, "net_income")
    cash_flow = _value(facts, "operating_cash_flow")
    assets = _value(facts, "assets")
    if net_income is None or cash_flow is None or not assets or assets <= 0:
        return None
    return (net_income - cash_flow) / assets


def current_ratio(facts: dict[str, Reported]) -> float | None:
    current_assets = _value(facts, "assets_current")
    current_liabilities = _value(facts, "liabilities_current")
    if current_assets is None or not current_liabilities or current_liabilities <= 0:
        return None
    return current_assets / current_liabilities


def net_share_issuance(
    facts: dict[str, Reported], prior: dict[str, Reported]
) -> float | None:
    """Fractional change in shares outstanding. Negative means buybacks.

    Both sides must be point-in-time. Comparing today's share count against a
    figure that was restated later is the same look-ahead in a subtler form.
    """
    now, before = _value(facts, "shares_outstanding"), _value(prior, "shares_outstanding")
    if not now or not before or before <= 0:
        return None
    return (now - before) / before


@dataclass(frozen=True)
class ValueSnapshot:
    """Everything the value screens need for one symbol on one date."""

    ticker: str
    price: float
    price_to_book: float | None
    ncav_per_share: float | None
    net_cash_per_share: float | None
    gross_profitability: float | None
    return_on_assets: float | None
    accrual_ratio: float | None
    current_ratio: float | None
    reported_as_of: str | None      # period_end of the newest fact used
    lag_days: int | None            # how stale that fact was

    @property
    def below_ncav(self) -> bool:
        """Graham's threshold: price below two-thirds of net current asset value."""
        return self.ncav_per_share is not None and self.price < self.ncav_per_share * (2 / 3)

    @property
    def below_net_cash(self) -> bool:
        return self.net_cash_per_share is not None and self.price < self.net_cash_per_share


def snapshot(ticker: str, price: float, facts: dict[str, Reported]) -> ValueSnapshot:
    shares = _value(facts, "shares_outstanding")
    cash_value = net_cash(facts)
    newest = max(facts.values(), key=lambda r: r.period_end, default=None)
    return ValueSnapshot(
        ticker=ticker,
        price=price,
        price_to_book=price_to_book(facts, price),
        ncav_per_share=ncav_per_share(facts),
        net_cash_per_share=(cash_value / shares) if shares and cash_value is not None else None,
        gross_profitability=gross_profitability(facts),
        return_on_assets=return_on_assets(facts),
        accrual_ratio=accrual_ratio(facts),
        current_ratio=current_ratio(facts),
        reported_as_of=str(newest.period_end) if newest else None,
        lag_days=newest.lag_days if newest else None,
    )


CONCEPTS = [
    "assets", "assets_current", "liabilities", "liabilities_current", "equity",
    "cash", "revenue", "cost_of_revenue", "gross_profit", "net_income",
    "operating_cash_flow", "long_term_debt", "shares_outstanding",
]
