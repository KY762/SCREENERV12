"""Independent reference source, used ONLY to verify ingested data.

This is deliberately not a PriceProvider and must never become the platform's
data source. Its single job is to answer one question: do the bars we stored
match a source that has no shared code, no shared vendor, and no shared bugs
with our ingestion path?

Stooq is used because it needs no key, no account, and no terms acceptance for
a one-off comparison. Its reliability is unproven and irrelevant here -- a
disagreement is a signal to investigate, never a reason to overwrite our data.

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
from datetime import date

import httpx

log = logging.getLogger(__name__)

STOOQ_URL = "https://stooq.com/q/d/l/"


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
        response = self._client.get(STOOQ_URL, params=params)
        response.raise_for_status()
        return parse_stooq_csv(response.text)

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
