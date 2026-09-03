"""Filings-derived signals, computed point-in-time.

Round 1 and Round 2 both looked for edge in the price series of liquid US
equities on daily bars. That is the most examined dataset in finance, and
forty-one configurations returned nothing -- which is the result theory
predicts. If a simple daily-bar rule on liquid names worked it would have been
arbitraged long ago.

These signals look somewhere else. All three are balance-sheet facts rather
than price patterns, all three come from filings this project already ingests,
and all three carry published evidence:

  accruals            Sloan (1996). Earnings backed by cash persist; earnings
                      backed by accruals reverse. High accruals predict weaker
                      subsequent returns.
  asset_growth        Cooper, Gulen and Schill (2008). Firms expanding the
                      balance sheet fastest subsequently underperform.
  net_share_issuance  Firms issuing shares underperform; firms retiring them
                      outperform. Dilution is a transfer, and the market is
                      slow to price it.

They share a direction, which is worth stating rather than discovering later:
each is long the firm that is SHRINKING -- fewer accruals, slower asset
growth, fewer shares. Three views of one idea, not three independent bets. Any
combined test must expect them to correlate, and `diagnose redundancy` should
be run before treating them as separate evidence.

POINT-IN-TIME IS THE WHOLE DIFFICULTY. A fiscal period ends months before
anyone can read the numbers, and companies restate prior periods afterwards.
Both facts are look-ahead traps, and both are handled the same way: every
lookup filters on `filed`, never on `period_end`, and takes the latest version
filed on or before the evaluation date. The restated figure is deliberately
invisible until the restatement itself was public.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

# A fiscal year is not exactly 365 days and filings slip. This window decides
# what counts as "the same period one year earlier" when pairing observations.
YEAR_DAYS = 365
YEAR_TOLERANCE_DAYS = 100

# Below this, a denominator is noise rather than a scale factor.
MIN_DENOMINATOR = 1.0

REQUIRED_COLUMNS = ("concept", "period_end", "filed", "value")


@dataclass(frozen=True)
class Observation:
    """One concept's value for one fiscal period, as known at a point in time."""

    concept: str
    period_end: date
    filed: date
    value: float


def _validate(facts: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in facts.columns]
    if missing:
        raise ValueError(f"facts frame missing columns: {', '.join(missing)}")


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def as_reported(
    facts: pd.DataFrame, concept: str, as_of: date
) -> list[Observation]:
    """Every period of `concept` knowable on `as_of`, newest period first.

    For each fiscal period the LATEST filing dated on or before `as_of` wins,
    so a restatement becomes visible on the day it was filed and not one day
    sooner. Periods whose first filing came after `as_of` are absent entirely,
    which is the correct representation of not knowing yet.
    """
    _validate(facts)
    if facts.empty:
        return []

    subset = facts[facts["concept"] == concept]
    if subset.empty:
        return []

    rows: dict[date, Observation] = {}
    for record in subset.to_dict("records"):
        filed = _as_date(record["filed"])
        if filed > as_of:
            continue
        period_end = _as_date(record["period_end"])
        existing = rows.get(period_end)
        if existing is None or filed >= existing.filed:
            rows[period_end] = Observation(
                concept=concept,
                period_end=period_end,
                filed=filed,
                value=float(record["value"]),
            )

    return sorted(rows.values(), key=lambda o: o.period_end, reverse=True)


def latest(facts: pd.DataFrame, concept: str, as_of: date) -> Observation | None:
    """Most recent period of `concept` knowable on `as_of`."""
    found = as_reported(facts, concept, as_of)
    return found[0] if found else None


def year_earlier(
    observations: list[Observation], reference: Observation
) -> Observation | None:
    """The observation roughly one year before `reference`, if one exists.

    Matched on period_end spacing rather than fiscal-period labels, because
    labels are inconsistent across registrants and absent for many.
    """
    target = reference.period_end - timedelta(days=YEAR_DAYS)
    best: Observation | None = None
    best_gap = YEAR_TOLERANCE_DAYS + 1

    for candidate in observations:
        if candidate.period_end >= reference.period_end:
            continue
        gap = abs((candidate.period_end - target).days)
        if gap < best_gap:
            best, best_gap = candidate, gap

    return best if best_gap <= YEAR_TOLERANCE_DAYS else None


def _paired(
    facts: pd.DataFrame, concept: str, as_of: date
) -> tuple[Observation, Observation] | None:
    """Latest observation and its year-earlier counterpart, or None."""
    observations = as_reported(facts, concept, as_of)
    if not observations:
        return None
    current = observations[0]
    prior = year_earlier(observations, current)
    return (current, prior) if prior else None


def accruals(facts: pd.DataFrame, as_of: date) -> float | None:
    """(net income - operating cash flow) / average total assets.

    Sloan's ratio. Positive means reported earnings ran ahead of the cash that
    arrived, which historically reverses. Returns None when any input is
    missing rather than substituting a zero -- an absent filing is not a
    company with no accruals.
    """
    income = latest(facts, "net_income", as_of)
    cash_flow = latest(facts, "operating_cash_flow", as_of)
    if income is None or cash_flow is None:
        return None
    # Both must describe the same fiscal period, or the difference is
    # meaningless -- a full-year profit against a single quarter of cash.
    if income.period_end != cash_flow.period_end:
        return None

    assets_pair = _paired(facts, "assets", as_of)
    if assets_pair is None:
        return None
    current_assets, prior_assets = assets_pair

    average_assets = (current_assets.value + prior_assets.value) / 2.0
    if average_assets < MIN_DENOMINATOR:
        return None

    return (income.value - cash_flow.value) / average_assets


def asset_growth(facts: pd.DataFrame, as_of: date) -> float | None:
    """Year-over-year change in total assets, as a fraction of the prior year."""
    pair = _paired(facts, "assets", as_of)
    if pair is None:
        return None
    current, prior = pair
    if prior.value < MIN_DENOMINATOR:
        return None
    return (current.value - prior.value) / prior.value


def net_share_issuance(facts: pd.DataFrame, as_of: date) -> float | None:
    """Year-over-year change in shares outstanding, as a fraction.

    Positive is dilution, negative is a buyback. Splits are the trap here: a
    2-for-1 doubles the count without issuing anything economic. This project
    stores corporate actions separately, so a caller comparing across a split
    date must adjust the counts first -- the raw ratio will read as a 100%
    issuance otherwise.
    """
    pair = _paired(facts, "shares_outstanding", as_of)
    if pair is None:
        return None
    current, prior = pair
    if prior.value < MIN_DENOMINATOR:
        return None
    return (current.value - prior.value) / prior.value


def signal_frame(facts: pd.DataFrame, as_of: date) -> dict[str, float | None]:
    """All three signals for one symbol at one date.

    Missing values stay None. A screen that ranks on these must drop them
    rather than impute, because "did not file" and "filed a zero" are
    different companies.
    """
    return {
        "accruals": accruals(facts, as_of),
        "asset_growth": asset_growth(facts, as_of),
        "net_share_issuance": net_share_issuance(facts, as_of),
    }
