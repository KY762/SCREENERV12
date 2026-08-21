"""Tiingo market-data adapter.

Chosen after Alpaca's free tier turned out to serve only the most recent years
(measured: first available bar 2020-07-27, on a request starting 2010-01-01).
The research design needs a development window that carries no evidential
weight, and there is no way to have one if all the available history is the
window the hypotheses will eventually be judged on.

Why this provider fits the schema
---------------------------------
Tiingo returns RAW and ADJUSTED prices as separate fields on every row:

    open / high / low / close / volume            as traded
    adjOpen / adjHigh / adjLow / adjClose         back-adjusted
    splitFactor / divCash                         the events causing the two to differ

That matches the platform's storage policy exactly -- raw bars in price_daily,
corporate actions in their own table, adjusted series derived on demand. Sources
that serve only adjusted history (Yahoo among them) would silently rewrite
stored history at every split.

Alpaca is NOT removed. It stays as the execution and paper-trading path, and
its overlap window doubles as an independent check on this data, since the two
share no code and no vendor.

Rate limits
-----------
The free tier is capped per hour and per day. A limit response is surfaced as a
ProviderError naming the wait rather than retried into the ground -- ingestion
records the failure per symbol and continues, so a capped run is resumable by
re-running the same command.
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

_RETRY_STATUS = frozenset({500, 502, 503, 504})
_RATE_LIMIT_STATUS = 429


class TiingoProvider:
    """Implements PriceProvider against Tiingo's end-of-day API.

    One request per symbol -- Tiingo has no multi-symbol daily endpoint -- so a
    wide universe is slow on the free tier. That is a one-time backfill cost;
    subsequent runs fetch only the tail.
    """

    name = "tiingo"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        if not self.settings.has_tiingo_credentials:
            raise ProviderError(
                "Tiingo API key is not configured. Set TIINGO_API_KEY in .env "
                "(free key at tiingo.com -- see .env.example)."
            )
        token = self.settings.tiingo_api_key.get_secret_value()
        self._client = client or httpx.Client(
            base_url=self.settings.tiingo_base_url,
            timeout=self.settings.request_timeout_seconds,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Token {token}",
            },
        )

    # -- http ---------------------------------------------------------------

    def _get(self, path: str, params: dict) -> list[dict]:
        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                response = self._client.get(path, params=params)

                if response.status_code == _RATE_LIMIT_STATUS:
                    # Not retried. The free tier's window is measured in hours,
                    # and backing off inside a single command would hang for
                    # longer than anyone will wait at a terminal.
                    raise ProviderError(
                        "Tiingo rate limit reached. The free tier caps requests per "
                        "hour and per day. Wait and re-run the same command -- "
                        "already-stored bars are skipped, so it resumes where it "
                        "stopped."
                    )
                if response.status_code in _RETRY_STATUS:
                    last_error = ProviderError(
                        f"{response.status_code} from Tiingo: {response.text[:200]}"
                    )
                    log.warning(
                        "tiingo transient %s on %s, retry %d/%d in %.1fs",
                        response.status_code, path, attempt + 1,
                        self.settings.max_retries, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    # Tiingo reports errors as a JSON object; success is a list.
                    raise ProviderError(
                        f"Tiingo returned an error: {payload.get('detail', payload)}"
                    )
                return payload
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    raise ProviderError(
                        f"Tiingo does not recognise this symbol ({path})."
                    ) from exc
                raise ProviderError(
                    f"Tiingo rejected the request ({status}): {exc.response.text[:200]}"
                ) from exc
            except httpx.RequestError as exc:
                last_error = exc
                log.warning("tiingo network error on %s, retry in %.1fs: %s", path, delay, exc)
                time.sleep(delay)
                delay *= 2
        raise ProviderError(f"Tiingo request failed after retries: {last_error}")

    # -- bars ---------------------------------------------------------------

    def get_daily_bars(self, request: BarRequest) -> pd.DataFrame:
        if request.adjustment != "raw":
            log.warning(
                "requesting adjustment=%r; the platform stores raw bars and derives "
                "adjustments from corporate actions (see providers.base.PriceProvider)",
                request.adjustment,
            )

        frames: list[pd.DataFrame] = []
        failures: list[str] = []
        for symbol in request.symbols:
            try:
                rows = self._fetch_symbol(symbol, request.start, request.end)
            except ProviderError as exc:
                if "rate limit" in str(exc).lower():
                    raise            # a cap applies to every remaining symbol
                failures.append(f"{symbol}: {exc}")
                continue
            if rows:
                frames.append(_rows_to_frame(symbol, rows))

        if failures:
            log.warning("tiingo skipped %d symbol(s): %s", len(failures), "; ".join(failures))
        if not frames:
            return _empty_bars()

        out = pd.concat(frames, ignore_index=True)
        out = out.drop_duplicates(subset=["symbol", "date"], keep="last")
        return out.set_index(["symbol", "date"]).sort_index()

    def _fetch_symbol(self, symbol: str, start: date, end: date) -> list[dict]:
        return self._get(
            f"/tiingo/daily/{symbol.lower()}/prices",
            {
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "format": "json",
                "resampleFreq": "daily",
            },
        )

    # -- corporate actions --------------------------------------------------

    def get_corporate_actions(
        self, symbols: tuple[str, ...], start: date, end: date
    ) -> list[CorporateAction]:
        """Splits and dividends, read from the daily rows that carry them.

        Tiingo puts ``splitFactor`` and ``divCash`` on the price rows rather
        than behind a separate endpoint, so this costs no extra requests when
        bars have already been fetched -- but it is written to stand alone.
        """
        actions: list[CorporateAction] = []
        for symbol in symbols:
            try:
                rows = self._fetch_symbol(symbol, start, end)
            except ProviderError as exc:
                if "rate limit" in str(exc).lower():
                    raise
                log.warning("tiingo corporate actions unavailable for %s: %s", symbol, exc)
                continue
            actions.extend(parse_corporate_actions(symbol, rows))
        return actions

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TiingoProvider:
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


def _rows_to_frame(symbol: str, rows: list[dict]) -> pd.DataFrame:
    """Build a raw-price frame. The adj* columns are deliberately discarded.

    Storing adjusted prices would make history mutate at every future split:
    what the file says about 2019 would change because of something that
    happened this morning. Splits are captured separately as corporate actions.
    """
    frame = pd.DataFrame(rows)
    frame["symbol"] = symbol
    frame["date"] = pd.to_datetime(frame["date"], utc=True, format="ISO8601").dt.date
    keep = ["symbol", "date", "open", "high", "low", "close", "volume"]
    return frame[keep].astype(
        {"open": "float64", "high": "float64", "low": "float64",
         "close": "float64", "volume": "float64"}
    )


def parse_corporate_actions(symbol: str, rows: list[dict]) -> list[CorporateAction]:
    """Extract splits and dividends from Tiingo daily rows.

    A row's ``splitFactor`` is 1.0 on an ordinary day, and the row carrying a
    factor is the ex-date itself.
    """
    out: list[CorporateAction] = []
    for row in rows:
        try:
            ex_date = pd.Timestamp(row["date"]).date()
        except (KeyError, ValueError):
            continue

        factor = row.get("splitFactor")
        if factor is not None and float(factor) != 1.0:
            out.append(
                CorporateAction(
                    symbol=symbol, ex_date=ex_date,
                    action_type="split", ratio=float(factor),
                )
            )

        cash = row.get("divCash")
        if cash is not None and float(cash) > 0:
            out.append(
                CorporateAction(
                    symbol=symbol, ex_date=ex_date,
                    action_type="dividend", amount=float(cash),
                )
            )
    return out
