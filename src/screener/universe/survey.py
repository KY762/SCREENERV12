"""Which symbols were ever worth trading, decided before any of them is stored.

The old universe was 307 of today's large caps, then S&P 500 membership. Both
are indexes someone else maintains, and the second is the only one with a
point-in-time membership file. For mid and small caps no such file exists, so
the universe has to be constructed from the market itself: every US common
stock that, on a given date, actually traded enough to be tradeable.

Doing that naively means storing every one of ~22,000 NYSE and NASDAQ tickers
including delisted ones, which is roughly 40 million bars and hours of writes,
most of it names that never traded $100,000 in a day. Instead this samples the
WHOLE market on a handful of dates -- one bulk call per date, ~40,000 symbols
each -- and keeps only the tickers that cleared the bar on at least one of
them.

WHY THIS IS NOT SURVIVORSHIP BIAS, AND WHERE IT STILL IS. The symbol list comes
from EODHD's active AND delisted rosters, so a company that failed in 2012 is a
candidate on exactly the same terms as one still trading -- which is the whole
point, and the opposite of screening today's listings. What it cannot fix is a
name that was liquid only between two sample dates; a quarterly sweep can miss
a stock that listed and delisted inside one quarter. That is a real gap, it
biases toward longer-lived names, and it is the price of not storing forty
million bars.

The qualifying bar is deliberately loose. This decides what gets STORED, not
what gets traded: the per-date universe filter runs later, on real bars, and
is free to be stricter. A symbol excluded here can never be reconsidered
without another survey, so it errs wide.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

log = logging.getLogger(__name__)

#: Listing venues worth storing. PINK, OTCQB, OTCGREY and the rest are excluded:
#: spreads there make the cost model the entire result, and a $10,000 account
#: cannot reliably exit a position it can enter.
EXCHANGES = frozenset({"NYSE", "NASDAQ", "AMEX", "NYSE ARCA", "NYSE MKT", "BATS"})

#: Common stock only. Funds, ETFs, preferred and units are not what any
#: hypothesis here is about, and including them would put the same company in
#: the cross-section several times.
SECURITY_TYPE = "Common Stock"

#: Ever-cleared thresholds. A symbol qualifies on ANY sampled date.
MIN_DOLLAR_VOLUME = 2_000_000.0
MIN_PRICE = 5.0


@dataclass
class SurveyResult:
    dates_sampled: int = 0
    rows_seen: int = 0
    eligible_symbols: set[str] = field(default_factory=set)
    #: Best dollar volume each qualifying symbol ever showed, for reporting.
    best_dollar_volume: dict[str, float] = field(default_factory=dict)
    first_seen: dict[str, date] = field(default_factory=dict)
    last_seen: dict[str, date] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"{len(self.eligible_symbols):,} symbol(s) cleared "
            f"${MIN_DOLLAR_VOLUME:,.0f}/day and ${MIN_PRICE:.0f} on at least one "
            f"of {self.dates_sampled} sampled date(s) "
            f"({self.rows_seen:,} rows examined)"
        )


def sample_dates(start: date, end: date, every_days: int) -> list[date]:
    """Sample dates across the window, skipping weekends.

    A date that lands on a holiday returns an empty or stale bulk response;
    the caller reports the row count so a run of empty dates is visible rather
    than silently narrowing the universe.
    """
    out: list[date] = []
    day = start
    while day <= end:
        shifted = day
        while shifted.weekday() >= 5:          # Sat/Sun -> next Monday
            shifted += timedelta(days=1)
        if shifted <= end and (not out or shifted != out[-1]):
            out.append(shifted)
        day += timedelta(days=every_days)
    return out


def eligible(row: dict, allowed: dict[str, str]) -> tuple[str, float] | None:
    """One bulk row, judged. Returns (ticker, dollar volume) or None.

    `allowed` maps ticker -> exchange for symbols that passed the type and
    venue screen, so this stays a dict lookup rather than a second API call.
    """
    code = str(row.get("code") or "").strip().upper()
    if not code or code not in allowed:
        return None
    try:
        close = float(row.get("close") or 0.0)
        volume = float(row.get("volume") or 0.0)
    except (TypeError, ValueError):
        return None
    if close < MIN_PRICE or volume <= 0:
        return None
    dollar_volume = close * volume
    if dollar_volume < MIN_DOLLAR_VOLUME:
        return None
    return code, dollar_volume


def survey(
    provider,
    *,
    start: date,
    end: date,
    every_days: int = 91,
    progress=None,
) -> SurveyResult:
    """Sweep the market on sampled dates and collect everything tradeable.

    One bulk call per date. A failure on one date is logged and the sweep
    continues -- losing one quarter narrows the universe slightly, and aborting
    loses the whole survey.
    """
    from ..providers.base import ProviderError

    refs = list(provider.list_symbols("US", delisted=False))
    refs += list(provider.list_symbols("US", delisted=True))
    allowed = {
        r.symbol.strip().upper(): (r.exchange or "")
        for r in refs
        if (r.type or "") == SECURITY_TYPE and (r.exchange or "") in EXCHANGES
    }
    log.info("%d symbol(s) pass the type and venue screen", len(allowed))

    result = SurveyResult()
    for day in sample_dates(start, end, every_days):
        if progress is not None:
            progress(day, result)
        try:
            rows = provider.get_bulk_day(day)
        except ProviderError as exc:
            log.warning("%s: %s", day, exc)
            continue
        if not rows:
            log.warning("%s: no rows (holiday?)", day)
            continue
        result.dates_sampled += 1
        result.rows_seen += len(rows)
        for row in rows:
            hit = eligible(row, allowed)
            if hit is None:
                continue
            ticker, dollar_volume = hit
            result.eligible_symbols.add(ticker)
            if dollar_volume > result.best_dollar_volume.get(ticker, 0.0):
                result.best_dollar_volume[ticker] = dollar_volume
            result.first_seen.setdefault(ticker, day)
            result.last_seen[ticker] = day
    return result
