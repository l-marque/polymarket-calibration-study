# Polymarket Calibration Study

A quantitative analysis of prediction market efficiency on Polymarket, with a backtested trading strategy.

**Status** : Research phase completed April 2026. Paper trading bot deployed on Railway since April 20, 2026.

---

## Key results

- **Dataset** : 99,999 resolved markets and 1.36M price observations collected via Polymarket Gamma API
- **H1 Calibration** : No classical favorite-longshot bias detected. A specific +10.7 cents miscalibration identified in crypto markets in the 0.50-0.60 price band (p = 0.004)
- **H2 Late drift** : Price drift between T-48h and T-24h is strongly informative in crypto (OR = 266), absent in sports
- **H3 Cross-market coherence** : Inconclusive
- **Trading strategy** : Short-YES on the identified bias, +18.8% ROI over 187 trades, Sharpe 2.83, out-of-sample 2026 outperforms 2025 training

Full analysis, methodology, and glossary in the working paper : [`paper/polymarket_working_paper_EN.pdf`](paper/polymarket_working_paper_EN.pdf) (French version also available).

---

## Preregistered hypotheses

All three hypotheses were committed to GitHub on April 14, 2026, before any statistical analysis :

- **H1** : Polymarket prices show systematic miscalibration in at least one decile.
- **H2** : The price drift between T-48h and T-24h carries predictive information beyond the price level.
- **H3** : Markets on the same underlying event move coherently.

Preregistration prevents reshaping hypotheses after looking at the data, a practice known as p-hacking.

---

## Methodology

- Murphy Brier score decomposition (Reliability / Resolution / Uncertainty)
- Exact binomial tests with Bonferroni correction
- Non-parametric bootstrap confidence intervals
- Nested logistic regressions with Wald and likelihood-ratio tests
- Within-cluster sign concordance for H3
- Out-of-sample validation with temporal split at January 1, 2026

---

## Repository structure

- `paper/` : Working paper in French and English (PDF)
- `notebooks/` : Five notebooks covering data exploration, the three hypotheses, and the trading bot backtest, with JSON verdicts per hypothesis
- `src/` : Python modules for data collection, feature engineering, backtesting
- `paper_trading/` : Live paper trading bot deployed on Railway
- `tests/` : Unit tests

---

## Installation

```bash
git clone https://github.com/l-marque/polymarket-calibration-study.git
cd polymarket-calibration-study
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

To reproduce the analysis, run the notebooks in order (01 to 05).

---

## Data-quality caveats

Three issues were identified and documented transparently in the working paper :

1. Volume field from the API is bucketed into ~4 discrete tiers, not continuous values
2. Category field is empty in the API response ; a rule-based slug classifier provides 76% coverage
3. An earlier SQL UPDATE polluted the holdout flag ; it was recomputed from raw end_ts

---

## Limitations

- The 99,999-market sample is the API pagination cap, not a complete historical enumeration
- The H1 identification sample partially overlaps with the backtest ; the 2026 test period is genuinely out-of-sample but only 3 months long
- The 0.5% slippage assumption holds for 1-USDC stakes but likely understates impact at scale
- Ten months is sufficient to detect a stable inefficiency but not to rule out regime shifts

---

## Reproducibility

All random seeds are fixed (`seed = 42`). The three hypotheses were preregistered before any statistical analysis.

---

## License

MIT

---

## Contact

Lucas Marque, École Centrale Méditerranée
lucas.marque@centrale-marseille.fr
