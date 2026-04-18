"""
Phase 0 exploration & sanity reports.

Strict rule: this module MUST NOT touch markets where holdout=1.
That dataset is reserved for Phase 3 final validation.

Outputs:
- Coverage stats (#markets, #closed, #with prices, by category)
- Resolution outcome balance
- Calibration probe by decile (Brier score, accuracy)
- Late-resolution drift probe (price 48h before close vs close)
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from typing import Any
import pandas as pd
import numpy as np
from data import storage

log = logging.getLogger(__name__)


@dataclass
class CoverageReport:
    n_markets: int
    n_closed: int
    n_holdout_excluded: int
    n_with_yes_prices: int
    by_category: pd.DataFrame
    yes_no_balance: dict[str, float]


def coverage() -> CoverageReport:
    with storage.connect() as conn:
        markets = pd.read_sql_query(
            "SELECT market_id, category, closed, holdout, resolved_outcome, "
            "yes_token_id FROM markets",
            conn,
        )
        prices_count = pd.read_sql_query(
            "SELECT token_id, COUNT(*) as n FROM price_history GROUP BY token_id",
            conn,
        )

    n_markets = len(markets)
    n_closed = int(markets["closed"].sum())
    n_holdout = int(markets["holdout"].sum())

    eligible = markets[(markets["closed"] == 1) & (markets["holdout"] == 0)]
    eligible_with_prices = eligible.merge(
        prices_count, left_on="yes_token_id", right_on="token_id", how="inner",
    )
    n_with_prices = len(eligible_with_prices)

    by_cat = (
        eligible.groupby("category", dropna=False)
        .agg(n=("market_id", "count"),
             n_yes=("resolved_outcome", lambda s: int((s == "YES").sum())),
             n_no=("resolved_outcome", lambda s: int((s == "NO").sum())))
        .reset_index()
        .sort_values("n", ascending=False)
    )

    yn = eligible["resolved_outcome"].value_counts(dropna=False).to_dict()

    return CoverageReport(
        n_markets=n_markets,
        n_closed=n_closed,
        n_holdout_excluded=n_holdout,
        n_with_yes_prices=n_with_prices,
        by_category=by_cat,
        yes_no_balance={str(k): int(v) for k, v in yn.items()},
    )


def _price_at_offset(prices: pd.DataFrame, target_ts: int) -> float | None:
    """Return last price <= target_ts, else None."""
    s = prices[prices["ts"] <= target_ts]
    if s.empty:
        return None
    return float(s.iloc[-1]["price"])


def calibration_probe(
    hours_before_close: float = 24.0,
    n_bins: int = 10,
) -> pd.DataFrame:
    """
    For every closed (non-holdout) market with YES price history, look at the
    YES price `hours_before_close` before close, bin it into `n_bins` deciles,
    and compute realized YES rate + Brier score per bin.

    Output columns:
      bin, n, mean_predicted, realized_yes_rate, brier, miscalibration
    """
    with storage.connect() as conn:
        markets = pd.read_sql_query(
            "SELECT market_id, yes_token_id, end_ts, resolved_outcome, category "
            "FROM markets "
            "WHERE closed = 1 AND holdout = 0 "
            "  AND resolved_outcome IN ('YES','NO') "
            "  AND yes_token_id IS NOT NULL AND end_ts IS NOT NULL",
            conn,
        )
        prices = pd.read_sql_query(
            "SELECT token_id, ts, price FROM price_history ORDER BY token_id, ts",
            conn,
        )

    samples: list[dict[str, Any]] = []
    by_token = {tok: g for tok, g in prices.groupby("token_id")}
    offset_sec = int(hours_before_close * 3600)

    for _, m in markets.iterrows():
        g = by_token.get(m["yes_token_id"])
        if g is None or g.empty:
            continue
        target_ts = int(m["end_ts"]) - offset_sec
        p = _price_at_offset(g, target_ts)
        if p is None:
            continue
        samples.append({
            "predicted": p,
            "realized": 1.0 if m["resolved_outcome"] == "YES" else 0.0,
            "category": m["category"],
        })

    if not samples:
        return pd.DataFrame(columns=[
            "bin", "n", "mean_predicted", "realized_yes_rate", "brier", "miscalibration",
        ])

    df = pd.DataFrame(samples)
    df["bin"] = pd.cut(
        df["predicted"], bins=np.linspace(0, 1, n_bins + 1),
        include_lowest=True, labels=False,
    )
    grp = df.groupby("bin", dropna=True).agg(
        n=("predicted", "count"),
        mean_predicted=("predicted", "mean"),
        realized_yes_rate=("realized", "mean"),
    ).reset_index()
    grp["brier"] = df.groupby("bin").apply(
        lambda x: float(np.mean((x["predicted"] - x["realized"]) ** 2))
    ).values
    grp["miscalibration"] = grp["mean_predicted"] - grp["realized_yes_rate"]
    return grp


def late_drift_probe(window_hours: float = 48.0) -> pd.DataFrame:
    """
    For each market, compute (price_at_close - price_window_before_close).
    Aggregate by category and predicted-bucket to look for systematic drift.
    """
    with storage.connect() as conn:
        markets = pd.read_sql_query(
            "SELECT market_id, yes_token_id, end_ts, resolved_outcome, category "
            "FROM markets "
            "WHERE closed = 1 AND holdout = 0 "
            "  AND resolved_outcome IN ('YES','NO') "
            "  AND yes_token_id IS NOT NULL AND end_ts IS NOT NULL",
            conn,
        )
        prices = pd.read_sql_query(
            "SELECT token_id, ts, price FROM price_history ORDER BY token_id, ts",
            conn,
        )

    by_token = {tok: g for tok, g in prices.groupby("token_id")}
    offset_sec = int(window_hours * 3600)
    rows = []
    for _, m in markets.iterrows():
        g = by_token.get(m["yes_token_id"])
        if g is None or g.empty:
            continue
        p_before = _price_at_offset(g, int(m["end_ts"]) - offset_sec)
        p_close = _price_at_offset(g, int(m["end_ts"]))
        if p_before is None or p_close is None:
            continue
        rows.append({
            "category": m["category"],
            "p_before": p_before,
            "p_close": p_close,
            "drift": p_close - p_before,
            "realized": 1.0 if m["resolved_outcome"] == "YES" else 0.0,
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["p_before_bucket"] = pd.cut(
        df["p_before"], bins=[0, 0.15, 0.4, 0.6, 0.85, 1.0],
        include_lowest=True,
    )
    return (
        df.groupby("p_before_bucket", observed=True)
        .agg(n=("drift", "count"),
             mean_drift=("drift", "mean"),
             std_drift=("drift", "std"),
             realized_rate=("realized", "mean"))
        .reset_index()
    )


def write_report(path: str = "reports/phase0_summary.txt") -> None:
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cov = coverage()
    calib = calibration_probe()
    drift = late_drift_probe()
    with open(path, "w") as f:
        f.write("=== Phase 0 Summary ===\n\n")
        f.write(f"Markets total                : {cov.n_markets}\n")
        f.write(f"Closed                       : {cov.n_closed}\n")
        f.write(f"Excluded as holdout          : {cov.n_holdout_excluded}\n")
        f.write(f"Eligible & with price history: {cov.n_with_yes_prices}\n\n")
        f.write("Resolution balance (eligible):\n")
        f.write(json.dumps(cov.yes_no_balance, indent=2) + "\n\n")
        f.write("By category:\n")
        f.write(cov.by_category.to_string(index=False) + "\n\n")
        f.write("Calibration probe (24h before close, 10 bins):\n")
        f.write(calib.to_string(index=False) + "\n\n")
        f.write("Late drift probe (last 48h):\n")
        f.write(drift.to_string(index=False) + "\n")
    log.info("Report written to %s", path)
