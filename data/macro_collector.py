"""
Macro / geopolitical context collector via FRED.

Why FRED instead of news scraping:
- Stable, free, time-stamped, citable (Federal Reserve of St Louis).
- The Caldara-Iacoviello GPR series (GPRD) is the standard academic measure
  of geopolitical risk and is updated daily.
- Series like VIXCLS, DCOILWTICO, DTWEXBGS reflect global risk pricing,
  energy shock, and dollar regime — i.e. the macro envelope every prediction
  market trades within.

Anti-leakage: every value is stored with its observation date (UTC midnight).
Phase 1 features must join with the rule: feature_ts <= market_observation_ts.
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from typing import Any

from config.settings import FRED_SERIES, FRED_API_KEY
from data import storage

log = logging.getLogger(__name__)


def _to_utc_ts(date_str: str) -> int:
    # FRED dates are 'YYYY-MM-DD' in their native timezone, treat as UTC midnight
    dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def collect_macro(start_date: str = "2020-01-01") -> int:
    """
    Pull all configured FRED series and persist them.
    Uses the synchronous fredapi library (FRED is rate-friendly; no need for async).
    Returns total rows written.
    """
    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY missing. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html and put it in .env"
        )
    # Lazy import so the file is parseable even if fredapi isn't installed yet
    from fredapi import Fred  # type: ignore[import-not-found]

    fred = Fred(api_key=FRED_API_KEY)
    run_id = storage.log_run_start("macro", {"start_date": start_date,
                                              "series": list(FRED_SERIES)})
    total = 0
    fetched_ts = int(time.time())
    try:
        for series_id, label in FRED_SERIES.items():
            try:
                s = fred.get_series(series_id, observation_start=start_date)
            except Exception as e:
                log.warning("FRED series %s failed: %s", series_id, e)
                continue
            rows: list[dict[str, Any]] = []
            for date, value in s.items():
                ts = _to_utc_ts(str(date.date()))
                # FRED uses NaN for missing; store as NULL
                v = None if value != value else float(value)  # NaN check
                rows.append({
                    "series_id": series_id,
                    "ts": ts,
                    "value": v,
                    "fetched_ts": fetched_ts,
                })
            written = storage.upsert_macro(rows)
            total += written
            log.info("FRED %-10s (%s): %d rows", series_id, label, written)
    except Exception as e:
        storage.log_run_end(run_id, total, "failed", str(e))
        raise
    storage.log_run_end(run_id, total, "ok")
    return total
