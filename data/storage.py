"""
SQLite storage layer.

Schema is intentionally normalized:
- markets: one row per binary market (market_id is Polymarket's condition_id)
- price_history: time series, one row per (token_id, ts)
- macro_series: time series, one row per (series_id, ts)
- collection_runs: audit log for reproducibility

Anti-leakage helpers:
- markets.holdout flag (TRUE for markets resolved within HOLDOUT_DAYS)
- All time fields are stored as Unix timestamps (UTC seconds, INTEGER)
"""
from __future__ import annotations
import sqlite3
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator
from config.settings import DB_PATH

log = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    market_id          TEXT PRIMARY KEY,         -- condition_id (on-chain)
    question           TEXT NOT NULL,
    slug               TEXT,
    category           TEXT,                     -- primary tag label
    tags_json          TEXT,                     -- full tags array as JSON
    yes_token_id       TEXT,
    no_token_id        TEXT,
    start_ts           INTEGER,                  -- market open (UTC seconds)
    end_ts             INTEGER,                  -- market scheduled close
    resolved_ts        INTEGER,                  -- actual resolution time
    resolved_outcome   TEXT,                     -- 'YES' / 'NO' / NULL if open
    resolution_source  TEXT,                     -- 'UMA' / 'Chainlink' / NULL
    volume_total_usd   REAL,
    volume_24h_usd     REAL,
    liquidity_usd      REAL,
    active             INTEGER NOT NULL DEFAULT 0, -- bool
    closed             INTEGER NOT NULL DEFAULT 0, -- bool
    archived           INTEGER NOT NULL DEFAULT 0, -- bool
    holdout            INTEGER NOT NULL DEFAULT 0, -- bool, anti-leakage
    raw_json           TEXT NOT NULL,            -- full Gamma payload
    fetched_ts         INTEGER NOT NULL          -- when WE fetched it
);
CREATE INDEX IF NOT EXISTS idx_markets_resolved_ts ON markets(resolved_ts);
CREATE INDEX IF NOT EXISTS idx_markets_category    ON markets(category);
CREATE INDEX IF NOT EXISTS idx_markets_closed      ON markets(closed);
CREATE INDEX IF NOT EXISTS idx_markets_holdout     ON markets(holdout);

CREATE TABLE IF NOT EXISTS price_history (
    token_id   TEXT NOT NULL,
    ts         INTEGER NOT NULL,                  -- UTC seconds
    price      REAL NOT NULL,                     -- in [0, 1]
    fidelity   INTEGER NOT NULL,                  -- minutes; provenance
    fetched_ts INTEGER NOT NULL,
    PRIMARY KEY (token_id, ts)
);
CREATE INDEX IF NOT EXISTS idx_prices_ts ON price_history(ts);

CREATE TABLE IF NOT EXISTS macro_series (
    series_id  TEXT NOT NULL,                     -- e.g. 'VIXCLS'
    ts         INTEGER NOT NULL,                  -- UTC seconds (date 00:00:00)
    value      REAL,                              -- NULL allowed (holidays)
    fetched_ts INTEGER NOT NULL,
    PRIMARY KEY (series_id, ts)
);
CREATE INDEX IF NOT EXISTS idx_macro_ts ON macro_series(ts);

CREATE TABLE IF NOT EXISTS collection_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_ts   INTEGER NOT NULL,
    finished_ts  INTEGER,
    kind         TEXT NOT NULL,                   -- 'markets'|'prices'|'macro'
    params_json  TEXT,
    rows_written INTEGER,
    status       TEXT,                            -- 'ok'|'partial'|'failed'
    error        TEXT
);
"""


@contextmanager
def connect(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    """Idempotent schema initialization."""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
    log.info("Initialized DB at %s", db_path)


def upsert_markets(rows: Iterable[dict[str, Any]], db_path: Path = DB_PATH) -> int:
    """Insert or replace markets. Returns number of rows written."""
    sql = """
    INSERT INTO markets(
      market_id, question, slug, category, tags_json,
      yes_token_id, no_token_id, start_ts, end_ts, resolved_ts,
      resolved_outcome, resolution_source, volume_total_usd, volume_24h_usd,
      liquidity_usd, active, closed, archived, holdout, raw_json, fetched_ts
    ) VALUES (
      :market_id, :question, :slug, :category, :tags_json,
      :yes_token_id, :no_token_id, :start_ts, :end_ts, :resolved_ts,
      :resolved_outcome, :resolution_source, :volume_total_usd, :volume_24h_usd,
      :liquidity_usd, :active, :closed, :archived, :holdout, :raw_json, :fetched_ts
    )
    ON CONFLICT(market_id) DO UPDATE SET
      question=excluded.question,
      slug=excluded.slug,
      category=excluded.category,
      tags_json=excluded.tags_json,
      yes_token_id=excluded.yes_token_id,
      no_token_id=excluded.no_token_id,
      start_ts=excluded.start_ts,
      end_ts=excluded.end_ts,
      resolved_ts=excluded.resolved_ts,
      resolved_outcome=excluded.resolved_outcome,
      resolution_source=excluded.resolution_source,
      volume_total_usd=excluded.volume_total_usd,
      volume_24h_usd=excluded.volume_24h_usd,
      liquidity_usd=excluded.liquidity_usd,
      active=excluded.active,
      closed=excluded.closed,
      archived=excluded.archived,
      holdout=excluded.holdout,
      raw_json=excluded.raw_json,
      fetched_ts=excluded.fetched_ts;
    """
    rows_list = list(rows)
    if not rows_list:
        return 0
    with connect(db_path) as conn:
        conn.executemany(sql, rows_list)
    return len(rows_list)


def upsert_prices(rows: Iterable[dict[str, Any]], db_path: Path = DB_PATH) -> int:
    sql = """
    INSERT OR REPLACE INTO price_history(token_id, ts, price, fidelity, fetched_ts)
    VALUES (:token_id, :ts, :price, :fidelity, :fetched_ts);
    """
    rows_list = list(rows)
    if not rows_list:
        return 0
    with connect(db_path) as conn:
        conn.executemany(sql, rows_list)
    return len(rows_list)


def upsert_macro(rows: Iterable[dict[str, Any]], db_path: Path = DB_PATH) -> int:
    sql = """
    INSERT OR REPLACE INTO macro_series(series_id, ts, value, fetched_ts)
    VALUES (:series_id, :ts, :value, :fetched_ts);
    """
    rows_list = list(rows)
    if not rows_list:
        return 0
    with connect(db_path) as conn:
        conn.executemany(sql, rows_list)
    return len(rows_list)


def log_run_start(kind: str, params: dict[str, Any], db_path: Path = DB_PATH) -> int:
    import time
    with connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO collection_runs(started_ts, kind, params_json, status) "
            "VALUES (?, ?, ?, 'running')",
            (int(time.time()), kind, json.dumps(params, default=str)),
        )
        return cur.lastrowid


def log_run_end(
    run_id: int,
    rows_written: int,
    status: str,
    error: str | None = None,
    db_path: Path = DB_PATH,
) -> None:
    import time
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE collection_runs SET finished_ts=?, rows_written=?, status=?, error=? "
            "WHERE id=?",
            (int(time.time()), rows_written, status, error, run_id),
        )


def list_market_tokens(
    closed_only: bool = True,
    exclude_holdout: bool = True,
    db_path: Path = DB_PATH,
) -> list[tuple[str, str, str | None, int | None]]:
    """Return list of (market_id, yes_token_id, no_token_id, end_ts) needing prices."""
    where = []
    if closed_only:
        where.append("closed = 1")
    if exclude_holdout:
        where.append("holdout = 0")
    where.append("yes_token_id IS NOT NULL")
    sql = (
        "SELECT market_id, yes_token_id, no_token_id, end_ts FROM markets "
        + ("WHERE " + " AND ".join(where) if where else "")
    )
    with connect(db_path) as conn:
        return [(r[0], r[1], r[2], r[3]) for r in conn.execute(sql)]
