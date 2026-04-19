# Notes en français — Notebook 03 (Late Resolution Drift Analysis)

> Document de révision personnel. Explications en français de chaque cellule
> du notebook.
>
> Voir aussi `concepts_theoriques.md` pour les définitions détaillées.

---

## Objectif du notebook 03

**Question scientifique centrale :** la dérive du prix entre T-48h et T-24h
avant la résolution d'un marché Polymarket contient-elle de l'information
prédictive au-delà du niveau de prix lui-même ?

**Méthode formelle :** on teste H2 (préenregistrée le 14-20 avril 2026) via :
1. Extraction de `price_t48h` et `price_t24h` via `merge_asof`
2. Calcul de `drift = price_t24h - price_t48h`
3. Régression logistique baseline M0 : outcome ~ price_t48h
4. Régression logistique complète M1 : outcome ~ price_t48h + drift
5. Test de Wald sur β_drift
6. Test du rapport de vraisemblance M1 vs M0
7. Stratification par catégorie

**Sortie attendue :** verdict formel **H2 acceptée ou rejetée**, et si acceptée,
identification des catégories où l'effet est robuste.

---

## Résumé cellule par cellule

### Cellule 1 — Markdown d'en-tête

Déclaration formelle de H0 et H1, méthodologie, scope (duration ≥ 3 jours
pour que T-48h soit bien avant T-24h avant résolution).

### Cellule 2 — Imports et setup

**Nouvelle dépendance :** `statsmodels` pour les régressions logistiques
avec p-values, SE et intervalles de confiance. scipy.stats ne fait pas ça
aussi proprement.

**Point technique :** on utilise `statsmodels.api.Logit` qui retourne un
objet de résultat riche en diagnostics (pseudo R², log-likelihood, tests
de spécification).

### Cellules 3-4 — Extraction des dérives

**Ce qu'on fait :**
Pour chaque marché, on extrait deux prix :
- `price_t48h` : prix YES 48h avant fermeture
- `price_t24h` : prix YES 24h avant fermeture

Puis on calcule `drift = price_t24h − price_t48h`.

**Méthode : double merge_asof**
- Un premier merge sur target_48h pour obtenir price_t48h
- Un second merge sur target_24h pour obtenir price_t24h
- Jointure finale sur market_id

**Filtres qualité appliqués :**
- `duration_days >= 3` : indispensable pour que T-48h ait du sens
- `volume >= $1000` : exclusion des micro-marchés
- `yes_token_id` non null
- Pas de holdout

**Résultats de cellule 4 :**
- N = 8,160 marchés
- YES rate = 36.9% (cohérent avec notebook 02)
- Mean drift = -0.003 (quasi nul)
- Std drift = 0.079 (dérive typique ±8 cents)
- Range [-0.92, +0.90] (quelques mouvements extrêmes)

**Pourquoi la moyenne de la dérive est nulle :**
Par construction, si le marché est un martingale (prix = espérance de
l'outcome), la dérive a espérance nulle. Ce qu'on observe confirme cette
propriété : Polymarket n'a pas de biais directionnel systématique.

### Cellules 5-6 — Régressions logistiques M0 et M1

**Ce qu'on teste :**
- M0 : baseline, seul price_t48h prédit l'outcome
- M1 : ajout du drift comme second prédicteur

**Résultats clés pour M1 :**
- β_drift = +5.25 (fortement positif)
- SE = 0.375
- p-value = 1.8 × 10⁻⁴⁴ (essentiellement zéro)
- Odds ratio = 190.8

**Interprétation de l'OR :**
Un drift de +0.10 multiplie les odds de YES par exp(5.25 × 0.10) = 1.69,
soit +69% sur les odds. C'est énorme.

**Test du rapport de vraisemblance :**
LR statistic = 240, p < 10⁻⁵⁰. Ajouter drift améliore massivement le modèle.
Gain de pseudo R² = +2.24 points de pourcentage (de 0.314 à 0.337).

**Point pro important :**
Un gain de pseudo R² de 0.02 sur un modèle déjà à 0.31 est **très
substantiel**. Dans la littérature finance/économie, gagner 1 point de R²
avec un seul prédicteur supplémentaire est déjà considéré comme fort.

### Cellule 7 — Visualisation de l'effet de la dérive

Deux graphiques :

**Panel gauche :** distributions de drift colorées par outcome (YES en vert,
NO en rouge). Les YES ont une distribution décalée vers la droite.

**Panel droit :** YES rate en fonction du drift, par bin.
- Drift à -0.20 : YES rate ~26%
- Drift à 0 : YES rate ~37% (= base rate)
- Drift à +0.20 : YES rate ~59%

**Courbe monotone croissante : la dérive est clairement prédictive.**

### Cellules 8-9 — Stratification par catégorie

**Résultats par catégorie :**

| Catégorie | n | OR_drift | p-value | Significatif |
|---|---|---|---|---|
| Crypto | 1,132 | 266 | 10⁻¹⁸ | **YES** |
| Sports | 2,407 | 4.22 | 0.13 | no |
| Politics | 314 | 18.6 | 0.14 | no |
| Other | 4,062 | 848 | 10⁻²⁶ | **YES** |

**Lecture :**
- Effet massif dans Crypto et Other (asymétrie d'information forte)
- Effet non-significatif dans Sports malgré n=2407 (**marchés sports
  efficients au niveau de la dérive**)
- Politics sous-puissant (n trop petit)

**Conclusion subtile :**
L'effet pooled de H2 vient principalement de Crypto + Other. Les sports
sont efficients au sens où leur dérive pré-match n'est pas prédictive.
C'est cohérent avec une théorie "information-driven drift" : là où
l'information arrive par sauts asymétriques (crypto, politique, autres
événements), la dérive reflète l'absorption progressive de cette info.
Dans les sports, le résultat se décide pendant le match, pas avant.

### Cellules 10-12 — Verdict formel + JSON

**H2 est acceptée avec hétérogénéité.**

On sauvegarde `h2_verdict.json` avec :
- status: "accepted_with_heterogeneity"
- Résultats pooled et par catégorie
- Nuances d'interprétation (causalité ambiguë, exploitation non-triviale)

---

## 🎓 Comprendre le notebook 03 pour un débutant complet

*Si tu lis ce document sans rien connaître à la finance ni aux statistiques,
commence par ici. Tout est expliqué avec des mots simples et des exemples.*

## Le contexte : qu'est-ce qu'on teste ?

Dans le notebook 02, on s'est demandé : **"Quand le marché dit 80%, est-ce
que ça arrive 80% du temps ?"** C'était la calibration.

Maintenant la question change. On se demande : **"Est-ce que la FAÇON DONT
LE PRIX BOUGE pendant les dernières heures contient de l'information sur
ce qui va se passer ?"**

C'est complètement différent.

### Exemple très simple

Imagine un match de foot qui se joue dans 24 heures : France vs Italie. Le
marché Polymarket propose un marché "La France va-t-elle gagner ?".

**Scénario A :**
- Il y a 48 heures : le prix de "OUI" est à 0.60 (60% de chances de victoire française)
- Il y a 24 heures : le prix de "OUI" est à 0.75 (75%)

La France a monté de 0.60 à 0.75. **Dérive = +0.15.** Le marché est devenu
plus confiant dans la victoire française.

**Scénario B :**
- Il y a 48 heures : le prix de "OUI" est à 0.85 (85%)
- Il y a 24 heures : le prix de "OUI" est à 0.75 (75%)

La France a baissé de 0.85 à 0.75. **Dérive = -0.10.** Le marché est devenu
moins confiant.

**Dans les deux scénarios, le prix actuel est identique : 0.75.** Mais la
trajectoire est opposée. Question H2 : est-ce que le scénario A va finir
plus souvent en victoire française que le scénario B ?

Si oui, alors **la dérive contient de l'information au-delà du prix lui-même**.
Si non, alors seul compte le prix présent, peu importe comment on y est arrivé.

---

## Pourquoi c'est important

Si les trajectoires contiennent de l'information, alors :

1. **Théoriquement** : le marché absorbe progressivement de l'information
   plutôt que d'être instantané. Les prix montrent du "momentum"
   (tendance à continuer dans la même direction).

2. **Pratiquement** : on pourrait détecter des dérives en cours et parier
   sur leur continuation. Stratégie de "momentum trading" adaptée aux
   marchés de prédiction.

---

## La difficulté technique : on teste DEUX variables à la fois

Pour H1, on testait une seule chose : le prix. Ça suffisait de compter les
OUI dans chaque tranche de prix.

Pour H2, on teste deux choses en même temps :
- Le niveau de prix (prix à T-48h, comme avant)
- La dérive (mouvement T-48h → T-24h, nouveau)

**Problème** : ces deux variables peuvent être corrélées. Un marché à prix
très bas à T-48h (disons 0.10) ne peut pas dériver de -0.30. Les deux
variables se contraignent mutuellement.

**Solution** : la **régression logistique**. C'est un modèle mathématique
qui estime simultanément l'effet de plusieurs variables sur un outcome
binaire (YES/NO), en contrôlant les autres.

### Image mentale de la régression logistique

Imagine un pédiatre qui veut savoir si la taille ET le poids d'un enfant
prédisent son état de santé (sain/malade).

- Version naïve : "Les enfants grands sont-ils plus sains ?" → on regarde
  corrélation taille-santé.
- Problème : les enfants grands sont plus lourds. C'est peut-être le poids
  qui compte vraiment, pas la taille.
- Solution : régression logistique avec taille ET poids comme variables.
  Le modèle nous dit l'effet **propre** de chaque variable, en contrôlant
  pour l'autre.

Dans notre cas : la régression nous dit l'effet propre de la dérive, en
contrôlant pour le prix.

---

## La formule (pour ceux qui veulent comprendre)

La régression logistique suppose que la probabilité de OUI se modélise
ainsi : P(OUI) = 1 / (1 + exp(-(β₀ + β₁ × prix + β₂ × dérive)))

Les coefficients β₀, β₁, β₂ sont estimés à partir des données.

**Ce qui nous intéresse : β₂.**
- Si β₂ = 0 → la dérive n'a aucun effet propre
- Si β₂ > 0 → une dérive positive augmente les chances de OUI
- Si β₂ < 0 → une dérive positive diminue les chances de OUI

On teste **formellement** si β₂ est significativement différent de 0 (test
de Wald).

---

## Les odds ratio, simplifiés

Un coefficient β dans une régression logistique, c'est un changement sur une
échelle bizarre (le "log des odds"). Pour rendre ça intuitif, on calcule
**l'odds ratio** : OR = exp(β)

**Interprétation magique** : l'OR te dit **par combien multiplient les
chances** quand la variable augmente d'une unité.

- OR = 1 : aucun effet
- OR = 2 : les chances doublent
- OR = 0.5 : les chances sont divisées par 2

Pour notre H2 : β_drift = +5.25, donc OR = exp(5.25) = 190.

**Interprétation** : une augmentation de la dérive de 1 unité multiplie les
chances de OUI par 190. Mais comme la dérive est en "fraction de dollar"
(0 à 1), une unité = 1 dollar complet, ce qui est énorme.

**Pour être réaliste** : un drift de +0.10 (10 cents) multiplie les chances
par exp(5.25 × 0.10) = 1.69, soit +69%. C'est toujours beaucoup.

---

## Le résultat en une phrase

**La dérive entre T-48h et T-24h est massivement prédictive de l'outcome.**

- p-value = 1.8 × 10⁻⁴⁴ (probabilité quasi nulle que ce soit du hasard)
- Odds ratio de 190 par unité, +69% pour un drift de 10 cents

**Mais ATTENTION** : l'effet n'est pas uniforme par catégorie.

---

## La stratification : un résultat plus subtil qu'il n'y paraît

Quand on sépare par catégorie :

**Crypto** : effet massif (OR = 266). Pourquoi ? Les crypto bougent sur
du news : un tweet de Musk, une régulation, un hack. Ces événements sont
**asymétriques** (ils arrivent soudainement) et informationnels. Quand le
prix monte fort entre T-48h et T-24h, c'est parce qu'une info vient de
tomber, et cette info ne va pas s'inverser.

**Other** : effet massif aussi (OR = 848). Catégorie fourre-tout mais
dominée par des événements à issue binaire claire (élections locales,
annonces, etc.).

**Sports** : effet NON-SIGNIFICATIF (p = 0.13). Surprise ? Pas vraiment.
Avant un match de foot ou de basket, il n'y a pas beaucoup d'info qui
tombe (peut-être une blessure de dernière minute, mais rare). Le prix
pré-match reflète déjà les cotes des parieurs professionnels. **Le vrai
résultat se joue pendant le match, pas avant.** Donc la dérive pré-match
est du bruit.

**Politics** : n = 314, trop petit pour conclure.

### La leçon scientifique

Le résultat pooled ("H2 validé") cachait une réalité plus nuancée. La
stratification révèle que :

1. Dans les marchés à information asymétrique (crypto, other), la dérive
   porte de la vraie information.
2. Dans les marchés sport, où l'information pré-événement est limitée,
   la dérive est du bruit.

**C'est cohérent avec la théorie de l'efficience des marchés** : les
marchés sont efficients quand l'information est déjà toute disponible et
digérée (sports). Ils le sont moins quand l'information arrive par sauts
(crypto, politique).

---

## Les limites scientifiques 

1. **Causalité ambiguë** : on voit une corrélation entre drift et outcome,
   mais on ne peut pas dire si la drift CAUSE l'outcome, ou si une
   information cachée cause les deux. Pour tester la causalité il faudrait
   un modèle structurel ou une expérience, ce qu'on ne peut pas faire sur
   des données observationnelles.

2. **Le drift observé est déjà intégré dans le prix à T-24h** : si tu vois
   un drift de +15 cents, ce drift est déjà "payé" par le prix actuel.
   Tu ne peux pas "acheter après avoir vu le drift" et espérer du profit
   gratuitement. Pour exploiter H2, il faudrait :
   - Prédire le drift AVANT qu'il ne se réalise (donc prédire les news)
   - Ou prédire que le drift VA CONTINUER (extension de momentum)

3. **Les coûts de transaction (2% sur Polymarket)** doivent être couverts
   par l'edge. Même si la dérive prédit l'outcome, si l'edge attendu par
   trade est < 2%, la stratégie est non rentable.



## Vocabulaire clé introduit dans ce notebook

**Régression logistique** : modèle qui estime la probabilité d'un outcome
binaire (0/1) en fonction de plusieurs variables simultanément. Forme :
P(Y=1) = σ(β₀ + β₁X₁ + β₂X₂ + ...). Remplace le test binomial quand on a
plusieurs prédicteurs.

**Coefficient β** : mesure du changement du log-odds pour une augmentation
d'une unité de la variable. Peut être positif, négatif, ou nul.

**Odds ratio (OR)** : exp(β). Interprétation multiplicative intuitive. OR=2
signifie "les odds doublent", OR=0.5 "les odds sont divisés par 2".

**Test de Wald** : test statistique qui vérifie si un coefficient β est
significativement différent de 0. Similaire dans l'esprit à un test t.

**Test du rapport de vraisemblance (LR test)** : compare deux modèles
(M0 baseline vs M1 complet) pour voir si ajouter une variable améliore
significativement l'ajustement. Statistique suit un chi² à (nb variables
ajoutées) degrés de liberté.

**Pseudo R² McFadden** : équivalent logit du R² classique. Mesure la
fraction de variance (log-likelihood) expliquée par le modèle. Valeurs
typiques : 0.2-0.4 considéré comme bon ajustement.

**Momentum** : phénomène financier où les prix qui bougent dans une
direction ont tendance à continuer dans cette direction. Bien documenté
en actions (Jegadeesh & Titman 1993). Notre H2 teste une version
spécifique aux prediction markets.

**Information asymétrique** : situation où certains acteurs détiennent de
l'information que d'autres n'ont pas. Crée des mouvements de prix brusques
quand l'info est révélée.

**Efficience des marchés** : hypothèse selon laquelle les prix reflètent
toute l'information disponible. Un marché efficient ne laisse pas
d'arbitrage gratuit. Les sports sont plus efficients que les crypto dans
nos résultats.

**Clustered standard errors** : correction des erreurs-types quand les
observations ne sont pas indépendantes (markets liés à un même event).
Non appliqué ici par simplicité mais mentionné dans les limitations.

**Causalité vs corrélation** : distinction fondamentale en statistiques.
Nos tests montrent une corrélation entre drift et outcome, mais pas que
l'un cause l'autre. Démontrer la causalité nécessite des conditions
supplémentaires (expérience contrôlée, variable instrumentale, etc.).

