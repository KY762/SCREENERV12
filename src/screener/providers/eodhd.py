"""EODHD adapter. Like the Polygon one, it exists for delisted coverage.

Chosen by the operator on 2026-09-19 after the Polygon plan on record turned
out not to reach the data it was meant to fix. Polygon (now Massive) prices
history by depth -- $29 for 5 years, $79 for 10, $199 for 20+ -- and this
project's development split starts in 2010. The $29 plan reaches about 2021:
neither development (2010-2015) nor validation (2016-2019). EODHD's
"EOD Historical Data - All World" is $19.99/month and carries US tickers
mostly from 2000, delisted ones included, which covers every split.

The plan is a one-month purchase: pull everything, store it, cancel. What is
stored is raw prices, per non-negotiable 2 -- `adjusted_close` arrives as its
own column and is deliberately not written into `price_daily`.

Two endpoints matter, and the second is the one free feeds cannot do:

    get_daily_bars   bars for a ticker that has since delisted, so a known
                     dead symbol returns its real history to its last day.
    list_delisted    what is no longer listed. Fixing survivorship needs the
                     names that USED to be in the universe; querying symbols
                     already known cannot recover them, because the missing
                     ones are exactly what is not known.

Coverage is a claim until measured. `screener universe coverage` is the check,
and it is worth running on the six known-dead names (FRC, BBBY, YELL, RAD,
SIVB, SBNY) before relying on anything here.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime

import httpx
import pandas as pd

from ..config import Settings, get_settings
from .base import BarRequest, ProviderError

log = logging.getLogger(__name__)

# EODHD's published limit on the All World plan is 1,000 calls/minute. This is
# far below it: the constraint is the daily allowance, not the rate.
REQUEST_INTERVAL = 0.05

BARS_PATH = "/api/eod/{symbol}"
SYMBOLS_PATH = "/api/exchange-symbol-list/{exchange}"


@dataclass(frozen=True)
class DelistedTicker:
    """A symbol EODHD no longer lists. `name` is often all that survives."""

    symbol: str
    name: str | None
    exchange: str | None
    type: str | None


class EodhdProvider:
    """Daily bars and delisted symbols. Read-only."""

    name = "eodhd"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        key = self.settings.eodhd_api_key
        # An empty EODHD_API_KEY= line in .env parses to SecretStr(""), which
        # is not None. Accepting it sends an empty token and fails later as a
        # 401, which reads like a wrong key rather than a missing one.
        if key is None or not key.get_secret_value().strip():
            raise ProviderError(
                "EODHD_API_KEY is not set. The 'EOD Historical Data - All World' "
                "plan ($19.99/month) is what carries delisted US history back to "
                "2000; without a key this provider cannot be used."
            )
        self._token = key.get_secret_value()
        self._base = self.settings.eodhd_base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=self.settings.request_timeout_seconds)
        self._last_request = 0.0

    # -- http ---------------------------------------------------------------

    def _get(self, path: str, params: dict) -> list[dict]:
        elapsed = time.monotonic() - self._last_request
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        url = f"{self._base}{path}"
        try:
            response = self._client.get(
                url, params={**params, "api_token": self._token, "fmt": "json"}
            )
            self._last_request = time.monotonic()
            if response.status_code == 401:
                raise ProviderError("EODHD rejected the API key (401).")
            if response.status_code == 402:
                raise ProviderError(
                    "EODHD says this data is outside the plan (402). The All World "
                    "plan is the one with delisted US history."
                )
            if response.status_code == 429:
                # Raise rather than back off: a silent wait turns a quota
                # problem into a run that looks slow instead of one that
                # stopped. Ingestion is idempotent, so re-running resumes.
                raise ProviderError("EODHD daily request quota exhausted (429).")
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"EODHD rejected the request ({exc.response.status_code})"
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"EODHD unreachable: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"EODHD returned unparseable JSON: {exc}") from exc

        if isinstance(payload, dict):      # errors arrive as an object
            raise ProviderError(f"EODHD returned an error: {payload}")
        return payload

    # -- prices --------------------------------------------------------------

    def get_daily_bars(self, request: BarRequest) -> pd.DataFrame:
        """Raw daily bars for each symbol, indexed by (symbol, date).

        `adjustment` is accepted for the Protocol's sake and must be "raw":
        EODHD serves raw OHLC with `adjusted_close` alongside, and storing the
        adjusted series is what makes history mutate at the next split.
        """
        if request.adjustment != "raw":
            raise ProviderError(
                f"EODHD adapter stores raw prices only, got {request.adjustment!r}"
            )
        frames = [
            _rows_to_frame(symbol, self._fetch_symbol(symbol, request.start, request.end))
            for symbol in request.symbols
        ]
        frames = [f for f in frames if not f.empty]
        return pd.concat(frames) if frames else _empty_bars()

    def _fetch_symbol(self, symbol: str, start: date, end: date) -> list[dict]:
        return self._get(
            BARS_PATH.format(symbol=_us(symbol)),
            {"from": start.isoformat(), "to": end.isoformat(), "period": "d", "order": "a"},
        )

    # -- what is missing -----------------------------------------------------

    def list_delisted(self, exchange: str = "US") -> list[DelistedTicker]:
        """Every symbol EODHD marks as no longer listed on the exchange.

        The point of the subscription. A backtest universe built from symbols
        that still trade silently drops the companies that failed, and their
        endings are the bad ones.
        """
        rows = self._get(SYMBOLS_PATH.format(exchange=exchange), {"delisted": "1"})
        out = []
        for row in rows:
            code = str(row.get("Code") or "").strip().upper()
            if not code:
                continue
            out.append(DelistedTicker(
                symbol=code,
                name=(row.get("Name") or None),
                exchange=(row.get("Exchange") or None),
                type=(row.get("Type") or None),
            ))
        return out

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EodhdProvider:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


# -- parsing (pure, so the format is pinned without a network) ---------------

def _us(symbol: str) -> str:
    """EODHD addresses US tickers as SYMBOL.US."""
    symbol = symbol.strip().upper()
    return symbol if "." in symbol else f"{symbol}.US"


def _empty_bars() -> pd.DataFrame:
    index = pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"])
    return pd.DataFrame(
        {c: pd.Series(dtype="float64") for c in ("open", "high", "low", "close", "volume")},
        index=index,
    )


def _rows_to_frame(symbol: str, rows: list[dict]) -> pd.DataFrame:
    """Rows to a raw-price frame. `adjusted_close` is dropped deliberately."""
    records, index = [], []
    for row in rows:
        try:
            day = datetime.strptime(str(row["date"]), "%Y-%m-%d").date()
            record = {
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0.0),
            }
        except (KeyError, TypeError, ValueError):
            # One malformed bar is dropped, not the symbol. Ingestion's
            # verification gate is what decides whether what arrived is usable.
            log.warning("eodhd: unparseable bar for %s: %r", symbol, row)
            continue
        records.append(record)
        index.append((symbol.strip().upper(), day))

    if not records:
        return _empty_bars()
    return pd.DataFrame(
        records,
        index=pd.MultiIndex.from_tuples(index, names=["symbol", "date"]),
    )
