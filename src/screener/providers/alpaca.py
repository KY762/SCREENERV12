"""Alpaca market-data adapter.

Free tier, chosen because it collapses three integrations into one: the same
credentials serve historical data, paper-trading forward tests, and eventual
live execution.

Known limitation, restated here so it stays visible at the point of use:
Alpaca's free tier has limited delisted-ticker coverage, so a historical
universe built from it skews toward survivors. The >=$20M ADV liquidity filter
reduces the effect materially -- large liquid names rarely delist to zero -- but
does not remove it. Every backtest report must state this. Polygon (~$29/mo)
carries delisted tickers and is the documented upgrade path.
"""

from __future__ import annotations

import logging
import time
from datetime import date

import httpx
import pandas as pd

from ..config import Settings, get_settings
from .base import BarRequest, CorporateAction, ProviderError

log = logging.getLogger(__name__)

_MAX_SYMBOLS_PER_REQUEST = 100
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class AlpacaProvider:
    """Implements PriceProvider against Alpaca's market-data v2 API."""

    name = "alpaca"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        if not self.settings.has_alpaca_credentials:
            raise ProviderError(
                "Alpaca credentials are not configured. Set ALPACA_API_KEY_ID and "
                "ALPACA_API_SECRET_KEY in .env (see .env.example)."
            )
        self._client = client or httpx.Client(
            base_url=self.settings.alpaca_data_url,
            timeout=self.settings.request_timeout_seconds,
            headers={
                "APCA-API-KEY-ID": self.settings.alpaca_api_key_id.get_secret_value(),
                "APCA-API-SECRET-KEY": self.settings.alpaca_api_secret_key.get_secret_value(),
                "accept": "application/json",
            },
        )

    # -- http ---------------------------------------------------------------

    def _get(self, path: str, params: dict) -> dict:
        """GET with exponential backoff on transient failures."""
        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                response = self._client.get(path, params=params)
                if response.status_code in _RETRY_STATUS:
                    last_error = ProviderError(
                        f"{response.status_code} from Alpaca: {response.text[:200]}"
                    )
                    log.warning(
                        "alpaca transient %s on %s, retry %d/%d in %.1fs",
                        response.status_code, path, attempt + 1,
                        self.settings.max_retries, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                raise ProviderError(
                    f"Alpaca rejected the request ({exc.response.status_code}): "
                    f"{exc.response.text[:200]}"
                ) from exc
            except httpx.RequestError as exc:
                last_error = exc
                log.warning("alpaca network error on %s, retry in %.1fs: %s", path, delay, exc)
                time.sleep(delay)
                delay *= 2
        raise ProviderError(f"Alpaca request failed after retries: {last_error}")

    # -- bars ---------------------------------------------------------------

    def get_daily_bars(self, request: BarRequest) -> pd.DataFrame:
        if request.adjustment != "raw":
            log.warning(
                "requesting adjustment=%r; the platform stores raw bars and derives "
                "adjustments from corporate actions (see providers.base.PriceProvider)",
                request.adjustment,
            )
        frames: list[pd.DataFrame] = []
        symbols = list(request.symbols)
        for i in range(0, len(symbols), _MAX_SYMBOLS_PER_REQUEST):
            chunk = symbols[i : i + _MAX_SYMBOLS_PER_REQUEST]
            frames.extend(self._fetch_chunk(chunk, request))
        if not frames:
            return _empty_bars()
        out = pd.concat(frames, ignore_index=True)
        out = out.drop_duplicates(subset=["symbol", "date"], keep="last")
        return out.set_index(["symbol", "date"]).sort_index()

    def _fetch_chunk(self, chunk: list[str], request: BarRequest) -> list[pd.DataFrame]:
        params = {
            "symbols": ",".join(chunk),
            "timeframe": "1Day",
            "start": request.start.isoformat(),
            "end": request.end.isoformat(),
            "adjustment": request.adjustment,
            "feed": self.settings.alpaca_feed,
            "limit": 10_000,
        }
        frames: list[pd.DataFrame] = []
        page_token: str | None = None
        while True:
            if page_token:
                params["page_token"] = page_token
            payload = self._get("/v2/stocks/bars", params)
            for symbol, bars in (payload.get("bars") or {}).items():
                if bars:
                    frames.append(_bars_to_frame(symbol, bars))
            page_token = payload.get("next_page_token")
            if not page_token:
                break
        return frames

    # -- corporate actions --------------------------------------------------

    def get_corporate_actions(
        self, symbols: tuple[str, ...], start: date, end: date
    ) -> list[CorporateAction]:
        """Splits and cash dividends, used to derive adjusted series on demand."""
        actions: list[CorporateAction] = []
        symbol_list = list(symbols)
        for i in range(0, len(symbol_list), _MAX_SYMBOLS_PER_REQUEST):
            chunk = symbol_list[i : i + _MAX_SYMBOLS_PER_REQUEST]
            payload = self._get(
                "/v1/corporate-actions",
                {
                    "symbols": ",".join(chunk),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "types": "forward_split,reverse_split,cash_dividend",
                    "limit": 1000,
                },
            )
            actions.extend(_parse_corporate_actions(payload))
        return actions

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AlpacaProvider:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


# -- parsing helpers (pure, so they are unit-testable without a network) -----

def _empty_bars() -> pd.DataFrame:
    idx = pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"])
    return pd.DataFrame(
        {c: pd.Series(dtype="float64") for c in ("open", "high", "low", "close", "volume")},
        index=idx,
    )


def _bars_to_frame(symbol: str, bars: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(bars)
    frame = frame.rename(
        columns={"t": "date", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
    )
    frame["symbol"] = symbol
    # Alpaca timestamps daily bars at 05:00Z; the trading DATE is what matters.
    frame["date"] = pd.to_datetime(frame["date"], utc=True, format="ISO8601").dt.date
    keep = ["symbol", "date", "open", "high", "low", "close", "volume"]
    return frame[keep].astype(
        {"open": "float64", "high": "float64", "low": "float64",
         "close": "float64", "volume": "float64"}
    )


def _parse_corporate_actions(payload: dict) -> list[CorporateAction]:
    out: list[CorporateAction] = []
    container = payload.get("corporate_actions") or {}
    for kind in ("forward_splits", "reverse_splits"):
        for item in container.get(kind) or []:
            old, new = item.get("old_rate"), item.get("new_rate")
            ratio = (float(new) / float(old)) if old and new else None
            out.append(
                CorporateAction(
                    symbol=item["symbol"],
                    ex_date=date.fromisoformat(item["ex_date"]),
                    action_type="split",
                    ratio=ratio,
                )
            )
    for item in container.get("cash_dividends") or []:
        out.append(
            CorporateAction(
                symbol=item["symbol"],
                ex_date=date.fromisoformat(item["ex_date"]),
                action_type="dividend",
                amount=float(item["rate"]) if item.get("rate") is not None else None,
            )
        )
    return out
