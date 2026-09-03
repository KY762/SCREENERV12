"""Polygon adapter. The reason it exists is delisted coverage.

`screener universe coverage` measured the problem on 2026-08-26: acquisitions
6/6 present, failures 0/6. TWTR, ATVI, CERN, XLNX, MRO and VMW all survive in
the data with full history to their delisting date. FRC, BBBY, YELL and RAD
return nothing at all, and SIVB and SBNY return bars dated today despite both
banks failing in March 2023 -- a reused ticker or a stale series being served
as current, which is worse than absence because it is wrong rather than empty.

That asymmetry is not random missingness. An acquisition ends at a premium and
a failure ends near zero, so the data retains every good ending and loses every
bad one. Every backtested return computed on it is overstated by an unknown
amount, and value screens are the most exposed because they select distressed
companies -- exactly the missing population.

Two capabilities here address it, and the second matters more than the first:

  get_daily_bars      serves bars for tickers that have since delisted, so a
                      known-dead symbol returns its real history.
  list_delisted       enumerates what delisted in a window. This is the part
                      free feeds cannot do at all. Fixing survivorship needs
                      the names that USED to be in the universe, and those
                      cannot be recovered by querying symbols you already know
                      -- you do not know what you are missing.

Prices are requested with ``adjusted=false``. The raw-storage policy is
non-negotiable 2: storing pre-adjusted prices makes history mutate at every
future split.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx
import pandas as pd

from ..config import Settings, get_settings
from .base import BarRequest, CorporateAction, ProviderError

log = logging.getLogger(__name__)

# Polygon timestamps are epoch milliseconds marking the start of the aggregate
# window, which for daily bars is midnight US/Eastern. Converting through UTC
# happens to agree for daily data, but stating the intent avoids an off-by-one
# the first time anyone reaches for intraday.
_MS_PER_SECOND = 1000

# Paid tiers are generous; this is polite rather than required, and keeps a
# backfill from tripping a burst limit.
REQUEST_INTERVAL = 0.05

MAX_LIMIT = 50_000


@dataclass(frozen=True)
class TickerStatus:
    """Whether a symbol is still listed, and when it stopped if not.

    `delisted_on` is None for an active ticker AND for one whose delisting date
    the provider does not carry. Those are different facts and the caller must
    not treat an absent date as evidence of continued listing.
    """

    ticker: str
    active: bool
    delisted_on: date | None
    name: str | None = None


class PolygonProvider:
    """Daily bars, corporate actions and listing status."""

    name = "polygon"

    def __init__(
        self, settings: Settings | None = None, client: httpx.Client | None = None
    ):
        self._settings = settings or get_settings()
        if not self._settings.polygon_api_key:
            raise ProviderError(
                "POLYGON_API_KEY is not configured. Polygon is the documented fix "
                "for delisted coverage; see providers/polygon.py."
            )
        self._key = self._settings.polygon_api_key.get_secret_value()
        self._client = client or httpx.Client(
            base_url=self._settings.polygon_base_url,
            timeout=self._settings.request_timeout_seconds,
            headers={"Authorization": f"Bearer {self._key}"},
        )

    # -- transport ---------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        """One request with bounded retries.

        429 and 5xx are transient and retried with backoff. 401/403 are
        configuration errors and raised immediately -- retrying a bad key just
        wastes time and hides the real problem.
        """
        last_error: str | None = None

        for attempt in range(self._settings.max_retries):
            delay = 2.0 ** attempt
            try:
                response = self._client.get(path, params=params or {})
            except httpx.HTTPError as exc:
                last_error = str(exc)
                log.warning(
                    "polygon network error on %s, retry in %.1fs: %s", path, delay, exc
                )
                time.sleep(delay)
                continue

            if response.status_code in (401, 403):
                raise ProviderError(
                    f"Polygon rejected the API key ({response.status_code}). "
                    "Check POLYGON_API_KEY and the subscription tier."
                )
            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
                log.warning(
                    "polygon transient %s on %s, retry %d/%d in %.1fs",
                    response.status_code, path, attempt + 1,
                    self._settings.max_retries, delay,
                )
                time.sleep(delay)
                continue
            if response.status_code == 404:
                return {}
            if response.status_code >= 400:
                raise ProviderError(
                    f"Polygon returned {response.status_code} for {path}: "
                    f"{response.text[:200]}"
                )

            try:
                return response.json()
            except ValueError as exc:
                raise ProviderError(f"Polygon returned non-JSON for {path}") from exc

        raise ProviderError(f"Polygon request failed after retries: {last_error}")

    def _paged(self, path: str, params: dict) -> list[dict]:
        """Follow next_url until exhausted.

        Stopping at the first page silently truncates history, which reads as a
        symbol that delisted early rather than one that was paginated.
        """
        results: list[dict] = []
        payload = self._get(path, params)

        while True:
            results.extend(payload.get("results") or [])
            next_url = payload.get("next_url")
            if not next_url:
                return results
            time.sleep(REQUEST_INTERVAL)
            # next_url is absolute and already carries the cursor; the auth
            # header travels with it on the same client.
            payload = self._get(next_url)

    # -- prices ------------------------------------------------------------

    def get_daily_bars(self, request: BarRequest) -> pd.DataFrame:
        """Raw daily OHLCV indexed by (symbol, date).

        A delisted ticker returns its real history up to the delisting rather
        than an empty frame, which is the entire reason for this adapter.
        """
        if request.adjustment != "raw":
            raise ProviderError(
                f"PolygonProvider stores raw bars only; got {request.adjustment!r}. "
                "Adjusted series are derived on demand from corporate_actions."
            )

        frames: list[pd.DataFrame] = []
        for symbol in request.symbols:
            rows = self._fetch_symbol(symbol, request.start, request.end)
            if rows:
                frames.append(_rows_to_frame(symbol, rows))
            time.sleep(REQUEST_INTERVAL)

        if not frames:
            return _empty_bars()
        return pd.concat(frames).sort_index()

    def _fetch_symbol(self, symbol: str, start: date, end: date) -> list[dict]:
        upper = symbol.strip().upper()
        return self._paged(
            f"/v2/aggs/ticker/{upper}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            {"adjusted": "false", "sort": "asc", "limit": MAX_LIMIT},
        )

    def get_corporate_actions(
        self, symbols: tuple[str, ...], start: date, end: date
    ) -> list[CorporateAction]:
        actions: list[CorporateAction] = []

        for symbol in symbols:
            upper = symbol.strip().upper()

            for row in self._paged("/v3/reference/splits", {
                "ticker": upper,
                "execution_date.gte": start.isoformat(),
                "execution_date.lte": end.isoformat(),
                "limit": 1000,
            }):
                parsed = _parse_split(upper, row)
                if parsed:
                    actions.append(parsed)
            time.sleep(REQUEST_INTERVAL)

            for row in self._paged("/v3/reference/dividends", {
                "ticker": upper,
                "ex_dividend_date.gte": start.isoformat(),
                "ex_dividend_date.lte": end.isoformat(),
                "limit": 1000,
            }):
                parsed = _parse_dividend(upper, row)
                if parsed:
                    actions.append(parsed)
            time.sleep(REQUEST_INTERVAL)

        return actions

    # -- listing status ----------------------------------------------------

    def get_ticker_status(self, symbol: str) -> TickerStatus | None:
        """Whether a symbol is listed, and when it stopped. None if unknown."""
        upper = symbol.strip().upper()
        payload = self._get(f"/v3/reference/tickers/{upper}")
        result = payload.get("results")
        if not result:
            return None
        return _parse_status(upper, result)

    def list_delisted(
        self, start: date, end: date, *, market: str = "stocks"
    ) -> list[TickerStatus]:
        """Every ticker that stopped trading between `start` and `end`.

        The survivorship fix proper. A point-in-time universe rebuilt without
        these is a universe of survivors no matter how carefully the membership
        dates are stored, because the failed companies were never candidates in
        the first place. Free feeds cannot answer this question at all.
        """
        rows = self._paged("/v3/reference/tickers", {
            "market": market,
            "active": "false",
            "delisted_utc.gte": start.isoformat(),
            "delisted_utc.lte": end.isoformat(),
            "limit": 1000,
        })

        found: list[TickerStatus] = []
        for row in rows:
            ticker = (row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            found.append(_parse_status(ticker, row))
        return sorted(found, key=lambda s: (s.delisted_on or date.min, s.ticker))

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PolygonProvider:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


# ---------------------------------------------------------------------------
# parsing -- module level so it is testable without a client or a key
# ---------------------------------------------------------------------------


def _empty_bars() -> pd.DataFrame:
    index = pd.MultiIndex.from_arrays(
        [pd.Index([], dtype="object"), pd.DatetimeIndex([])],
        names=["symbol", "date"],
    )
    return pd.DataFrame(
        {c: pd.Series(dtype="float64") for c in ("open", "high", "low", "close", "volume")},
        index=index,
    )


def _bar_date(milliseconds: int) -> date:
    """Epoch ms to calendar date.

    Polygon marks a daily aggregate at midnight US/Eastern. Naive UTC
    conversion agrees for daily bars, but the intent is the trading date.
    """
    return datetime.fromtimestamp(
        milliseconds / _MS_PER_SECOND, tz=UTC
    ).date()


def _rows_to_frame(symbol: str, rows: list[dict]) -> pd.DataFrame:
    records = []
    for row in rows:
        timestamp = row.get("t")
        if timestamp is None:
            continue
        records.append({
            "symbol": symbol.strip().upper(),
            "date": pd.Timestamp(_bar_date(int(timestamp))),
            "open": float(row["o"]),
            "high": float(row["h"]),
            "low": float(row["l"]),
            "close": float(row["c"]),
            "volume": float(row.get("v") or 0.0),
        })

    if not records:
        return _empty_bars()

    frame = pd.DataFrame.from_records(records)
    return frame.set_index(["symbol", "date"]).sort_index()


def _parse_split(symbol: str, row: dict) -> CorporateAction | None:
    """Polygon reports split_from and split_to; the ratio is to/from.

    A 2-for-1 is split_to=2, split_from=1, ratio 2.0. Inverting this silently
    halves every pre-split price instead of doubling it.
    """
    execution = row.get("execution_date")
    to_shares = row.get("split_to")
    from_shares = row.get("split_from")
    if not execution or not to_shares or not from_shares:
        return None
    try:
        ratio = float(to_shares) / float(from_shares)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return CorporateAction(
        symbol=symbol,
        ex_date=date.fromisoformat(execution),
        action_type="split",
        ratio=ratio,
    )


def _parse_dividend(symbol: str, row: dict) -> CorporateAction | None:
    ex_date = row.get("ex_dividend_date")
    amount = row.get("cash_amount")
    if not ex_date or amount is None:
        return None
    try:
        cash = float(amount)
    except (TypeError, ValueError):
        return None
    return CorporateAction(
        symbol=symbol,
        ex_date=date.fromisoformat(ex_date),
        action_type="dividend",
        amount=cash,
    )


def _parse_status(ticker: str, row: dict) -> TickerStatus:
    """Listing status. An absent delisted_utc is not evidence of being listed."""
    delisted_raw = row.get("delisted_utc")
    delisted_on: date | None = None
    if delisted_raw:
        try:
            delisted_on = datetime.fromisoformat(
                str(delisted_raw).replace("Z", "+00:00")
            ).date()
        except ValueError:
            delisted_on = None

    return TickerStatus(
        ticker=ticker,
        active=bool(row.get("active", False)),
        delisted_on=delisted_on,
        name=row.get("name"),
    )
