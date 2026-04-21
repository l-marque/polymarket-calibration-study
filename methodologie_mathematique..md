# Méthodologie mathématique du projet

Ce document explique en détail les concepts mathématiques utilisés dans le projet Polymarket Calibration Study. Pour chaque concept, on donne :

1. **L'intuition** : une explication accessible sans formule
2. **La formule** : la définition mathématique rigoureuse
3. **L'usage dans le projet** : où et pourquoi on l'a utilisé
4. **Question d'entretien type** : ce qu'un recruteur pourrait demander, avec la réponse

---

## 1. Brier score et sa décomposition

### Intuition

Le Brier score mesure à quel point une prévision probabiliste est bonne. Imagine un météorologue qui annonce chaque jour "il y a X% de chances qu'il pleuve demain". Le Brier score regarde, sur un grand nombre de jours, si les pourcentages annoncés correspondent à la fréquence réelle de pluie.

Un météorologue parfait aurait un Brier de 0. Un météorologue qui répond "50% tous les jours" aurait un Brier de 0.25 (le maximum pour des événements binaires équilibrés).

### Formule

Pour une prévision $p_i \in [0, 1]$ et un outcome réalisé $y_i \in \{0, 1\}$ sur $N$ événements :

$$\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2$$

### Décomposition de Murphy (1973)

Le Brier score se décompose **exactement** en trois termes :

$$\text{Brier} = \text{Reliability} - \text{Resolution} + \text{Uncertainty}$$

Avec :

- **Reliability** : mesure la miscalibration. Pour chaque bin de prévision, on compare la probabilité annoncée à la fréquence réalisée. 0 = parfaitement calibré.
- **Resolution** : mesure le pouvoir discriminant. Un prévisionniste qui dit toujours 36% (notre base rate) a Resolution = 0. Un prévisionniste qui distingue les événements probables des improbables a une grande Resolution.
- **Uncertainty** : $\bar{y}(1-\bar{y})$, c'est une propriété du dataset, pas du prévisionniste. Pour notre projet, Uncertainty = 0.362 × 0.638 = 0.2310.

### Usage dans le projet

Notebook 02 (calibration). On calcule les trois termes et on vérifie numériquement que $\text{Rel} - \text{Res} + \text{Unc} = \text{BS}$.

Résultats : Brier = 0.1414, Reliability = 0.0015 (très bon), Resolution = 0.0904, Uncertainty = 0.2310.

La Reliability petite nous dit que Polymarket est globalement bien calibré. La Resolution importante nous dit que les prix sont **informatifs** : ils discriminent bien.

---

## 2. Test binomial exact

### Intuition

On a un décile de prix (disons 0.5 à 0.6), avec $N = 187$ marchés dedans et une moyenne de prix $\bar{p} = 0.528$. Sous l'hypothèse de calibration parfaite, chaque marché devrait avoir une probabilité de 0.528 de finir en YES. On a observé $k$ YES parmi 187. La question : la valeur observée de $k$ est-elle compatible avec la calibration parfaite, ou est-elle anormalement haute ou basse ?

### Formule

Sous $H_0$ : calibration parfaite, le nombre de YES suit une loi binomiale :

$$K \sim \text{Binomial}(N, \bar{p})$$

La p-value bilatérale est :

$$p = \Pr(K \leq k | H_0) + \Pr(K \geq k | H_0)$$

calculée sur la loi binomiale exacte (pas une approximation normale).

### Usage dans le projet

Notebook 02. On applique un test binomial exact à chacun des 10 bins de prix. Le choix "exact" plutôt que "chi-square" est délibéré : avec des tailles d'échantillon modérées dans certains bins (N = 187 dans le bin crypto), l'approximation normale du chi-square peut être imprécise, surtout près des bornes (probabilités proches de 0 ou 1).



## 3. Correction de Bonferroni

### Intuition

Si tu fais **un seul** test statistique au seuil $\alpha = 0.05$, tu as 5% de chances de conclure à tort à la significativité (faux positif). Mais si tu fais **dix** tests indépendants au même seuil, la probabilité qu'au moins l'un d'eux soit un faux positif monte à $1 - (1 - 0.05)^{10} \approx 40\%$. C'est énorme.

La correction de Bonferroni résout ce problème en durcissant le seuil : on utilise $\alpha / k$ au lieu de $\alpha$, où $k$ est le nombre de tests.

### Formule

Pour $k$ tests simultanés, on contrôle le **family-wise error rate** (FWER) au niveau $\alpha$ en exigeant pour chaque test :

$$p_i < \frac{\alpha}{k}$$

### Usage dans le projet

Notebook 02. On teste 10 bins de calibration simultanément, donc on exige $p < 0.05 / 10 = 0.005$ pour déclarer un bin significatif. Quand on stratifie par catégorie (crypto, sports, politics, other), on applique aussi Bonferroni **au sein de chaque catégorie** (10 tests par catégorie).

Résultat : après stratification, seulement 2 bins sur 40 restent significatifs (crypto 0.5-0.6 et other 0.2-0.3).

### Pourquoi Bonferroni plutôt que Benjamini-Hochberg ?

Il existe une alternative moins conservatrice : le contrôle du **false discovery rate** (FDR) par la procédure de Benjamini-Hochberg. BH est plus puissant (il rejette plus d'hypothèses) mais contrôle une quantité différente (la proportion attendue de faux positifs parmi les rejets, pas la probabilité d'au moins un faux positif).

On a choisi Bonferroni parce qu'on veut des conclusions solides : si on identifie un biais qui servira de base à une stratégie de trading, le coût d'un faux positif est asymétrique (on perdra de l'argent sur une stratégie qui n'a pas de vrai edge). Mieux vaut être conservateur.



## 4. Intervalles de confiance bootstrap

### Intuition

Tu veux connaître l'incertitude autour d'une statistique (disons le taux de YES dans un bin). Méthode classique : tu utilises une formule analytique qui suppose une distribution normale. Problème : près des bornes (probabilités proches de 0 ou 1), la distribution n'est pas normale, la formule ment.

Méthode bootstrap : tu **rééchantillonnes** tes données avec remise, tu recalcules la statistique sur chaque rééchantillon, et tu regardes la distribution empirique obtenue. Les percentiles 2.5% et 97.5% te donnent ton intervalle de confiance à 95%.

### Formule

Pour une statistique $\hat{\theta}$ estimée sur un échantillon de taille $N$ :

1. Tirer $B = 10000$ rééchantillons $\{X_b^*\}_{b=1}^{B}$ de taille $N$ avec remise dans les données d'origine.
2. Calculer $\hat{\theta}_b^*$ sur chaque rééchantillon.
3. L'intervalle de confiance à 95% est $[\hat{\theta}_{(0.025 B)}^*, \hat{\theta}_{(0.975 B)}^*]$ (percentiles).

### Usage dans le projet

Notebook 02. Pour chaque bin de calibration, on calcule un IC à 95% sur le taux YES réalisé via 10 000 rééchantillonnages. Ça permet de tracer les barres d'erreur verticales sur la courbe de calibration (Figure 1 du paper).



## 5. Régression logistique

### Intuition

Tu veux modéliser une probabilité ($P(Y=1)$) en fonction de variables explicatives ($X_1, X_2, ...$). Problème : si tu utilises une régression linéaire classique, tu peux prédire des probabilités négatives ou supérieures à 1, ce qui n'a pas de sens.

Solution : passer par la fonction **logit**, qui transforme $[0, 1]$ en $[-\infty, +\infty]$. On modélise le logit comme une combinaison linéaire des variables, puis on inverse pour obtenir la probabilité.

### Formule

$$\text{logit}(p) = \log \frac{p}{1-p} = \beta_0 + \beta_1 X_1 + \beta_2 X_2 + \ldots$$

Inversement :

$$p = \frac{1}{1 + e^{-(\beta_0 + \beta_1 X_1 + \ldots)}}$$

Les coefficients $\beta_i$ sont estimés par maximum de vraisemblance.

### Usage dans le projet

Notebook 03 (H2). On teste si la dérive tardive $\delta = p^{24} - p^{48}$ porte de l'information au-delà du prix à T-48h. Deux modèles :

- Baseline : $\text{logit}(P(Y=1)) = \beta_0 + \beta_1 p^{48}$
- Complet : $\text{logit}(P(Y=1)) = \beta_0 + \beta_1 p^{48} + \beta_2 \delta$

On trouve $\hat{\beta}_2 = +5.25$ ($p = 1.8 \times 10^{-44}$). La dérive est très significative.


## 6. Odds ratio

### Intuition

Les **odds** (cote en français) traduisent une probabilité en ratio gagner/perdre. Une probabilité de 75% correspond à des odds de 3 contre 1 (on gagne 3 fois sur 4, on perd 1 fois sur 4).

L'**odds ratio** compare les odds dans deux situations. Un OR de 2 signifie "les odds sont doublés". Dans une régression logistique, $e^{\beta_i}$ est l'odds ratio associé à une augmentation d'une unité de la variable $X_i$.

### Formule

$$\text{odds}(p) = \frac{p}{1-p}$$

$$\text{Odds Ratio} = \frac{\text{odds}(p_1)}{\text{odds}(p_2)}$$

Dans une régression logistique, $\text{OR}_i = e^{\beta_i}$.

### Usage dans le projet

Notebook 03. On a $\hat{\beta}_2 = +5.25$ pour la dérive, donc OR $= e^{5.25} = 190$. **Mais attention** : ce 190 correspond à une augmentation d'une unité entière de la dérive, c'est-à-dire +1.00 en prix. En pratique, la dérive est exprimée en centimes (disons +0.10). L'OR pour +10 cents est donc $e^{5.25 \times 0.10} = e^{0.525} = 1.69$.

Interprétation : une dérive positive de 10 cents entre T-48h et T-24h multiplie par 1.69 les odds que le marché se résolve en YES. Autrement dit, +69% sur les odds.


## 7. Test de Wald et test du rapport de vraisemblance

### Intuition

Dans une régression logistique, on veut tester si un coefficient $\beta_i$ est significativement différent de zéro. Deux tests classiques :

- **Wald** : compare directement $\hat{\beta}_i$ à sa barre d'erreur (écart-type estimé). Simple et rapide.
- **Likelihood-Ratio (LR)** : compare la log-vraisemblance du modèle complet à celle du modèle restreint ($\beta_i = 0$). Plus robuste en petits échantillons.

### Formules

**Wald** :

$$W = \frac{\hat{\beta}_i}{\text{SE}(\hat{\beta}_i)} \sim \mathcal{N}(0, 1) \text{ sous } H_0$$

**Likelihood-Ratio** :

$$\text{LR} = 2 (\ell_{\text{complet}} - \ell_{\text{restreint}}) \sim \chi^2_{df} \text{ sous } H_0$$

où $df$ est le nombre de paramètres supplémentaires dans le modèle complet.

### Usage dans le projet

Notebook 03. Pour tester si la dérive apporte de l'information :

- Wald : $\hat{\beta}_2 / \text{SE}(\hat{\beta}_2) = 5.25 / 0.375 = 14$, $p < 10^{-40}$
- LR : $2 (\ell_1 - \ell_0) = 240$, $p < 10^{-50}$

Les deux rejettent massivement $H_0$.



## 8. Pseudo-R² de McFadden

### Intuition

En régression linéaire, le R² mesure la proportion de variance expliquée, entre 0 et 1. En régression logistique, il n'y a pas de R² naturel parce qu'il n'y a pas de variance à expliquer (l'outcome est binaire). Plusieurs "pseudo-R²" existent, dont celui de McFadden :

$$R^2_{\text{McFadden}} = 1 - \frac{\ell_{\text{modèle}}}{\ell_{\text{null}}}$$

où $\ell_{\text{null}}$ est la log-vraisemblance du modèle avec seulement une constante.

**Attention** : un $R^2_{\text{McFadden}}$ entre 0.2 et 0.4 est déjà considéré comme un bon ajustement en régression logistique. Ne pas le comparer à l'échelle d'un R² linéaire.

### Usage dans le projet

Notebook 03. Le modèle baseline (prix à T-48h seul) a $R^2_{\text{McF}} = 0.314$. Le modèle complet (ajoutant la dérive) a $R^2_{\text{McF}} = 0.337$. Gain = 2.2 pp, ce qui est substantiel en pratique.



## 9. Paradoxe de Simpson

### Intuition

Un effet visible globalement peut **disparaître ou s'inverser** quand on stratifie par une variable. Exemple classique : dans un hôpital, un traitement A peut sembler meilleur que B en moyenne, mais être en réalité moins bon dans **chaque** catégorie de patients, parce que B est donné surtout aux cas graves.

Dans notre projet, la pooled calibration montre 4 bins miscalibrés. Après stratification par catégorie, seuls 2 bins restent significatifs, dans 2 catégories différentes. Le pattern global était partiellement un **artefact de composition**.

### Pourquoi ça arrive

Quand une variable cachée (ici la catégorie) corrèle à la fois avec la variable d'exposition (le bin de prix) et avec la variable de réponse (taux YES), les effets intra-catégorie peuvent s'inverser par rapport à l'effet inter-catégorie.

### Usage dans le projet

Notebooks 02 et 03. Pour H1 : pooled montre 4 bins significatifs (0.2-0.6), stratifié montre 2 bins dans 2 catégories distinctes. Pour H2 : pooled montre un coefficient de dérive très significatif ($p = 10^{-44}$), stratifié révèle que sports est nul alors que crypto est massif.

La leçon : **toujours stratifier**.



## 10. Ratio de Sharpe et Max drawdown

### Ratio de Sharpe

**Intuition** : combien de "rendement par unité de risque" une stratégie génère. Un Sharpe de 0 = inutile. Un Sharpe de 1 = correct. Un Sharpe > 2 = très bon. Un Sharpe > 3 = suspect (soit génie, soit erreur).

**Formule** :

$$\text{Sharpe} = \frac{\mathbb{E}[r] - r_f}{\sigma(r)} \times \sqrt{T}$$

où $r$ est le rendement par période, $r_f$ le taux sans risque, $\sigma$ l'écart-type des rendements, et $T$ le nombre de périodes par an pour annualiser.

**Dans le projet** : 187 trades sur ~10 mois, P&L moyen = 0.188 USDC, écart-type = 0.978. Sharpe non-annualisé = 0.188/0.978 = 0.192. Annualisé avec ~240 trades/an : $0.192 \times \sqrt{240} = 2.83$.

### Max drawdown

**Intuition** : la pire perte "en chemin", mesurée depuis le plus haut atteint. Capture la douleur psychologique de subir une série perdante avant la reprise.

**Formule** :

$$\text{MDD} = \max_{t_2 \geq t_1} \frac{\text{Equity}(t_1) - \text{Equity}(t_2)}{\text{Equity}(t_1)}$$

**Dans le projet** : MDD de 4.1% du capital déployé. Très modéré grâce à la diversification temporelle (187 trades sur 10 mois).

*Document préparé dans le cadre du projet Polymarket Calibration Study, avril 2026.*
