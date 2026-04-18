"""
Polymarket data collector — Gamma + CLOB.

Design notes:
- Token-bucket rate limiter, one bucket per endpoint family + a global bucket.
- Tenacity retries with exponential backoff on 429/5xx and network errors.
- Parsing is defensive: Polymarket occasionally returns string-encoded JSON
  for fields like clobTokenIds, outcomes, outcomePrices. We unwrap them.
- Prices fidelity for closed markets: 60 min often returns empty per
  py-clob-client #216. We try fine first, then fall back to 720 min (12h).
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
)

from config.settings import (
    GAMMA_MARKETS, GAMMA_EVENTS, CLOB_PRICES_HISTORY,
    GLOBAL_BUDGET, MARKETS_BUDGET, EVENTS_BUDGET, CLOB_BUDGET,
    HTTP_TIMEOUT_SEC, HTTP_MAX_RETRIES, HTTP_BACKOFF_BASE_SEC,
    GAMMA_PAGE_SIZE, HOLDOUT_DAYS, RateBudget,
)
from data import storage

log = logging.getLogger(__name__)


# ---------- Token bucket (async-safe) ----------

class TokenBucket:
    """
    Simple async token bucket. Refills `requests` tokens every `window_sec`.
    """
    def __init__(self, budget: RateBudget):
        self.budget = budget
        self.capacity = budget.requests
        self.tokens = float(budget.requests)
        self.last_refill = time.monotonic()
        self.refill_per_sec = budget.requests / budget.window_sec
        self._lock = asyncio.Lock()

    async def take(self, n: int = 1) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.capacity, self.tokens + elapsed * self.refill_per_sec
                )
                self.last_refill = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                # not enough tokens; sleep until at least n are available
                deficit = n - self.tokens
                sleep_for = deficit / self.refill_per_sec
                await asyncio.sleep(sleep_for + 0.01)


@dataclass
class Limiter:
    """Bundle of buckets; .take() on (global, endpoint) before each request."""
    global_b: TokenBucket = field(default_factory=lambda: TokenBucket(GLOBAL_BUDGET))
    markets_b: TokenBucket = field(default_factory=lambda: TokenBucket(MARKETS_BUDGET))
    events_b: TokenBucket = field(default_factory=lambda: TokenBucket(EVENTS_BUDGET))
    clob_b: TokenBucket = field(default_factory=lambda: TokenBucket(CLOB_BUDGET))

    async def take(self, kind: str) -> None:
        await self.global_b.take()
        if kind == "markets":
            await self.markets_b.take()
        elif kind == "events":
            await self.events_b.take()
        elif kind == "clob":
            await self.clob_b.take()


# ---------- Retry policy ----------

class RetryableHTTP(Exception):
    pass


def _is_retryable_status(status: int) -> bool:
    return status == 429 or 500 <= status < 600


def _make_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=HTTP_BACKOFF_BASE_SEC, min=1, max=60),
        retry=retry_if_exception_type(
            (RetryableHTTP, httpx.TransportError, httpx.TimeoutException)
        ),
        before_sleep=before_sleep_log(log, logging.WARNING),
    )


# ---------- Parsing helpers ----------

def _maybe_load_json(value: Any) -> Any:
    """Polymarket sometimes returns JSON-encoded strings for arrays."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _parse_iso_to_ts(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        # Gamma returns ISO 8601 with 'Z' or '+00:00'
        s = iso.replace("Z", "+00:00")
        return int(datetime.fromisoformat(s).timestamp())
    except (ValueError, TypeError):
        return None


def _safe_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _resolve_outcome(market: dict[str, Any]) -> str | None:
    """
    Determine YES/NO/None from Gamma payload.

    A binary market has outcomes ~ ["Yes","No"] and outcomePrices that, after
    resolution, are "1"/"0" or "0"/"1". We use that as the source of truth.
    """
    if not market.get("closed"):
        return None
    prices = _maybe_load_json(market.get("outcomePrices"))
    outcomes = _maybe_load_json(market.get("outcomes"))
    if not isinstance(prices, list) or not isinstance(outcomes, list):
        return None
    if len(prices) != 2 or len(outcomes) != 2:
        return None
    try:
        p_yes = float(prices[0])
        p_no = float(prices[1])
    except (TypeError, ValueError):
        return None
    if abs(p_yes - 1.0) < 1e-6 and abs(p_no) < 1e-6:
        return "YES"
    if abs(p_no - 1.0) < 1e-6 and abs(p_yes) < 1e-6:
        return "NO"
    return None  # mid-resolution / disputed / invalid


def _category_from_tags(tags: Any) -> str | None:
    tags = _maybe_load_json(tags)
    if isinstance(tags, list) and tags:
        first = tags[0]
        if isinstance(first, dict):
            return first.get("label") or first.get("slug")
        if isinstance(first, str):
            return first
    return None


def _extract_token_ids(market: dict[str, Any]) -> tuple[str | None, str | None]:
    ids = _maybe_load_json(market.get("clobTokenIds"))
    if isinstance(ids, list) and len(ids) == 2:
        return str(ids[0]), str(ids[1])
    return None, None


def _normalize_market(raw: dict[str, Any], fetched_ts: int) -> dict[str, Any] | None:
    """Map a Gamma market payload to our DB schema. Returns None if non-binary."""
    outcomes = _maybe_load_json(raw.get("outcomes"))
    if not (isinstance(outcomes, list) and len(outcomes) == 2):
        # Non-binary or malformed; out of scope for Phase 0
        return None

    yes_id, no_id = _extract_token_ids(raw)
    end_ts = _parse_iso_to_ts(raw.get("endDate"))
    closed = bool(raw.get("closed"))
    resolved_ts = end_ts if closed else None  # Gamma doesn't expose UMA-finalize ts directly

    holdout = False
    if resolved_ts is not None:
        age_days = (fetched_ts - resolved_ts) / 86400.0
        holdout = age_days < HOLDOUT_DAYS

    return {
        "market_id": raw.get("conditionId") or raw.get("id"),
        "question": raw.get("question") or "",
        "slug": raw.get("slug"),
        "category": _category_from_tags(raw.get("tags")),
        "tags_json": json.dumps(_maybe_load_json(raw.get("tags")) or []),
        "yes_token_id": yes_id,
        "no_token_id": no_id,
        "start_ts": _parse_iso_to_ts(raw.get("startDate")),
        "end_ts": end_ts,
        "resolved_ts": resolved_ts,
        "resolved_outcome": _resolve_outcome(raw),
        "resolution_source": raw.get("resolutionSource"),
        "volume_total_usd": _safe_float(raw.get("volume")),
        "volume_24h_usd": _safe_float(raw.get("volume24hr")),
        "liquidity_usd": _safe_float(raw.get("liquidity")),
        "active": int(bool(raw.get("active"))),
        "closed": int(closed),
        "archived": int(bool(raw.get("archived"))),
        "holdout": int(holdout),
        "raw_json": json.dumps(raw, default=str),
        "fetched_ts": fetched_ts,
    }


# ---------- HTTP layer ----------

class PolymarketCollector:
    def __init__(self) -> None:
        self.limiter = Limiter()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PolymarketCollector":
        # Polymarket sits behind Cloudflare. A bare Python User-Agent can be
        # challenged. We send a conventional UA + Accept headers; Gamma is
        # public so no auth is involved.
        self._client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT_SEC,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; polymarket-research-bot/0.1; "
                    "+https://github.com/yourusername/polymarket_bot)"
                ),
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            http2=False,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, url: str, params: dict[str, Any], kind: str) -> Any:
        @_make_retry()
        async def _do() -> Any:
            await self.limiter.take(kind)
            assert self._client is not None
            resp = await self._client.get(url, params=params)
            if _is_retryable_status(resp.status_code):
                # honor Retry-After if present
                ra = resp.headers.get("Retry-After")
                if ra:
                    try:
                        await asyncio.sleep(float(ra))
                    except ValueError:
                        pass
                raise RetryableHTTP(f"{resp.status_code} on {url}")
            resp.raise_for_status()
            return resp.json()
        return await _do()

    # ----- Markets -----

    async def fetch_markets_page(
        self,
        offset: int,
        limit: int = GAMMA_PAGE_SIZE,
        closed: bool | None = None,
        start_date_min: str | None = None,
        end_date_max: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if closed is True:
            params["closed"] = "true"
        elif closed is False:
            params["closed"] = "false"
        if start_date_min:
            params["start_date_min"] = start_date_min
        if end_date_max:
            params["end_date_max"] = end_date_max
        # Order by liquidity desc to prioritize meaningful markets
        params["order"] = "volume"
        params["ascending"] = "false"

        data = await self._get(GAMMA_MARKETS, params, kind="markets")
        if not isinstance(data, list):
            log.warning("Unexpected /markets response shape: %s", type(data))
            return []
        return data

    async def collect_markets(
        self,
        closed: bool | None = True,
        months_lookback: int = 12,
        max_pages: int = 200,
    ) -> int:
        """Paginate through Gamma /markets and persist normalized rows."""
        run_id = storage.log_run_start(
            "markets",
            {"closed": closed, "months_lookback": months_lookback},
        )
        total_written = 0
        offset = 0
        empty_streak = 0
        fetched_ts = int(time.time())

        # Compute date filter for resolved markets
        start_date_min = None
        if closed and months_lookback:
            cutoff = datetime.now(timezone.utc).timestamp() - months_lookback * 30 * 86400
            start_date_min = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

        try:
            for page in range(max_pages):
                page_data = await self.fetch_markets_page(
                    offset=offset,
                    limit=GAMMA_PAGE_SIZE,
                    closed=closed,
                    start_date_min=start_date_min,
                )
                if not page_data:
                    empty_streak += 1
                    if empty_streak >= 2:
                        break
                    offset += GAMMA_PAGE_SIZE
                    continue
                empty_streak = 0

                normalized = [
                    n for raw in page_data
                    if (n := _normalize_market(raw, fetched_ts)) is not None
                    and n["market_id"] is not None
                ]
                written = storage.upsert_markets(normalized)
                total_written += written
                log.info(
                    "Page %d: fetched %d, normalized %d, written %d (offset=%d)",
                    page, len(page_data), len(normalized), written, offset,
                )
                offset += GAMMA_PAGE_SIZE
        except Exception as e:
            storage.log_run_end(run_id, total_written, "failed", str(e))
            raise
        storage.log_run_end(run_id, total_written, "ok")
        return total_written

    # ----- Prices -----

    async def fetch_price_history(
        self,
        token_id: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        fidelity: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Fetch /prices-history for a given CLOB token_id.

        Per docs: params are `market` (token_id), `startTs`/`endTs` OR `interval`
        (mutually exclusive), and `fidelity` in minutes.
        """
        params: dict[str, Any] = {"market": token_id, "fidelity": fidelity}
        if start_ts is not None and end_ts is not None:
            params["startTs"] = int(start_ts)
            params["endTs"] = int(end_ts)
        else:
            params["interval"] = "max"

        data = await self._get(CLOB_PRICES_HISTORY, params, kind="clob")
        history = data.get("history", []) if isinstance(data, dict) else []
        return history

    async def collect_prices_for_market(
        self,
        market_id: str,
        yes_token_id: str,
        no_token_id: str | None,
        end_ts: int | None,
    ) -> int:
        """
        Pull both YES and NO timeseries with sensible fidelity.
        Tries 60min first; if empty (closed-market limitation), falls back to 720min.
        """
        fetched_ts = int(time.time())
        total = 0
        for token_id, side in [(yes_token_id, "YES"), (no_token_id, "NO")]:
            if not token_id:
                continue
            history: list[dict[str, Any]] = []
            for fidelity in (60, 720):
                try:
                    history = await self.fetch_price_history(
                        token_id, fidelity=fidelity,
                    )
                except Exception as e:
                    log.warning("Price fetch failed for %s (%s): %s",
                                market_id, side, e)
                    continue
                if history:
                    break
            if not history:
                log.info("No price history for %s (%s)", market_id, side)
                continue

            rows = []
            for pt in history:
                ts = pt.get("t")
                price = pt.get("p")
                if ts is None or price is None:
                    continue
                rows.append({
                    "token_id": token_id,
                    "ts": int(ts),
                    "price": float(price),
                    "fidelity": int(fidelity),
                    "fetched_ts": fetched_ts,
                })
            written = storage.upsert_prices(rows)
            total += written
        return total

    async def collect_prices_for_all(
        self,
        closed_only: bool = True,
        exclude_holdout: bool = True,
        concurrency: int = 4,
    ) -> int:
        targets = storage.list_market_tokens(
            closed_only=closed_only, exclude_holdout=exclude_holdout,
        )
        log.info("Will fetch prices for %d markets", len(targets))
        run_id = storage.log_run_start(
            "prices",
            {"closed_only": closed_only, "exclude_holdout": exclude_holdout,
             "n_markets": len(targets)},
        )
        sem = asyncio.Semaphore(concurrency)
        total = 0

        async def worker(t: tuple[str, str, str | None, int | None]) -> int:
            async with sem:
                mid, yes_id, no_id, end_ts = t
                try:
                    return await self.collect_prices_for_market(mid, yes_id, no_id, end_ts)
                except Exception as e:
                    log.warning("Skipping market %s: %s", mid, e)
                    return 0

        try:
            results = await asyncio.gather(*[worker(t) for t in targets])
            total = sum(results)
        except Exception as e:
            storage.log_run_end(run_id, total, "failed", str(e))
            raise
        storage.log_run_end(run_id, total, "ok")
        return total
