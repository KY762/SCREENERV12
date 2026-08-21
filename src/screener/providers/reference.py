"""Independent reference source, used ONLY to verify ingested data.

This is deliberately not a PriceProvider and must never become the platform's
data source. Its single job is to answer one question: do the bars we stored
match a source that has no shared code, no shared vendor, and no shared bugs
with our ingestion path?

Two sources are implemented, both keyless, and the verifier tries them in turn.
Neither is trusted: a disagreement is a signal to investigate, never a reason to
overwrite our data. What matters is only that they share no code and no vendor
with the ingestion path, so a bug in ours cannot also be a bug in theirs.

Free sources block automated requests without warning -- Stooq answers HTTP 200
with an HTML anti-bot page rather than an error. Having a second source is not
redundancy for its own sake; it is what keeps an unreachable site from being
indistinguishable from a verified one.

Adjustment caveat
-----------------
Reference sources vary in whether they serve split-adjusted history. That is why
verification defaults to the MOST RECENT bars: over a short recent window a split
is very unlikely, so adjustment policy cannot explain a mismatch. Comparing bars
from years ago would produce spurious failures on every symbol that ever split.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

import httpx

log = logging.getLogger(__name__)

# Stooq serves the same CSV from two hosts. They fail independently -- one
# returning 404 or a rate-limit page while the other answers is common -- so
# both are tried before the reference is declared unavailable.
STOOQ_HOSTS = ("https://stooq.com/q/d/l/", "https://stooq.pl/q/d/l/")

# Stooq refuses or 404s requests without a browser-like User-Agent.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SCREENERV12 data verification; "
        "one request per symbol)"
    ),
    "Accept": "text/csv,text/plain,*/*",
}


class ReferenceUnavailable(RuntimeError):
    """The reference could not be read. NOT a verification failure.

    The distinction is load-bearing: 'the prices disagree' and 'we could not
    ask' are different findings, and collapsing them into one lets an
    unanswered question be recorded as a passed check.
    """


@dataclass(frozen=True)
class ReferenceBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class StooqReference:
    """Fetches daily bars from Stooq as CSV."""

    name = "stooq"

    def __init__(self, client: httpx.Client | None = None, timeout: float = 30.0):
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)

    def get_bars(self, ticker: str, start: date, end: date) -> list[ReferenceBar]:
        params = {
            "s": f"{ticker.lower()}.us",
            "d1": start.strftime("%Y%m%d"),
            "d2": end.strftime("%Y%m%d"),
            "i": "d",
        }
        problems: list[str] = []
        for host in STOOQ_HOSTS:
            try:
                response = self._client.get(host, params=params, headers=HEADERS)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                problems.append(f"{host}: {exc}")
                continue

            text = response.text.strip()
            if not text.lower().startswith("date,"):
                # Rate-limit notices and error pages arrive with HTTP 200 and a
                # body that is not CSV. Parsing that would yield zero bars and
                # read as a clean comparison of nothing.
                first_line = text.splitlines()[0][:120] if text else "(empty body)"
                problems.append(f"{host}: not CSV -- {first_line!r}")
                continue

            bars = parse_stooq_csv(text)
            if not bars:
                problems.append(f"{host}: CSV contained no usable rows")
                continue
            return bars

        raise ReferenceUnavailable(
            f"{ticker}: no reference data ({'; '.join(problems)})"
        )

    def close(self) -> None:
        self._client.close()


def parse_stooq_csv(text: str) -> list[ReferenceBar]:
    """Parse Stooq's CSV. Pure, so the format is pinned by tests without a network."""
    rows: list[ReferenceBar] = []
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames or "Date" not in reader.fieldnames:
        return rows
    for row in reader:
        try:
            rows.append(
                ReferenceBar(
                    trade_date=date.fromisoformat(row["Date"]),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume") or 0),
                )
            )
        except (ValueError, KeyError, TypeError) as exc:
            log.debug("skipping unparseable reference row %r: %s", row, exc)
    return sorted(rows, key=lambda b: b.trade_date)


# --------------------------------------------------------------------------
# Yahoo Finance -- second, independent reference
# --------------------------------------------------------------------------

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def parse_yahoo_chart(payload: dict) -> list[ReferenceBar]:
    """Parse Yahoo's chart JSON. Pure, so the shape is pinned without a network.

    Bars with a null field are dropped rather than defaulted. Yahoo emits nulls
    for a session still in progress, and a partial bar compared against a
    completed one would fail the gate for a reason that has nothing to do with
    our data.
    """
    chart = (payload or {}).get("chart") or {}
    results = chart.get("result") or []
    if not results:
        return []

    result = results[0]
    stamps = result.get("timestamp") or []
    quotes = (result.get("indicators") or {}).get("quote") or [{}]
    quote = quotes[0] if quotes else {}

    fields = ("open", "high", "low", "close", "volume")
    series = {f: quote.get(f) or [] for f in fields}

    bars: list[ReferenceBar] = []
    for i, stamp in enumerate(stamps):
        values = {}
        for field in fields:
            column = series[field]
            value = column[i] if i < len(column) else None
            if value is None:
                break
            values[field] = float(value)
        else:
            # US sessions open at 13:30 or 14:30 UTC, so the UTC date and the
            # trading date always agree. This would need care for other venues.
            bars.append(
                ReferenceBar(
                    trade_date=datetime.fromtimestamp(stamp, tz=UTC).date(),
                    **values,
                )
            )
    return sorted(bars, key=lambda b: b.trade_date)


class YahooReference:
    """Daily bars from Yahoo's chart endpoint. No key, no account.

    Returns UNADJUSTED OHLC (the ``quote`` block), matching what price_daily
    stores. Yahoo's adjusted series lives separately in ``adjclose`` and is
    deliberately ignored.
    """

    name = "yahoo"

    def __init__(self, client: httpx.Client | None = None, timeout: float = 30.0):
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)

    def get_bars(self, ticker: str, start: date, end: date) -> list[ReferenceBar]:
        params = {
            "period1": int(datetime(start.year, start.month, start.day,
                                    tzinfo=UTC).timestamp()),
            # One day past the end, since the range is half-open at the top.
            "period2": int(datetime(end.year, end.month, end.day,
                                    tzinfo=UTC).timestamp()) + 86_400,
            "interval": "1d",
            "events": "div,splits",
        }
        url = YAHOO_URL.format(ticker=ticker.upper())
        try:
            response = self._client.get(url, params=params, headers=HEADERS)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ReferenceUnavailable(f"{ticker}: yahoo unreachable ({exc})") from exc

        error = ((payload or {}).get("chart") or {}).get("error")
        if error:
            raise ReferenceUnavailable(f"{ticker}: yahoo returned an error ({error})")

        bars = parse_yahoo_chart(payload)
        if not bars:
            raise ReferenceUnavailable(f"{ticker}: yahoo returned no usable bars")
        return bars

    def close(self) -> None:
        self._client.close()


# --------------------------------------------------------------------------
# Trying several sources
# --------------------------------------------------------------------------

class Reference(Protocol):
    name: str

    def get_bars(self, ticker: str, start: date, end: date) -> list[ReferenceBar]: ...

    def close(self) -> None: ...


class ChainedReference:
    """Tries each source in order and reports which one answered.

    Naming the source that answered matters: 'verified against yahoo' and
    'verified against stooq' are different statements, and a reader of the
    output should not have to guess which was made.
    """

    def __init__(self, sources: list[Reference]):
        if not sources:
            raise ValueError("a chained reference needs at least one source")
        self.sources = sources
        self.name = "+".join(s.name for s in sources)
        self.last_source: str | None = None

    def get_bars(self, ticker: str, start: date, end: date) -> list[ReferenceBar]:
        problems: list[str] = []
        for source in self.sources:
            try:
                bars = source.get_bars(ticker, start, end)
            except (ReferenceUnavailable, httpx.HTTPError) as exc:
                problems.append(f"{source.name}: {exc}")
                continue
            if bars:
                self.last_source = source.name
                return bars
            problems.append(f"{source.name}: no bars returned")
        self.last_source = None
        raise ReferenceUnavailable("; ".join(problems))

    def close(self) -> None:
        for source in self.sources:
            source.close()


REFERENCES: dict[str, type] = {
    "yahoo": YahooReference,
    "stooq": StooqReference,
}


def build_reference(name: str = "auto") -> Reference:
    """Build a reference by name. ``auto`` chains every source in preference
    order, which is what the Phase 1 gate uses."""
    key = name.strip().lower()
    if key == "auto":
        return ChainedReference([YahooReference(), StooqReference()])
    if key not in REFERENCES:
        raise ValueError(
            f"unknown reference {name!r}; expected auto, {' or '.join(REFERENCES)}"
        )
    return REFERENCES[key]()
