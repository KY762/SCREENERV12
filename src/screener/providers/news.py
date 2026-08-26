"""Alpaca news feed.

Free with the market-data credentials already configured -- no separate account,
no extra tier. Headlines are Benzinga-sourced and carry the symbols they refer
to, which is what makes them joinable to a screen rather than a separate reading
exercise.

What news is and is not good for here
-------------------------------------
At a 3-15 day horizon, a headline is CONTEXT, not a signal. By the time a story
is published the move has usually happened, and the platform has no way to
measure whether a given headline predicts anything. Treating "lots of news" as
bullish is how a screen manufactures conviction.

Its honest use is the opposite: explaining a move you can already see, and
flagging that something happened before you size into it. A stock up 9% on
volume with no news is a different situation from the same move on a guidance
raise, and only one of them is likely to persist.

Nothing here scores sentiment. A sentiment number computed from headlines is
false precision, and there is no evidence in this project that it predicts
anything.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime

import httpx

from ..config import Settings, get_settings
from .base import ProviderError

log = logging.getLogger(__name__)

NEWS_PATH = "/v1beta1/news"
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_PAGE = 50


@dataclass(frozen=True)
class NewsItem:
    id: str
    headline: str
    summary: str
    source: str
    url: str
    symbols: tuple[str, ...]
    created_at: datetime
    author: str | None = None

    @property
    def trade_date(self) -> date:
        """The session this lands in. News after the close belongs to the next
        session's decision, not the one that already happened."""
        return self.created_at.date()


class AlpacaNewsProvider:
    """Headlines by symbol and date range."""

    name = "alpaca-news"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        if not self.settings.has_alpaca_credentials:
            raise ProviderError(
                "Alpaca credentials are not configured. The news feed uses the same "
                "keys as market data — set ALPACA_API_KEY_ID and "
                "ALPACA_API_SECRET_KEY in .env."
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

    def _get(self, params: dict) -> dict:
        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                response = self._client.get(NEWS_PATH, params=params)
                if response.status_code in _RETRY_STATUS:
                    last_error = ProviderError(
                        f"{response.status_code} from Alpaca news: {response.text[:200]}"
                    )
                    log.warning(
                        "alpaca news transient %s, retry %d/%d in %.1fs",
                        response.status_code, attempt + 1, self.settings.max_retries, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                raise ProviderError(
                    f"Alpaca news rejected the request ({exc.response.status_code}): "
                    f"{exc.response.text[:200]}"
                ) from exc
            except httpx.RequestError as exc:
                last_error = exc
                log.warning("alpaca news network error, retry in %.1fs: %s", delay, exc)
                time.sleep(delay)
                delay *= 2
        raise ProviderError(f"Alpaca news failed after retries: {last_error}")

    def get_news(
        self,
        symbols: tuple[str, ...],
        start: date,
        end: date,
        *,
        limit: int = 200,
    ) -> list[NewsItem]:
        """Headlines mentioning any of ``symbols`` in the window, newest first."""
        params = {
            "symbols": ",".join(s.strip().upper() for s in symbols if s.strip()),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": min(MAX_PAGE, limit),
            "sort": "desc",
            "include_content": "false",
        }

        items: list[NewsItem] = []
        token: str | None = None
        while len(items) < limit:
            if token:
                params["page_token"] = token
            payload = self._get(params)
            items.extend(parse_news(payload))
            token = payload.get("next_page_token")
            if not token:
                break
        return items[:limit]

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AlpacaNewsProvider:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def parse_news(payload: dict) -> list[NewsItem]:
    """Parse the news block. Pure, so the shape is pinned without a network."""
    out: list[NewsItem] = []
    for record in (payload or {}).get("news") or []:
        created = _parse_timestamp(record.get("created_at"))
        if created is None or not record.get("headline"):
            continue
        out.append(
            NewsItem(
                id=str(record.get("id") or ""),
                headline=str(record["headline"]).strip(),
                summary=str(record.get("summary") or "").strip(),
                source=str(record.get("source") or "unknown"),
                url=str(record.get("url") or ""),
                symbols=tuple(
                    str(s).upper() for s in (record.get("symbols") or [])
                ),
                created_at=created,
                author=str(record.get("author")) if record.get("author") else None,
            )
        )
    return out


def _parse_timestamp(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def headlines_by_symbol(items: list[NewsItem]) -> dict[str, list[NewsItem]]:
    """Group by symbol. An item mentioning three tickers appears under each --
    a story about a supplier is news for the customer too."""
    grouped: dict[str, list[NewsItem]] = {}
    for item in items:
        for symbol in item.symbols:
            grouped.setdefault(symbol, []).append(item)
    for symbol in grouped:
        grouped[symbol].sort(key=lambda i: i.created_at, reverse=True)
    return grouped
