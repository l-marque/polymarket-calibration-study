"""
Phase 1: feature engineering.

Will produce, per market observation timestamp t:
- price_derivative_7d: d(YES price)/dt over last 7 days
- consensus_gap: YES price minus external consensus (e.g. polling, FRED)
- relative_liquidity: liquidity_usd normalized by category median at t
- category_one_hot
- macro_features_at_t: VIXCLS, GPRD, DXY, etc. at last ts <= t

CRITICAL anti-leakage rule, enforced by `as_of_join` below:
  Every external feature joined to a market sample MUST satisfy
      external.ts <= sample.ts
  No exceptions. The Phase 0 holdout flag is a backstop, this join is the
  primary defense.
"""
from __future__ import annotations
import pandas as pd


def as_of_join(
    samples: pd.DataFrame,
    series: pd.DataFrame,
    sample_ts_col: str = "obs_ts",
    series_ts_col: str = "ts",
    series_value_col: str = "value",
    suffix: str = "_macro",
) -> pd.DataFrame:
    """
    Backward-looking as-of join. For each row in `samples`, attach the most
    recent value from `series` such that series.ts <= samples.obs_ts.

    Implementation uses pandas.merge_asof with direction='backward'.
    Both inputs must be sorted by their ts column.
    """
    samples_sorted = samples.sort_values(sample_ts_col).copy()
    series_sorted = series.sort_values(series_ts_col).copy()
    out = pd.merge_asof(
        samples_sorted,
        series_sorted,
        left_on=sample_ts_col,
        right_on=series_ts_col,
        direction="backward",
        suffixes=("", suffix),
        allow_exact_matches=True,
    )
    return out


# To be implemented in Phase 1 once the analyst's strategy doc is finalized.
def build_features(market_id: str) -> pd.DataFrame:
    raise NotImplementedError("Phase 1 — implement after strategy design.")
