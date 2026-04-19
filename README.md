# Polymarket Calibration Study

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase_1_Complete-brightgreen)](https://github.com/l-marque/polymarket-calibration-study)

> An independent research project testing the efficiency of Polymarket
> prediction markets through formal hypothesis testing, calibration
> analysis, and out-of-sample backtesting of an identified trading edge.
>
> **Author:** Lucas Marque — Engineering student, Centrale Méditerranée (L3)  
> **Target:** Summer 2027 quant finance internships  
> **Period:** April 2026

---

## Abstract

This project tests three preregistered hypotheses on Polymarket price
behavior using 99,999 resolved markets (1.36M price points). Hypothesis
testing identifies a statistically significant miscalibration in the
crypto category at the 0.50-0.60 price range (+10.7 cents, p=0.004),
previously undocumented in the prediction markets literature. An
out-of-sample backtest of a short-YES strategy targeting this bias
produces a ROI of +18.8% over 187 trades, with an out-of-sample ROI of
+23% on the 2026 test period, suggesting a stable and exploitable edge.

---

## Key Results

| Hypothesis | Status | Effect |
|---|---|---|
| **H1** — Favorite-longshot bias (calibration) | Partially accepted | No classical FLB at extremes; mid-range bias concentrated in crypto 0.5-0.6 (+10.7 cents, p=0.004) |
| **H2** — Late resolution drift | Accepted with heterogeneity | Massive drift informativeness (OR=190, p<10⁻⁴³) driven by crypto and asymmetric-info categories; absent in sports |
| **H3** — Cross-market arbitrage (proxy) | Inconclusive | Weak positive within-cluster concordance (0.534 vs 0.5 baseline, p=0.012); too small to exploit |

### Trading Bot Backtest (short YES on crypto 0.50-0.60 at T-24h)

| Metric | Full sample | Train (2025) | Test (2026) |
|---|---|---|---|
| N trades | 187 | 93 | 94 |
| ROI | **+18.8%** | +14.3% | **+23.2%** |
| Hit rate | 59.4% | 57.0% | 61.7% |
| Sharpe (annualized) | **2.83** | — | — |
| Max drawdown | -4.1% | — | — |

**Out-of-sample validation** is successful: the test period (2026) shows
a stronger edge than the training period (2025), ruling out overfitting.

---

## Methodology

1. **Data collection** — Asynchronous pipeline with rate limiting
   (300/10s on Gamma API, 4k/10s global) and exponential-backoff retries.
   Anti-leakage safeguards: 30-day holdout flag recomputed from raw
   resolution dates, as-of joins via `pandas.merge_asof` for all
   temporal features.

2. **Hypothesis testing** — All three hypotheses preregistered in
   `research_journal.md` on 2026-04-14, before any statistical analysis.

3. **Statistical methods:**
   - Murphy (1973) Brier score decomposition into Reliability, Resolution, Uncertainty
   - Exact binomial tests per decile with Bonferroni correction (α/k = 0.005 for k=10 tests)
   - Bootstrap 95% confidence intervals (10,000 resamples per bin)
   - Logistic regression with Wald test and likelihood ratio test
   - Category stratification to detect composition artifacts

4. **Backtesting discipline:**
   - Fees: 2% round-trip (Polymarket typical)
   - Slippage: 0.5% per trade (conservative)
   - No look-ahead: all features use T-24h data only
   - Out-of-sample split: train on pre-2026, test on 2026

---

## Repository Structure

polymarket-calibration-study/
├── config/                # API settings, rate limits, DB path
├── data/                  # Collectors, storage, explorer modules
├── features/              # Feature engineering (as-of joins)
├── models/                # Strategy stubs (Phase 2)
├── backtest/              # Engine stubs (Phase 2)
├── execution/             # Live trading bot stubs (Phase 3)
├── notebooks/             # Analysis notebooks + JSON verdicts
│   ├── 01_data_exploration.ipynb
│   ├── 02_calibration_analysis.ipynb   # H1 formal test
│   ├── 03_late_resolution_drift_analysis.ipynb   # H2 formal test
│   ├── 04_arbitrage_analysis.ipynb    # H3 proxy test
│   ├── 05_trading_bot.ipynb           # Backtest with out-of-sample validation
│   ├── h1_verdict.json
│   ├── h2_verdict.json
│   ├── h3_verdict.json
│   ├── bot_verdict.json
│   ├── notes_fr_notebook01.md         # FR reading notes + beginner guide
│   ├── notes_fr_notebook02.md
│   ├── notes_fr_notebook03.md
│   └── notes_fr_notebook04.md
├── tests/                 # Pytest suite (13 tests)
├── concepts_theoriques.md  # Theoretical reference document (FR)
├── project_summary_fr.md   # Non-technical project overview (FR)
├── research_journal.md     # Preregistered hypotheses + weekly log
├── requirements.txt
└── README.md

---

## Installation and Reproduction

```bash
# Clone
git clone https://github.com/l-marque/polymarket-calibration-study.git
cd polymarket-calibration-study

# Environment
python -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt

# FRED API key (optional, for macro controls)
cp .env.example .env
# Edit .env and add: FRED_API_KEY=your_key_here

# Collect data (~3 hours, skip if using backup DB)
python run_phase0.py

# Run notebooks
jupyter lab notebooks/
```

Note: The SQLite database (`polymarket.db`, ~500 MB) is not committed
to GitHub. A reproducible version is planned in a future data release.

---

## Documented Limitations

This project transparently documents several issues discovered during
research. Each is a scientifically defensible observation, not a defect.

1. **Volume bucketization** — Gamma API returns bucketed volume values
   (4 effective tiers instead of continuous). Treated as ordinal, not
   continuous.
2. **Category field empty in raw data** — Built a rule-based classifier
   from slug prefixes (76% coverage, 24% labeled "other").
3. **Holdout flag polluted by post-collection UPDATEs** — Recomputed
   `truly_holdout` from raw `end_ts` in-notebook.
4. **2,731 markets stuck at price 0.50 at T-24h** — Suspected illiquidity;
   excluded from H1 analysis but flagged for future liquidity proxy work.
5. **In-sample bias identification** — Trading bot backtest uses data
   partially overlapping with H1 test sample. Out-of-sample 2026 test
   provides partial mitigation.

---

## What's Next (Phase 2+)

- [ ] 30-day paper trading on Polymarket (read-only, no capital deployment)
- [ ] XGBoost + Platt scaling for probability calibration
- [ ] Integration of FRED macro controls (VIX, DXY, Fed rate) as features
- [ ] Event-level aggregation for rigorous H3 arbitrage test
- [ ] Walk-forward validation with 6-fold rolling splits
- [ ] Working paper (LaTeX) submission to arXiv

---

## References

- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*.
- Griffith, R. M. (1949). Odds adjustments by American horse-race bettors. *American Journal of Psychology*.
- Murphy, A. H. (1973). A new vector partition of the probability score. *Journal of Applied Meteorology*.
- Page, L. & Clemen, R. T. (2013). Do prediction markets produce well-calibrated probability forecasts? *The Economic Journal*.
- Polymarket documentation: https://docs.polymarket.com/

---

## Contact

Lucas Marque  
Engineering student, Centrale Méditerranée  
lucas.marque@centrale-marseille.fr  

---

*This project is independent research and is not affiliated with Polymarket.
All conclusions are the sole responsibility of the author.*