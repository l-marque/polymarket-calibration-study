\# Research Journal



> Weekly progress on the Polymarket Calibration Study.

> Format inspired by Lakens' preregistration practices.



\---



\## Week 1 — April 14-20, 2026 — Project Setup and Phase 0 Launch



\### Objectives

\- Design the three-phase architecture (collection → exploration → strategy).

\- Implement a rate-limit-compliant, anti-leakage data pipeline.

\- Pre-register the three hypotheses to be tested.



\### Pre-registered hypotheses



\*\*H1 (favorite-longshot bias).\*\* For closed binary markets, the realized YES

rate in the top decile of price (`p >= 0.9`) differs from the mean predicted

price by more than 2% after correcting for market heterogeneity. Symmetric

hypothesis for the bottom decile. Test: decile-level chi-squared on

`(p\_bin, outcome)` with Bonferroni correction.



\*\*H2 (late resolution drift).\*\* In a logit regression of realized outcome on

price at T-48h and drift between T-48h and T-24h, the coefficient on drift is

significantly non-zero after controlling for price level. Test: Wald test on

the drift coefficient, clustered standard errors by market.



\*\*H3 (cross-market arbitrage).\*\* For Gamma events containing two or more

mutually exclusive binary markets, the sum of YES prices deviates from 1.0 by

more than twice the round-trip transaction cost in at least 5% of observed

events. Test: empirical distribution of deviations, one-sample t-test against

zero.



\### Work completed this week

\- Verified current Polymarket API structure (Gamma + CLOB, April 2026).

\- Designed the SQLite schema with `holdout` flag for temporal anti-leakage.

\- Implemented the async collector with per-endpoint token buckets respecting

&#x20; documented rate limits (300/10s on `/markets`, 500/10s on `/events`).

\- Documented known limitations of the `/prices-history` endpoint: for closed

&#x20; markets, fidelity below 720 minutes frequently returns empty arrays (see

&#x20; py-clob-client issue #216). Implemented automatic fallback.

\- Selected FRED macroeconomic controls: VIXCLS (risk appetite), GPRD (daily

&#x20; Geopolitical Risk Index, Caldara-Iacoviello), DTWEXBGS (USD broad),

&#x20; DCOILWTICO (WTI), DGS10 (10y Treasury), DFF (Fed funds), T10YIE (breakeven

&#x20; inflation), STLFSI4 (financial stress).

\- Wrote 13 unit tests, including one that verifies holdout markets cannot

&#x20; leak into training queries.



\### Open questions

\- How stable is the distribution of categories across time? If political

&#x20; markets dominated 2024 and are now a minority, category effects may be

&#x20; confounded with time effects.

\- Fee structure changed on March 31, 2026 (per-market `feeSchedule` object).

&#x20; Need to account for this in any backtest of pre-2026 data.



\### Plan for next week

\- Run full collection for the last 12 months of closed markets.

\- Produce notebook `01\_data\_exploration.ipynb` with descriptive statistics.

\- Produce notebook `02\_calibration\_analysis.ipynb` testing H1.



\---

