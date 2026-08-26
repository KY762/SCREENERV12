"""Alpaca option chain snapshots.

Uses the same credentials as market data. The free tier serves indicative
quotes rather than real-time OPRA, which matters: an indicative spread is an
estimate of an estimate, so treat the liquidity filters as directional rather
than exact and confirm the actual market in the broker before sending anything.

That caveat is not a formality. Selection here rejects contracts on spread
width, and rejecting on a spread that is itself approximate can both admit a
bad contract and exclude a good one.
"""

from __future__ import annotations

import logging
import time
from datetime import date

import httpx

from ..config import Settings, get_settings
from ..providers.base import ProviderError
from .contracts import OptionContract, parse_occ

log = logging.getLogger(__name__)

SNAPSHOT_PATH = "/v1beta1/options/snapshots/{underlying}"
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class AlpacaOptionsProvider:
    name = "alpaca-options"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        if not self.settings.has_alpaca_credentials:
            raise ProviderError(
                "Alpaca credentials are not configured. Option chains use the same "
                "keys as market data."
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

    def _get(self, path: str, params: dict) -> dict:
        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                response = self._client.get(path, params=params)
                if response.status_code in _RETRY_STATUS:
                    last_error = ProviderError(
                        f"{response.status_code} from Alpaca options: {response.text[:200]}"
                    )
                    log.warning(
                        "alpaca options transient %s, retry %d/%d in %.1fs",
                        response.status_code, attempt + 1, self.settings.max_retries, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (401, 403):
                    raise ProviderError(
                        "Alpaca refused the options request. Options data may not be "
                        "enabled on this account — check the dashboard, and note that "
                        "the free tier serves indicative rather than real-time quotes."
                    ) from exc
                raise ProviderError(
                    f"Alpaca options rejected the request ({status}): "
                    f"{exc.response.text[:200]}"
                ) from exc
            except httpx.RequestError as exc:
                last_error = exc
                log.warning("alpaca options network error, retry in %.1fs: %s", delay, exc)
                time.sleep(delay)
                delay *= 2
        raise ProviderError(f"Alpaca options failed after retries: {last_error}")

    def get_chain(
        self,
        underlying: str,
        *,
        expiry_after: date | None = None,
        expiry_before: date | None = None,
        feed: str = "indicative",
        limit: int = 1000,
    ) -> list[OptionContract]:
        """Snapshots for one underlying, paged until exhausted."""
        params: dict = {"feed": feed, "limit": min(limit, 1000)}
        if expiry_after:
            params["expiration_date_gte"] = expiry_after.isoformat()
        if expiry_before:
            params["expiration_date_lte"] = expiry_before.isoformat()

        path = SNAPSHOT_PATH.format(underlying=underlying.strip().upper())
        contracts: list[OptionContract] = []
        token: str | None = None
        while True:
            if token:
                params["page_token"] = token
            payload = self._get(path, params)
            contracts.extend(parse_snapshots(payload))
            token = payload.get("next_page_token")
            if not token or len(contracts) >= limit:
                break
        return contracts

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AlpacaOptionsProvider:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def parse_snapshots(payload: dict) -> list[OptionContract]:
    """Flatten the snapshot map into contracts. Pure and testable.

    Snapshots are keyed by OCC symbol, and the strike, expiry and right live in
    that key rather than in the body -- so a contract whose key will not parse
    is unusable and is dropped rather than guessed at.
    """
    out: list[OptionContract] = []
    for symbol, snapshot in ((payload or {}).get("snapshots") or {}).items():
        base = parse_occ(symbol)
        if base is None:
            continue
        quote = (snapshot or {}).get("latestQuote") or {}
        trade = (snapshot or {}).get("latestTrade") or {}
        greeks = (snapshot or {}).get("greeks") or {}

        out.append(
            OptionContract(
                symbol=base.symbol,
                underlying=base.underlying,
                expiry=base.expiry,
                strike=base.strike,
                right=base.right,
                bid=_number(quote.get("bp")),
                ask=_number(quote.get("ap")),
                last=_number(trade.get("p")) or None,
                volume=int(_number(trade.get("s"))),
                open_interest=int(_number((snapshot or {}).get("openInterest"))),
                delta=_optional(greeks.get("delta")),
                theta=_optional(greeks.get("theta")),
                implied_volatility=_optional((snapshot or {}).get("impliedVolatility")),
            )
        )
    return sorted(out, key=lambda c: (c.expiry, c.strike))


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
