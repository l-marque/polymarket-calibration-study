# Polymarket Calibration Study — Résumé global du projet

> Document accessible à toute personne curieuse, sans prérequis en finance
> ou en statistiques. Explique simplement ce qui a été fait, pourquoi, et
> ce qu'on a découvert.
>
> **Auteur :** Lucas Marque — Étudiant L3 ingénieur, Centrale Méditerranée  
> **Période :** Avril 2026  
> **Repository :** https://github.com/l-marque/polymarket-calibration-study

---

## Partie 1 — C'est quoi ce projet, en une phrase

**J'ai analysé scientifiquement si les prix de Polymarket (un site où les
gens parient sur l'avenir) sont justes ou biaisés, et si un trader peut
exploiter ces biais pour gagner de l'argent.**

---

## Partie 2 — Polymarket, c'est quoi exactement

### Le principe de base

Polymarket est un site internet où on peut parier sur n'importe quel
événement futur. Exemples de questions qu'on y trouve :

- "Donald Trump va-t-il visiter la Russie avant juin 2026 ?"
- "Le Bitcoin va-t-il dépasser 150 000 $ avant fin 2026 ?"
- "Les Lakers vont-ils battre les Celtics dimanche ?"
- "La Terre va-t-elle avoir une canicule en France cet été ?"

Pour chaque question, deux réponses possibles : **OUI** ou **NON**.

### Le mécanisme des prix

Le site fonctionne comme une bourse. Pour chaque question :

- Tu peux **acheter** des parts "OUI" ou des parts "NON"
- Chaque part coûte entre 0 et 1 dollar
- Si tu as la bonne réponse, chaque part te rapporte 1 dollar
- Si tu as tort, tes parts valent 0

**Exemple chiffré** : les parts "OUI" sur "Bitcoin > 150k" sont à 30 cents.
- J'achète 10 parts pour 3 dollars
- Si le Bitcoin dépasse 150k fin 2026, je gagne 10 dollars (profit = 7 dollars)
- Sinon, je perds mes 3 dollars

**Le prix = la probabilité collective estimée par le marché.** Si les gens
achètent beaucoup de OUI, le prix monte. Si personne n'y croit, le prix
reste bas.

- Prix "OUI" à 0.85 → le marché pense qu'il y a 85% de chances que ce soit OUI
- Prix "OUI" à 0.15 → le marché pense qu'il y a 15% de chances

C'est la même logique que les cotes sportives (PMU, Bwin), mais sans
bookmaker : c'est les parieurs eux-mêmes qui fixent les prix par leurs
échanges.

### Pourquoi c'est intéressant scientifiquement

**Est-ce que "la sagesse des foules" produit des prix justes ?** Ou
est-ce qu'il y a des biais systématiques qu'on pourrait exploiter pour
gagner de l'argent ?

Si on trouve un biais, deux choses deviennent possibles :
1. **Publier un résultat scientifique** (contribution à la littérature sur
   les marchés de prédiction)
2. **Construire une stratégie de trading rentable**

C'est ce double objectif qui motive ce projet.

---

## Partie 3 — La question centrale

**Est-ce que les prix Polymarket sont "bien calibrés" ?**

Traduit en langage simple : quand le marché dit "80% de chances", est-ce
que ça arrive vraiment 80% du temps ?

### Trois hypothèses pré-enregistrées

Avant de regarder les données, j'ai écrit formellement trois hypothèses
à tester. **C'est crucial méthodologiquement** : si je choisis mes
hypothèses après avoir vu les résultats, je peux manipuler (souvent
inconsciemment) mes conclusions. En pré-enregistrant, je me prive de
cette facilité.

**Hypothèse H1 — Calibration biaisée** :
> Les prix Polymarket présentent un biais systématique (les marchés à
> 80% pourraient en fait arriver 85% du temps, etc.).

**Hypothèse H2 — Dérive informative** :
> Le mouvement du prix juste avant la résolution (entre T-48h et T-24h)
> contient de l'information supplémentaire sur l'issue.

**Hypothèse H3 — Arbitrage entre marchés liés** :
> Des marchés qui portent sur le même événement ont parfois des prix
> incohérents, créant des opportunités d'arbitrage.

---

## Partie 4 — Ce qu'on a fait, en 4 grandes étapes

### Étape 1 : Récupérer les données (notebook 01)

**Le problème** : Polymarket a une API (interface pour développeurs) mais
elle n'est pas faite pour les chercheurs. Elle impose des limites strictes
(nombre de requêtes par seconde), a des bugs de pagination, et ses
résultats changent selon les filtres qu'on applique.

**Ce que j'ai fait** :
- Écrit un script Python qui télécharge 99 999 marchés en respectant
  les limites de l'API (3 heures de collecte)
- Stocké tout ça dans une base de données SQLite (1.36 million de points
  de prix au total)
- Ajouté 8 séries macroéconomiques (taux Fed, VIX, dollar index, inflation
  US, indice de risque géopolitique, etc.) comme variables de contrôle
- Documenté trois bugs majeurs découverts dans les données (pagination
  incomplète, drapeau "holdout" pollué, champ "catégorie" systématiquement
  vide — j'ai construit un classifieur par règles pour pallier ce dernier
  point avec 76% de couverture)

**Durée** : 2 jours de travail.

**Leçon** : les données réelles ne sont jamais propres. 80% du temps d'un
data scientist est consacré au nettoyage. Mon projet le confirme.

### Étape 2 : Tester H1 — la calibration (notebook 02)

**Ce qu'on a cherché** : est-ce que le favorite-longshot bias classique
(biais bien documenté dans les paris hippiques depuis 1949) se retrouve
sur Polymarket ? Ce biais dirait que les "outsiders" (événements peu
probables) sont surestimés et les "favoris" sous-estimés.

**Ce qu'on a fait** :
- Extrait pour chaque marché le prix exactement 24 heures avant résolution
  (11 340 marchés utilisables)
- Décomposé le Brier score à la Murphy (1973) en trois composantes :
  Reliability (calibration), Resolution (pouvoir discriminant), Uncertainty
  (difficulté intrinsèque)
- Fait 10 tests binomiaux (un par tranche de prix) avec correction de
  Bonferroni pour le multi-tests
- Calculé des intervalles de confiance par bootstrap (10 000 rééchantillonnages)
- Stratifié par catégorie (crypto, sports, politics, other)

**Ce qu'on a découvert** :
- **Le favorite-longshot bias classique n'existe PAS** dans Polymarket.
  Les prix extrêmes (proches de 0 ou 1) sont remarquablement bien calibrés.
- **Un biais inattendu "mid-range"** apparaît : les marchés dans la zone
  0.2-0.6 montrent des écarts de 5-7 points de pourcentage entre prix et
  résultat réalisé.
- **Mais la stratification change l'histoire** : ce biais pooled vient
  essentiellement de la catégorie crypto (0.5-0.6 : +10.7 cents,
  significatif à p=0.004) et du fourre-tout "other". Les sports, avec
  2 416 marchés, sont parfaitement calibrés.

**Conclusion** : H1 est **partiellement acceptée**. Pas de biais généralisé
mais une poche d'inefficience locale en crypto.

### Étape 3 : Tester H2 — la dérive (notebook 03)

**Ce qu'on a cherché** : quand le prix d'un marché bouge entre T-48h et
T-24h, est-ce que ce mouvement est informatif ou juste du bruit ?

**Ce qu'on a fait** :
- Extrait deux prix par marché (T-48h et T-24h), calculé la dérive = T-24h − T-48h
- Fait une régression logistique baseline : outcome ~ prix_T-48h
- Fait une régression logistique complète : outcome ~ prix_T-48h + dérive
- Testé la significativité du coefficient de dérive (test de Wald)
- Comparé les deux modèles (test du rapport de vraisemblance)
- Stratifié par catégorie

**Ce qu'on a découvert** :
- **La dérive est massivement prédictive** : coefficient +5.25,
  p-value = 1.8 × 10⁻⁴⁴ (essentiellement zéro)
- **Odds ratio de 190** : une dérive de +10 cents multiplie les chances
  d'YES par 1.7 (+69% des odds)
- **Gain de pseudo R² de +2.2 points** en ajoutant la dérive au modèle
- **Mais encore une fois, l'effet est hétérogène par catégorie** :
  - Crypto : OR = 266, effet massif (p < 10⁻¹⁸)
  - Other : OR = 848 (p < 10⁻²⁶)
  - Sports : non-significatif (p = 0.13) — les sports sont efficients
  - Politics : n trop petit pour conclure

**Conclusion** : H2 est **acceptée avec hétérogénéité**. La dérive reflète
l'arrivée d'information dans les marchés à information asymétrique (crypto,
événements politiques), pas un pur momentum psychologique.

### Étape 4 : Tester H3 — l'arbitrage (notebook 04)

**Ce qu'on a cherché** : les marchés qui portent sur le même événement
(même catégorie, même semaine de résolution) bougent-ils ensemble comme
le voudrait la théorie de l'efficience, ou restent-ils déconnectés ?

**Ce qu'on a fait** :
- Groupé les marchés en 221 clusters (catégorie × semaine de résolution)
- Calculé pour chaque cluster la concordance directionnelle des dérives
  (fraction des paires de marchés qui dérivent dans le même sens)
- Testé par t-test si la moyenne de cette concordance est supérieure à 0.5
  (qu'on attendrait sous l'hypothèse d'indépendance)

**Ce qu'on a découvert** :
- **Concordance moyenne = 0.534** vs 0.50 attendu → léger excès mais faible
- **p-value = 0.012** → significatif à 5% mais pas à 1%
- **Variabilité énorme** entre clusters (écart-type de 0.17)
- Les gros clusters (n > 100) convergent vers 0.50 (indépendance)
- Les petits clusters sont très dispersés (bruit d'échantillonnage)

**Conclusion** : H3 est **inconclusive**. Effet présent mais trop petit
(3.4 points de pourcentage au-dessus du hasard) pour être exploitable
après frais. Marché globalement efficient au niveau de la cohérence
directionnelle inter-marchés.

---

## Partie 5 — Le verdict global, en une phrase

**Polymarket est approximativement efficient, avec une poche résiduelle
d'inefficience concentrée dans le segment crypto.**

Les deux principales inefficiences identifiées :
1. **Crypto, bin 0.5-0.6 (calibration)** : le marché surestime la
   probabilité d'YES de ~10.7 centimes
2. **Crypto, dérive T-48h→T-24h** : la dérive est très prédictive
   (OR=266), suggérant une intégration progressive de l'information

---

## Partie 6 — Pourquoi ce projet a de la valeur

### Pour la science

C'est une **étude originale** qui teste rigoureusement trois hypothèses
sur un marché de prédiction récent (Polymarket, lancé en 2020). Les
résultats contribuent à la littérature sur l'efficience des marchés de
prédiction et nuancent le favorite-longshot bias dans un contexte moderne.

### Pour une candidature quant

Le projet démontre :
- **Maîtrise technique** : Python, SQL, API, pandas, statsmodels, matplotlib
- **Rigueur méthodologique** : préregistrement des hypothèses, correction
  pour multi-tests, stratification, intervalles bootstrap
- **Honnêteté intellectuelle** : savoir distinguer résultat pooled et
  résultat stratifié, reconnaître quand un test est inconclusive
- **Pensée économique** : distinction entre biais statistique et biais
  exploitable, prise en compte des frais de transaction
- **Compétences de communication** : documentation française et anglaise,
  explication pédagogique, README professionnel

### Pour mon propre apprentissage

J'ai découvert concrètement ce qu'est la recherche quantitative en
finance :
- La patience du nettoyage de données (80% du temps)
- La déception de voir un résultat "significatif" s'évaporer après
  stratification (H1)
- La joie de découvrir un effet massif et net (H2)
- L'humilité d'accepter qu'un test soit inconclusive (H3)
- L'importance de raconter une histoire cohérente avec les résultats

---

## Partie 7 — Limites et prochaines étapes

### Limites honnêtes

1. **Le drapeau "holdout"** avait été pollué par une opération de nettoyage
   antérieure. J'ai dû le reconstruire. Cela ajoute un risque d'erreur
   mais pas de biais systématique identifié.

2. **Le champ "catégorie" était vide** dans les données Polymarket.
   J'ai dû construire un classifieur par règles sur les slugs
   d'URL. Couverture 76%, le 24% restant est classé "other" (fourre-tout).

3. **Le volume est bucketisé** par l'API. On ne peut pas l'utiliser
   comme variable continue.

4. **H3 est testé en version proxy** : on regarde la cohérence
   directionnelle, pas le respect strict des contraintes d'arbitrage.
   Un vrai test nécessiterait d'identifier les paires exactement
   complémentaires et de regarder si la somme des prix est égale à 1.

5. **Données observationnelles seulement** : impossible de tester la
   causalité (la dérive cause-t-elle l'outcome, ou une troisième variable
   cause-t-elle les deux ?).

### Prochaines étapes envisagées

**Court terme (semaines à venir)** :
- Rédiger un working paper LaTeX (format académique)
- Construire un **mini-bot de trading** qui exploite le biais crypto 0.5-0.6
  sur données historiques (backtest)
- Valider en walk-forward : est-ce que le biais crypto est stable dans le
  temps ou dépend-il du sample analysé ?

**Moyen terme** :
- Collecter davantage de données avec un meilleur pipeline
  (résoudre le bug de pagination, parser l'event_id pour H3 rigoureux)
- Explorer un modèle prédictif (logistic regression → XGBoost) sur les
  prix T-24h
- Intégrer les variables macro comme contrôles

**Long terme** :
- Paper trading en temps réel sur 30 jours
- Si les résultats sont robustes, live trading avec capital limité
  (~100-200 USDC) pour valider en conditions réelles

---

## Partie 8 — Ce que le projet m'a appris au niveau personnel

En commençant ce projet je pensais que **faire de la finance quantitative
c'était écrire des modèles complexes de machine learning et des stratégies
flashy**. La réalité est très différente :

1. **La rigueur méthodologique prime sur la sophistication technique.**
   Un test chi-deux bien fait avec une bonne correction pour tests multiples
   est plus utile qu'un modèle XGBoost mal validé.

2. **L'honnêteté intellectuelle est une compétence transférable.**
   Accepter que H1 soit partiellement acceptée, ou H3 inconclusive, c'est
   plus dur que de "cherry-picker" les résultats qui arrangent. Mais c'est
   ça qui distingue un chercheur sérieux.

3. **Le code qu'on écrit reflète la qualité de sa pensée.**
   Quand j'ai refactorisé ma fonction T-24h en `merge_asof`, j'ai gagné
   un facteur 40 en vitesse et j'ai rendu le code plus lisible. Les bons
   outils ne sont pas optionnels.

4. **Documenter au fur et à mesure est un investissement.**
   Chaque décision consignée dans le journal de recherche m'a économisé
   du temps plus tard (et me permettra d'en parler clairement en entretien).

5. **Le préregistrement est libérateur.**
   Une fois H1/H2/H3 fixées, je savais exactement ce que je testais. Plus
   besoin de me demander si je fais le "bon" test. Je fais le test
   préenregistré, point.

---

## Vocabulaire essentiel (pour s'y retrouver)

**Polymarket** : plateforme de prediction markets lancée en 2020. Les
utilisateurs parient en USDC sur des événements futurs via des contrats
intelligents sur la blockchain Polygon.

**Prediction market** : marché financier où les prix reflètent la
probabilité estimée d'événements futurs. Différent des paris sportifs
traditionnels car il n'y a pas de bookmaker : les parieurs se font face
directement.

**Calibration** : propriété d'un prédicteur. Un prédicteur est bien
calibré si ses prédictions probabilistes correspondent aux fréquences
observées.

**Favorite-longshot bias** : biais classique découvert par Griffith (1949)
sur les paris hippiques. Les outsiders sont surestimés, les favoris
sous-estimés. Documenté dans de nombreux marchés mais absent de nos
résultats Polymarket.

**Brier score** : mesure d'erreur pour prédictions probabilistes. Plus
c'est bas, meilleures sont les prédictions. Formule : moyenne de
(prédiction − réalité)².

**P-value** : probabilité d'observer un résultat au moins aussi extrême
sous l'hypothèse nulle. Plus c'est petit, plus le résultat est improbable
sous H0.

**Bonferroni** : correction pour tests multiples. Divise le seuil α par
le nombre de tests pour contrôler le taux global de faux positifs.

**Bootstrap** : technique de rééchantillonnage avec remise pour estimer
la distribution d'échantillonnage d'une statistique sans supposer une
forme paramétrique.

**Régression logistique** : modèle statistique qui prédit une probabilité
binaire en fonction de plusieurs variables. Standard en sciences sociales
et épidémiologie.

**Odds ratio** : interprétation multiplicative du coefficient d'une
régression logistique. OR = 2 signifie "les chances doublent".

**Walk-forward** : technique de validation pour séries temporelles où on
entraîne sur le passé et teste sur le futur, en glissant la fenêtre dans
le temps. Évite le look-ahead bias.

**Holdout** : portion des données mise de côté avant toute analyse,
touchée seulement à la toute fin pour validation finale.

**Look-ahead bias** : erreur méthodologique grave en finance consistant
à utiliser dans son analyse une information qui n'était pas disponible
au moment théorique de la décision.

**Edge (en trading)** : espérance de gain par trade. Doit être positive
après coûts (frais, spread) pour qu'une stratégie soit rentable.

**Efficience des marchés** : hypothèse selon laquelle les prix reflètent
toute l'information disponible. Un marché parfaitement efficient ne
laisse aucun arbitrage gratuit.

---

## Note finale

Ce projet a été réalisé en environ **deux semaines** de travail concentré,
réparties sur avril 2026. Tout le code, les données, les résultats et les
décisions méthodologiques sont publics et reproductibles :

**GitHub** : https://github.com/l-marque/polymarket-calibration-study

Pour toute question ou collaboration : lucas.marque@centrale-marseille.fr.
