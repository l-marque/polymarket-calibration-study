# Phase 1 — Strategy design (preparatory)

> **Statut** : ce document est un **plan d'analyse et un cadre de décision conditionnel**, pas un set de stratégies validées.
> Les paramètres numériques (seuils, magnitudes, EV) doivent être **mesurés sur ton dataset Phase 0 réel** avant tout passage en Phase 2.
> Toute affirmation chiffrée ci-dessous est explicitement marquée `[à mesurer]` ou `[hypothèse à tester]`.

---

## 1. Méthodologie statistique

Pour les trois pistes annoncées, le pipeline est identique :

1. **Constituer l'échantillon hors-holdout** : `markets WHERE closed=1 AND holdout=0 AND resolved_outcome IN ('YES','NO')`.
2. **Split temporel walk-forward** : 6 fenêtres glissantes (train 6 mois / test 1 mois). Pas de cross-validation aléatoire — ça créerait du leakage.
3. **Tests de significativité** (avec correction de Bonferroni si on teste plusieurs déciles) :
   - Test du **chi²** : indépendance entre bin de prix prédit et résolution observée.
   - **Brier score par décile** : `BS_d = (1/n_d) Σ (p_i − y_i)²`. On compare à un benchmark "marché parfaitement calibré" via bootstrap (10 000 rééchantillonnages).
   - **t-test apparié** sur la miscalibration `(p̄_d − ȳ_d)` par décile.
4. **Seuil d'acceptation d'un biais** : effet stable sur ≥ 4/6 fenêtres walk-forward, p-valeur Bonferroni-corrigée < 0.01, magnitude économique > 2× les frais de transaction (voir §5).

---

## 2. Piste A — Calibration bias aux extrêmes (favorite-longshot)

### Hypothèse formelle
Soit `p` le prix YES à T-24h et `y ∈ {0,1}` la résolution. L'hypothèse est :
- **H_A1** : pour `p ∈ [0.85, 1.0)`, `E[y | p]` est significativement > p (favoris sous-évalués) **OU** < p (favoris sur-évalués). Le sens et la magnitude sont à mesurer.
- **H_A2** : pour `p ∈ (0.0, 0.15]`, miscalibration symétrique sur les longshots.

### Mesure
Code déjà fourni dans `data/explorer.py::calibration_probe()`. Il produit, par décile :

```
bin | n | mean_predicted | realized_yes_rate | brier | miscalibration
```

### Décision conditionnelle (à instancier après mesure)

```
Soit MIS_d la miscalibration mesurée sur le bin d'intérêt (ex. p ∈ [0.85, 0.95]).
Soit STD_d son écart-type (bootstrap).

Si |MIS_d| > 2 × STD_d ET |MIS_d| > 2 × frais_round_trip:
    → Edge exploitable
    → Direction du trade :
        Si MIS_d > 0  (marché surestime YES) → vendre YES (acheter NO)
        Si MIS_d < 0  (marché sous-estime YES) → acheter YES
Sinon :
    → Pas de trade sur ce bin.
```

### Dimensionnement Kelly
Pour un marché à prix `p`, payoff $1 si bonne direction, perte de la mise sinon, et probabilité réelle estimée `q = p − MIS_d` :

```
b = (1 - p) / p   si on achète YES   (cote décimale - 1)
f* = (b·q − (1−q)) / b   = (q − p) / (1 − p)   pour BUY YES
f* = (p − q) / p                                pour BUY NO

# On applique un facteur prudentiel (half-Kelly):
size_fraction = max(0, 0.5 × f*)
```

### Risques principaux et mitigation

| Risque | Mitigation |
|---|---|
| Biais de sélection sur les marchés à fort volume | Stratifier par catégorie + tertile de volume avant de conclure |
| Le biais disparaît si la liquidité augmente avec le temps | Walk-forward obligatoire ; si l'effet décroît sur les fenêtres récentes, le considérer mort |
| Frais de transaction grignotent l'edge | Imposer `\|edge\| > 2 × frais` comme filtre dur |
| Marchés à résolution douteuse (UMA dispute) | Exclure marchés `resolved_outcome IS NULL` ou `resolution_source` non standard |

### EV théorique par trade
`EV = q − p − frais` (en BUY YES). Concrètement, **si** la mesure révèle MIS = 3 cents sur le bin [0.85, 0.95] avec frais round-trip ≈ 1 cent, alors EV ≈ 2 cents par trade, soit ~2.5% du capital engagé. **Toujours `[à mesurer]`** — ne pas trader sur cette estimation sans confirmation empirique.

---

## 3. Piste B — Late resolution drift

### Hypothèse formelle
Pour un marché qui se résoudra YES, la trajectoire des prix sur les 48 dernières heures avant clôture présente une **dérive monotone vers 1**, plus rapide que ne le justifie l'arrivée de nouvelle information. (Symétrique pour NO.)

Concrètement : `Δp = p_close − p_T-48h` est conditionné sur `y` au-delà de ce que `p_T-48h` à lui seul prédit.

### Mesure
Code dans `data/explorer.py::late_drift_probe()`. Il faut compléter avec une régression :

```python
# pseudocode
import statsmodels.api as sm
y = df["realized"]
X = df[["p_before", "drift"]]
X = sm.add_constant(X)
logit = sm.Logit(y, X).fit()
# Tester si le coefficient de "drift" est significativement non nul
# APRÈS contrôle de p_before. Si oui → information dans la dérive.
```

### Décision conditionnelle

```
Soit β_drift le coefficient de dérive estimé (logit), σ_β son écart-type.

Si |β_drift| / σ_β > 2.5 (≈ p<0.01) ET le sens est consistant entre catégories :
    Stratégie : à T-24h, mesurer la dérive sur les 24h précédentes (T-48h → T-24h).
    Si dérive positive ET p_actuel < seuil_haut :
        → BUY YES, taille half-Kelly basée sur l'edge implicite par β_drift
    Symétrique pour dérive négative.

Sortie : à T-1h, ou sur stop-loss si le prix bouge contre nous de > 5 cents.
```

### Risques

| Risque | Mitigation |
|---|---|
| **Look-ahead leakage** : utiliser p_close pour entraîner et trader à T-24h | Imposer features ne contenant que des données ts ≤ T-24h. Test unitaire à écrire. |
| Survivorship bias des marchés liquides à T-48h | Filtrer `liquidity_usd > seuil` AVANT le split, pas après |
| Le drift reflète une fuite d'info légitime (insider) | C'est précisément ce qu'on veut exploiter, mais à conditionner sur l'existence d'un orderbook tradable à notre prix |

### EV théorique
Si `β_drift` est par exemple +1.5 (logit) avec σ=0.4, l'odds-ratio par cent de dérive est ≈ exp(0.015) ≈ 1.015, soit **typiquement [hypothèse : 1-3 cents d'edge par trade]** sur les marchés où la dérive est observée. Mesurer.

---

## 4. Piste C — Arbitrage cross-market

### Hypothèse formelle
Il existe des familles de marchés liés (ex. "X gagne l'élection présidentielle US 2028" et les marchés par État correspondants) où la somme des probabilités des sous-événements doit respecter une contrainte additive ou multiplicative (par ex. `P(X) = Σ P(X | État i) · P(État i)` sous indépendance ou avec corrélations connues).

Quand `Σ P_marché ≠ contrainte_théorique ± frais`, il y a une opportunité d'arbitrage.

### Statut
**Plus difficile à automatiser que A et B.** Nécessite de mapper les groupes de marchés (un travail manuel ou semi-automatique via les `tags` Gamma + `events`). Mon avis : à reporter en Phase 2 après que les biais A et B soient mesurés et tradés. Coder un détecteur naïf pour la Phase 1 est faisable mais risqué (faux positifs sur marchés mal taggés).

### Décision conditionnelle (squelette)

```
Pour chaque "event" Gamma contenant ≥ 2 marchés exclusifs :
    s = Σ p_yes_i
    Si |s − 1.0| > 2 × frais ET liquidité_min > seuil :
        → Trade : vendre les surévalués, acheter les sous-évalués
                  proportionnellement, capital = min(liquidités · 0.05)
        → Arbitrage borné, risque résiduel = corrélation des résolutions UMA
```

### Risques majeurs
- **Risque de résolution corrélée** : si UMA résout un marché en désaccord avec les autres, l'arbitrage perd. Voir le précédent du marché Trump-Ukraine 2025.
- **Risque de liquidité asymétrique** : on peut entrer mais pas sortir.
- **Frais cumulés** : sur un panier de 5 marchés, les frais aller-retour s'additionnent.

---

## 5. Pseudocode unifié de la fonction de décision

```python
@dataclass
class Decision:
    market_id: str
    side: Literal["BUY_YES", "BUY_NO", "NONE"]
    edge_cents: float       # edge net après frais, en cents
    size_usd: float         # taille en USDC, half-Kelly capped
    rationale: str          # quelle stratégie a déclenché
    expires_at: int         # timestamp Unix au-delà duquel l'ordre meurt

def decide(market: MarketState, now_ts: int) -> Decision:
    # Pré-filtres durs
    if market.liquidity_usd < MIN_LIQUIDITY: return NONE
    if market.spread > MAX_SPREAD:           return NONE
    if market.time_to_close < MIN_TTC:       return NONE

    # Calcul de l'edge selon les stratégies activées (mesurées Phase 1)
    edges = []
    if STRAT_A_ACTIVE:
        e = compute_calibration_edge(market.price, market.category)
        if abs(e) > 2 * ROUND_TRIP_FEE:
            edges.append(("calibration", e))
    if STRAT_B_ACTIVE:
        e = compute_drift_edge(market.price_history)
        if abs(e) > 2 * ROUND_TRIP_FEE:
            edges.append(("drift", e))
    # (Strat C en Phase 2)

    if not edges: return NONE

    # On prend l'edge dominant ; si plusieurs vont dans le même sens, on combine
    # avec un poids inverse à la variance estimée de chaque edge.
    rationale, edge = max(edges, key=lambda x: abs(x[1]))
    side = "BUY_YES" if edge > 0 else "BUY_NO"

    # Kelly fraction
    p = market.price if side == "BUY_YES" else 1 - market.price
    q = p + abs(edge)                      # prob. réelle estimée
    f_kelly = (q - p) / (1 - p)            # full Kelly
    size_usd = min(
        BANKROLL * 0.5 * f_kelly,           # half-Kelly
        BANKROLL * MAX_POSITION_FRACTION,   # plafond dur (ex. 5%)
        market.depth_at_price * 0.3,        # ne pas manger > 30% du book
    )
    if size_usd < MIN_TICKET: return NONE

    return Decision(
        market_id=market.id, side=side,
        edge_cents=edge*100, size_usd=size_usd,
        rationale=rationale,
        expires_at=now_ts + ORDER_TTL_SEC,
    )
```

---

## 6. Constantes à fixer empiriquement (Phase 1, après mesure)

| Constante | Valeur initiale plausible | Méthode de calibration |
|---|---|---|
| `ROUND_TRIP_FEE` | 0.01 (1 cent) | Mesurer en paper trading sur 50 trades |
| `MIN_LIQUIDITY` | 10 000 USD | Tertile inférieur de l'échantillon Phase 0 |
| `MAX_SPREAD` | 0.02 (2 cents) | Quantile 75% des spreads observés |
| `MIN_TTC` | 6h | Évite les marchés en cours de résolution UMA |
| `MAX_POSITION_FRACTION` | 0.05 | Décision de risk management, pas empirique |
| `ORDER_TTL_SEC` | 600 | Évite les ordres "fantômes" si le marché a bougé |

---

## 7. Critères pour passer à la Phase 2 (modèle)

- Au moins **1 stratégie** parmi A, B, C présente un edge mesuré significatif et stable sur les fenêtres walk-forward.
- L'EV par trade après frais simulés est > 1.5%.
- La fonction `decide()` ci-dessus produit un signal dans ≥ 5% des marchés observés (sinon, trop sélectif pour être tradable).

Si ces critères ne sont pas remplis : **ne pas passer en Phase 2**. C'est aussi un résultat valide. Beaucoup de stratégies de calibration semblent prometteuses sur le papier puis disparaissent dès qu'on retire le data-snooping.
