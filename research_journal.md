# Research Journal

> Weekly progress on the Polymarket Calibration Study.
> Format inspired by Lakens' preregistration practices.

---

## Week 1 — April 14-20, 2026 — Project Setup and Phase 0 Launch

### Objectives
- Design the three-phase architecture (collection → exploration → strategy).
- Implement a rate-limit-compliant, anti-leakage data pipeline.
- Pre-register the three hypotheses to be tested.

### Pre-registered hypotheses

**H1 (favorite-longshot bias).** For closed binary markets, the realized YES rate in the top decile of price (`p >= 0.9`) differs from the mean predicted price by more than 2% after correcting for market heterogeneity. Symmetric hypothesis for the bottom decile. Test: decile-level chi-squared on `(p_bin, outcome)` with Bonferroni correction.

**H2 (late resolution drift).** In a logit regression of realized outcome on price at T-48h and drift between T-48h and T-24h, the coefficient on drift is significantly non-zero after controlling for price level. Test: Wald test on the drift coefficient, clustered standard errors by market.

**H3 (cross-market arbitrage).** For Gamma events containing two or more mutually exclusive binary markets, the sum of YES prices deviates from 1.0 by more than twice the round-trip transaction cost in at least 5% of observed events. Test: empirical distribution of deviations, one-sample t-test against zero.

### Work completed
- Verified current Polymarket API structure (Gamma + CLOB, April 2026).
- Designed the SQLite schema with `holdout` flag for temporal anti-leakage.
- Implemented the async collector with per-endpoint token buckets respecting documented rate limits (300/10s on `/markets`, 500/10s on `/events`).
- Documented known limitations of the `/prices-history` endpoint: for closed markets, fidelity below 720 minutes frequently returns empty arrays (see py-clob-client issue #216). Implemented automatic fallback.
- Selected FRED macroeconomic controls: VIXCLS, GPRD, DTWEXBGS, DCOILWTICO, DGS10, DFF, T10YIE, STLFSI4.
- Wrote 13 unit tests, including one that verifies holdout markets cannot leak into training queries.

### Phase 0 collection results (April 18)

**Market metadata collection:**
- Total markets fetched: **99,999** (hit `max_pages=200 × limit=500` ceiling)
- All closed binary markets with valid YES/NO tokens
- 32,379 (32%) flagged as holdout (resolved within last 30 days)
- 24,067 markets with volume > $10,000 selected for price history collection

**Price history collection (initial validation on top 100 by volume):**
- 30,491 price points collected
- Average ~305 points per market (~150 per YES/NO token at 12h fidelity)
- Pipeline validated, full 24k-market collection launched

### Data quality observations

**Volume bucketing.** Distribution of volumes shows suspicious step structure: count of markets with volume > $1k is identical to count > $5k (58,926), and count > $10k identical to count > $50k (24,067). Suggests Gamma's `volume` field is rounded or bucketed by the API. Decision: use $10k as the inclusion threshold for now, but flag this for further investigation before relying on `volume_total_usd` as a continuous predictor in any model.

**Pagination behavior.** Gamma API appears to ignore the `start_date_min` filter when also filtering on `closed=true`, returning the full historical dataset rather than the requested 12-month window. Will require a fix in `collect_markets` (see TODO).

############################################################################################################################################
### Phase 0 exploration complete (April 19)


### Performance optimization (April 19, morning)

Initial T-24h price extraction used a nested Python loop over markets and
tokens, resulting in 3+ minutes of execution for 65k markets against 1.36M
price points. Refactored to use `pandas.merge_asof` with `by="token_id"` and
`direction="backward"`, reducing runtime to <5 seconds (40× speedup).

This is the canonical pattern for financial time-series as-of joins: each
observation on the left side is matched to the most recent observation on
the right side where `right.ts <= left.target_ts`, preserving the
anti-look-ahead discipline.

**Final dataset characterization:**
- 99,999 markets collected; 67,081 in clean analysis set
- 1,361,079 price points across 46,930 tokens (97.5% coverage)
- 10,830 FRED macro observations across 8 series
- 11,340 markets with usable T-24h YES price (after duration ≥24h filter)

**Key statistical findings (preview of H1):**
- Correlation(price_T24h, outcome_YES) = 0.5408
- Overall Brier score = 0.1698 (baseline: 0.25 for random; 0.0 for perfect)
- Price distribution is trimodal: pics at 0.0 (~2k), 0.5 (~3k, dominated by
  crypto), and 1.0 (~400). Middle distribution is nearly flat.
- Decile-level calibration suggests possible favorite-longshot asymmetry:
  bottom decile realized 2% vs predicted ~5%, top decile realized 87% vs
  predicted ~85%. To be formally tested in notebook 02.

**Performance optimization:**
- Refactored T-24h price extraction from nested Python loops to
  `pandas.merge_asof`. Runtime reduced from 3min+ to <5 seconds (40x).

**Data quality issues identified:**
- 2,731 markets exactly at price 0.50 at T-24h (suspected illiquidity)
- 764 markets with zero or negative duration
- Volume field bucketing confirmed visually (CDF shows 4 plateaus)

### Updated TODOs
- [ ] Fix `DB_PATH` in `config/settings.py` to anchor at project root
- [ ] Fix `collect_markets` pagination (hit max_pages ceiling)
- [ ] Refactor holdout flag handling to never be mutated post-collection
- [ ] Investigate the 2,731 markets stuck at 0.50 (liquidity filter ?)




### TODOs (carry-over to Week 2)
- [ ] Fix `collect_markets` pagination: replace `empty_streak` stop condition with explicit date-based termination.
- [ ] Verify whether Gamma's `start_date_min` parameter is documented or has been deprecated.
- [ ] Investigate the volume bucketing pattern (API behavior vs raw on-chain data).

- [ ] Fix `config/settings.py`: `DB_PATH` uses `Path("./polymarket.db")` which
      resolves relative to the working directory. This breaks notebooks in
      `notebooks/` where cwd is the subfolder, not the project root. Should be
      anchored to `Path(__file__).parent.parent / "polymarket.db"` instead.


### Critical data cleaning issue (April 19, evening)

The `holdout` flag in the `markets` table no longer represents its original
semantics ("resolved within last 30 days"). The SQL `UPDATE` statements used
to select the volume-filtered subset for price collection have polluted the
flag, mixing in "low volume" with "recent". Diagnostic in
`notebooks/01_data_exploration.ipynb` shows:
- 76% of markets <30d old are holdout (correct anti-leakage behavior)
- 77% of markets 30-90d old are also holdout (INCORRECT, should be 0%)
- 69% of markets >365d old are holdout (INCORRECT, should be 0%)

Mitigation: in-notebook recomputation of `truly_holdout` and `analysis_set`
columns from raw data. The base table is preserved for auditability.

To fix in Week 2:
- [ ] Refactor `data/storage.py` to never mutate the `holdout` flag after
      initial computation. Volume-based filtering should use a separate flag
      like `selected_for_price_collection`.






### Open questions
- How stable is the distribution of categories across time? If political markets dominated 2024 and are now a minority, category effects may be confounded with time effects.
- Fee structure changed on March 31, 2026 (per-market `feeSchedule` object). Need to account for this in any backtest of pre-2026 data.

### Plan for next week
- Run full price collection on the 24k-market sample (estimated 3-4h).
- Produce notebook `01_data_exploration.ipynb` with descriptive statistics.
- Produce notebook `02_calibration_analysis.ipynb` testing H1.

---