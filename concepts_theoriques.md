# Concepts théoriques — Polymarket Calibration Study

> Document de référence rassemblant les concepts mathématiques, statistiques
> et méthodologiques utilisés dans le projet. Chaque concept est expliqué
> simplement avec un exemple concret, destiné à la révision pour entretiens.

---

## Table des matières

- [1. Vocabulaire de base](#1-vocabulaire-de-base)
- [2. Théorie statistique](#2-théorie-statistique)
- [3. Méthodologie scientifique](#3-méthodologie-scientifique)
- [4. Finance quantitative](#4-finance-quantitative)


---

## 1. Vocabulaire de base

### Bin (décile, quantile)

**Définition :** un "bin" est un intervalle utilisé pour découper une variable
continue en morceaux. Un "décile" est un bin qui contient 10% des observations.

**Exemple concret :** on a 11 340 marchés avec des prix entre 0 et 1. On les
découpe en 10 bins : 0.0-0.1, 0.1-0.2, ..., 0.9-1.0. Dans le bin 0.8-0.9,
on a 245 marchés.

**Pourquoi on utilise ça :** pour étudier si une relation varie selon la valeur
d'une variable. Si tous les marchés dans un bin donné se comportent de la même
façon, on peut comparer les bins entre eux.

---

### Base rate

**Définition :** la proportion de fois où un événement se produit dans une
population, indépendamment de tout prédicteur.

**Exemple concret :** dans notre dataset, le taux YES global est 41.3%. C'est
la base rate. Si je prédis toujours NO sans regarder les données, j'ai 58.7%
de chances d'avoir raison.

**Piège classique : base rate fallacy.** Confondre "probabilité conditionnelle"
et "base rate". Si un test médical détecte une maladie à 99%, mais la maladie
touche 1 personne sur 10 000, un test positif a ~99% de chances d'être un
faux positif.

---

### Brier score

**Définition :** mesure d'erreur pour prédictions probabilistes binaires.
BS = moyenne de (prédiction − réalité)². La réalité est 0 ou 1.

**Exemple concret :** je prédis 80% YES, le marché se résout YES.
Erreur = (0.8 − 1.0)² = 0.04. Je prédis 80% et ça finit NO : erreur = 0.64.

**Références :**
- Parfait = 0
- Aléatoire pur = 0.25
- "Toujours 0.5" = 0.25
- Pire qu'aléatoire = > 0.25
- **Notre Brier = 0.17 → meilleur qu'aléatoire, pas parfait**

---

## 2. Théorie statistique

### Décomposition de Murphy du Brier score

**Formule :** `Brier = Reliability − Resolution + Uncertainty`

**Reliability (fiabilité / calibration) :** mesure si tes prédictions
correspondent à la fréquence observée. "Quand tu dis 30%, ça arrive 30%
du temps ?" Parfait = 0.

**Resolution (pouvoir discriminant) :** mesure si tu fais varier tes
prédictions selon la difficulté. Plus c'est haut, mieux c'est.

**Uncertainty (incertitude intrinsèque) :** `p × (1 − p)` où p est la
base rate. Maximum = 0.25 à p = 0.5. Indépendante du prédicteur.

**Analogie des 2 météorologistes :**
- **Alice** dit toujours 30% → parfaitement calibrée mais inutile (Resolution = 0)
- **Bob** dit 0% ou 100% → très discriminant mais un peu mal calibré
- Les deux peuvent avoir le même Brier global, mais la décomposition
  montre où est le problème

**Pourquoi c'est utile :** si ton Brier est haut, tu sais s'il faut
améliorer la calibration (Reliability) ou le pouvoir de discrimination
(Resolution). Deux problèmes, deux solutions.

---

### Test binomial / chi² par bin

**Question posée :** dans mon bin avec 245 marchés, prix moyen 0.85, j'observe
87% d'YES réels. Est-ce significativement différent de 0.85 ?

**Test binomial :** sous H0 (calibration parfaite), chaque marché a probabilité
p = 0.85 de se résoudre YES. Le nombre d'YES suit une loi binomiale B(245, 0.85).
On calcule P(X ≥ 213) où 213 = 87% × 245.

**Intuition :** si cette probabilité est très petite (< 0.005 après Bonferroni),
l'hypothèse de calibration parfaite est rejetée pour ce bin.

---

### Correction de Bonferroni

**Problème résolu :** le multi-tests.

**Exemple du danger :** je teste 10 déciles au seuil α = 0.05. Sous H0 (aucun
biais), la probabilité de trouver au moins 1 faux positif = 1 − 0.95^10 = 40%.
**Je publie un faux résultat 40% du temps.**

**Solution Bonferroni :** utiliser un seuil α/k pour chaque test individuel.
Pour 10 tests à α = 0.05 : seuil individuel = 0.005.

**Propriétés :**
- Contrôle le **FWER** (Family-Wise Error Rate) = P(au moins 1 faux positif)
- Très conservateur (réduit la puissance)

**Alternative : Benjamini-Hochberg.** Contrôle le FDR (False Discovery Rate).
Accepte quelques faux positifs en échange de plus de puissance. Standard en
génomique quand on teste 10 000 gènes.

---

### Bootstrap

**Définition :** méthode de rééchantillonnage pour estimer la distribution
d'échantillonnage d'une statistique sans supposer de loi paramétrique.

**Algorithme concret :**
1. J'ai un échantillon de 245 marchés, je veux un IC sur le taux YES
2. Je tire **avec remise** 245 marchés dans mon échantillon
3. Je calcule le taux YES sur ce rééchantillon
4. Je répète 10 000 fois → 10 000 taux YES simulés
5. Quantiles 2.5% et 97.5% → IC à 95%

**Pourquoi c'est puissant :**
- **Non-paramétrique** : ne suppose rien sur la distribution
- **Robuste** : marche sur petits échantillons et distributions asymétriques
- **Flexible** : peut estimer l'IC de n'importe quelle statistique (médiane,
  corrélation, ratio, tout)
- **Auto-contraint** : ne donnera jamais une proba < 0 ou > 1

**Limite :** si l'échantillon initial n'est pas représentatif de la population,
le bootstrap hérite du biais. "Bootstrap ne crée pas d'information, il quantifie
celle qui existe."

---

## 3. Méthodologie scientifique

### Préregistrement (Preregistration)

**Définition :** déclarer publiquement ses hypothèses et méthodes AVANT de
regarder les données.

**Pourquoi c'est critique :** sans préregistrement, on tombe dans le
**data snooping** (aussi appelé p-hacking). On teste 50 hypothèses, on publie
les 3 significatives, on prétend qu'on n'avait que celles-là en tête.

**Notre préregistrement :** H1, H2, H3 dans `research_journal.md` datées du
14-20 avril 2026, avant toute analyse statistique.

**Référence clé :** Lakens, D. (2019). "The Value of Preregistration for
Psychological Science."

---

### Data leakage (look-ahead bias)

**Définition :** utiliser une information dans les features qui n'était pas
disponible au moment de la décision.

**Exemple concret :** pour tester H1, on prend le prix à T-24h et on teste
s'il prédit l'outcome. Si par erreur on prenait le prix à T-12h, on
"trichait" : un trader n'aurait pas eu cette info 24h avant.

**Comment on se protège :**
- Tous les timestamps sont explicites
- `merge_asof` avec `direction="backward"` garantit qu'on ne prend que des
  prix antérieurs au timestamp cible
- Les marchés résolus < 30 jours sont holdout (pour les futurs notebooks de
  validation)

---

### Walk-forward validation

**Définition :** technique de validation pour séries temporelles. Au lieu de
faire du K-fold aléatoire, on split dans l'ordre du temps.

**Exemple concret :** 6 fenêtres de 7 mois chacune (6 train + 1 test). On
entraîne sur les 6 premiers mois, on teste sur le 7e. Puis on glisse : train
sur les mois 2-7, test sur le 8e. Etc.

**Pourquoi on ne fait PAS du K-fold aléatoire :** ça créerait du data leakage
temporel (on entraînerait avec des données du futur pour prédire le passé).

---

### Analysis set vs holdout vs test

**Analysis set :** les données qu'on utilise pour explorer, poser des
hypothèses, développer des méthodes.

**Holdout :** données mises de côté AVANT toute analyse, touchées seulement
à la toute fin pour validation finale.

**Test walk-forward :** séparé de l'holdout. Sert à valider les choix de
modélisation pendant le développement.

**Règle d'or :** on ne touche JAMAIS le holdout avant la validation finale,
sous aucun prétexte. Sinon les biais de sélection reviennent par la petite
porte.

---

## 4. Finance quantitative

### Favorite-longshot bias

**Définition :** biais systématique où les marchés de paris sous-évaluent
les favoris et sur-évaluent les outsiders.

**Origine historique :** Griffith (1949) l'a documenté sur les paris hippiques
américains. Présent depuis dans : sports betting, loteries, options out-of-the-money.

**Intuition économique :** les parieurs préfèrent les "gros gains" (longshots)
à l'espérance négative, et sous-investissent dans les paris "ennuyeux" mais
rentables (favoris).

**Notre test :** le bin 0.85-0.95 montre 87% d'YES réels vs ~85% prédits.
Pourrait indiquer un FLB inversé (favoris sous-évalués), à confirmer
statistiquement.

---

### Kelly criterion

**Formule :** `f* = (bq − p) / b` où
- p = probabilité de gagner
- q = 1 − p = probabilité de perdre
- b = gain net sur une victoire (odds décimales − 1)
- f* = fraction optimale du capital à miser

**Exemple :** probabilité réelle 60%, prix de marché 50%. Edge = 10 cents.
Odds = (1 − 0.5)/0.5 = 1. f* = (1 × 0.6 − 0.4) / 1 = 0.20 = mise 20% du capital.

**En pratique :** on utilise **half-Kelly** (f*/2) pour réduire la variance
et le risque de ruine. Sacrifier 25% d'espérance pour 50% moins de volatilité.

---

### Spread, slippage, frais de transaction

**Spread :** différence entre meilleur bid et meilleur ask. Coût immédiat
d'entrer et sortir d'une position.

**Slippage :** différence entre le prix qu'on pensait obtenir et le prix
réellement exécuté. Plus l'ordre est gros, plus le slippage est important.

**Frais Polymarket :** 2% sur résolution pour la plupart des marchés
(peut varier selon feeSchedule depuis mars 2026).

**Règle pour la stratégie :** edge théorique doit être > 2 × frais aller-retour
pour que le trade soit rentable après coûts.

---

## Notes pour l'enrichissement

À ajouter au fur et à mesure des notebooks :
- [ ] Régression logistique et odds ratios (notebook 02)
- [ ] Clustered standard errors (notebook 03)
- [ ] Calibration curves et reliability diagrams (notebook 02)
- [ ] Platt scaling et isotonic regression (notebook 04)
- [ ] Metrics de classification : precision, recall, AUC-ROC
- [ ] Sharpe ratio, Sortino, max drawdown (backtest)
- [ ] Cross-sectional vs time-series regression


### Régression logistique

**Problème résolu :** tester l'effet de plusieurs variables simultanément
sur une issue binaire (0/1), en isolant l'effet propre de chaque variable.

**Formule :**

$$P(Y=1 | X_1, ..., X_k) = \frac{1}{1 + e^{-(\beta_0 + \beta_1 X_1 + ... + \beta_k X_k)}}$$

Les coefficients $\beta_i$ mesurent l'effet de chaque variable **après
contrôle** des autres.

**Exemple :** on veut savoir si la dérive de prix prédit l'outcome YES,
au-delà du niveau de prix lui-même. On régresse :

$$P(Y=1) = \sigma(\beta_0 + \beta_1 \cdot \text{prix} + \beta_2 \cdot \text{dérive})$$

Test H2 = tester si $\beta_2 \neq 0$.

**Différence avec test binomial :**
- Test binomial : 1 variable, 1 hypothèse par test
- Régression logistique : plusieurs variables, chaque coefficient est testé
  séparément en contrôlant les autres

**Analogie du café et de l'infarctus :**
Si les buveurs de café ont plus d'infarctus, est-ce le café ou le tabac
(confondant) ? Une régression logistique avec café ET tabac comme prédicteurs
permet d'isoler l'effet propre du café après contrôle du tabac.

---

### Odds et odds ratio

**Odds (cote) :** transformation de la probabilité qui va de 0 à l'infini
au lieu de 0 à 1.

$$\text{odds}(p) = \frac{p}{1-p}$$

**Exemples :**
- p = 0.5 → odds = 1 (50/50)
- p = 0.75 → odds = 3 (3 contre 1)
- p = 0.10 → odds = 0.111 (1 contre 9)

**Pourquoi les odds sont utiles :** elles ne sont pas bornées par 1. On peut
leur appliquer des transformations multiplicatives sans risque de dépasser
les probabilités valides.

**Odds ratio (OR) :** $OR = e^\beta$ où $\beta$ est le coefficient logit.

**Interprétation :** facteur multiplicatif des odds quand la variable augmente
de 1 unité.

- OR = 1 : aucun effet
- OR = 2 : l'odds double (variable augmente de 1)
- OR = 0.5 : l'odds est divisée par 2 (effet protecteur)

**Règle de significativité :** si l'intervalle de confiance à 95% de l'OR
ne contient pas 1, l'effet est significatif au seuil α = 0.05.

**Exemple numérique pour H2 :** si on trouve $\beta_2 = 1.5$, alors
$OR = e^{1.5} = 4.48$. Pour une variation réaliste de dérive de +0.10,
l'effet multiplicatif sur l'odds est $e^{1.5 \times 0.10} = 1.16$ (soit +16%).

**Pourquoi les statisticiens adorent l'OR :**
1. Interprétation multiplicative intuitive
2. Symétrie : OR=2 ↔ OR=0.5 (inverse)
3. Indépendant du baseline (contrairement aux différences absolues)

---