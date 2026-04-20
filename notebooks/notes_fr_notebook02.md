## Cellule 1 — Markdown d'en-tête

Déclaration formelle de H0 et H1, des méthodes qu'on va utiliser, et de la
structure du verdict. **C'est le contrat scientifique du notebook** : un
lecteur sait exactement ce qu'on va tester et comment.

---

## Cellule 2 — Imports et setup

**Nouvelles dépendances par rapport au notebook 01 :**
- `scipy.stats` : pour les tests statistiques (binomial, chi², etc.)

**Nouveau : `np.random.seed(42)`**
Fixe la graine aléatoire du générateur NumPy. Sans ça, chaque exécution
du notebook donnerait des résultats légèrement différents pour le bootstrap.
**La reproductibilité est une exigence absolue en recherche scientifique.**

**Question recruteur potentielle :**
"Pourquoi seed=42 ?" → Convention : référence au Guide du voyageur galactique
(Douglas Adams), où 42 est "la réponse à la grande question". Devenu seed
par défaut dans la communauté data science. Aucune importance technique, on
pourrait mettre 1 ou 12345. L'important est de **fixer une valeur**.

## Cellules 3-4 — Chargement et filtres qualité

**Pourquoi on recharge les données au lieu d'importer du notebook 01 :**
Principe de **notebook auto-suffisant**. Un recruteur qui clone le repo
doit pouvoir exécuter notebook02 directement, sans avoir fait notebook01
avant. C'est la norme en recherche reproductible.

**Principe DRY (Don't Repeat Yourself) vs autonomie :**
Recopier la logique de chargement est en tension avec DRY. Mais dans un
notebook de recherche, l'**autonomie** l'emporte : chaque notebook documente
ses propres hypothèses de traitement. Dans une vraie codebase on refactorerait
dans un module Python importable, mais pour la phase recherche c'est OK.

**Filtres qualité appliqués :**
1. `duration_days >= 2` : exclut les marchés intraday où T-24h est antérieur
   à l'ouverture. Indispensable pour que la mesure ait un sens.
2. `volume >= $1,000` : exclut les micro-marchés. Les prix y sont du bruit,
   pas une vraie agrégation d'info.
3. Exclusion de `price_t24h == 0.50` : le notebook 01 a détecté 2,731 marchés
   bloqués exactement à 0.50, probablement illiquides. Les garder biaiserait
   le bin 0.5-0.6.

**Important méthodologiquement :**
Ces seuils ont été décidés AVANT de regarder le résultat de H1. Pas de
p-hacking. Documenté dans le préregistrement de `research_journal.md`.


## Cellules 5-6 — Décomposition de Murphy

**Ce qu'on calcule :** on décompose le Brier score en 3 composantes :
Reliability, Resolution, Uncertainty.

**Rappel des définitions simples :**
- **Reliability** : mesure de la calibration. "Quand le marché dit 30%,
  ça arrive 30% du temps ?" Parfait = 0.
- **Resolution** : mesure du pouvoir discriminant. "Les prédictions varient-elles
  selon le cas ou sont-elles toutes autour de la moyenne ?" Plus c'est haut, mieux.
- **Uncertainty** : difficulté intrinsèque du problème = base_rate × (1 − base_rate).
  Indépendant du prédicteur. Notre cas : 0.362 × 0.638 = 0.2311.

**Comment lire les résultats :**

Si **Reliability est petit** (disons < 0.002), le marché est bien calibré globalement.
Même si H1 pointe un biais sur un bin précis, l'effet agrégé est marginal.

Si **Reliability est gros** (disons > 0.01), on a un biais systémique important.
H1 sera probablement acceptée sur plusieurs bins.

**Le ratio Reliability / Resolution** est l'indicateur clé :
- Ratio faible (< 0.1) : le marché est bon, peu d'opportunité calibration
- Ratio élevé (> 0.5) : grosse marge d'amélioration via calibration

**Colonne `miscalibration` = mean_predicted − yes_rate_realized**
- **Positif** : le marché surestime YES dans ce bin (prix trop hauts)
- **Négatif** : le marché sous-estime YES (prix trop bas)

**Pattern attendu du favorite-longshot bias :**
- Bins très bas (0.0-0.1, 0.1-0.2) : miscalibration **positive** (prix trop hauts
  sur les longshots → on les sur-paie)
- Bins très hauts (0.8-0.9, 0.9-1.0) : miscalibration **négative** (prix trop bas
  sur les favoris → sous-évalués)

Si on voit ce pattern dans les données, c'est une confirmation du FLB classique.


## Cellules 10-11 — Tests binomiaux avec Bonferroni

**Ce qu'on calcule :** pour chaque bin de prix, on teste formellement si
le nombre observé de YES est compatible avec la loi binomiale de paramètres
(n_bin, prix_moyen_bin).

**Test binomial exact vs chi² :**
On utilise le test exact plutôt qu'une approximation normale/chi². Pourquoi ?
Parce que pour les bins extrêmes (près de 0 ou 1), la loi binomiale est très
asymétrique et les approximations sont mauvaises. Coût : calcul un peu plus
lourd. Bénéfice : résultats fiables même sur les bins à faible n.

**Interprétation de la sortie :**

Pour chaque bin :
- `p_value` : probabilité d'observer un écart aussi extrême sous H0
- `significant_bonferroni` : True si p_value < 0.005 (seuil corrigé)
- `miscalibration` : prix_moyen − taux_réalisé
  - Positif → marché surestime YES (à vendre YES, à acheter NO)
  - Négatif → marché sous-estime YES (à acheter YES)

**Différence entre significativité et exploitabilité :**

Un bin peut être :
1. Significatif (p < 0.005) ET gros (|miscal| > 2 cents) → vraie opportunité
2. Significatif mais petit (|miscal| < 1 cent) → vrai biais mais mangé par les frais
3. Non significatif mais gros en apparence → n trop petit, bruit probable
4. Non significatif et petit → rien à exploiter

**En entretien** : savoir articuler "il y a une vraie edge statistique, mais
elle est trop petite pour être rentable après les 2% de frais Polymarket"
c'est le niveau pro. Les juniors oublient toujours les frais.

## Cellules 12-14 — Stratification par catégorie

**Pourquoi on stratifie :**
Un effet agrégé peut cacher une hétérogénéité. Si on trouve un biais global
mais qu'il vient à 100% d'une seule catégorie, la conclusion change : ce
n'est pas "le marché Polymarket est biaisé", c'est "les marchés crypto sont
biaisés, les autres sont OK".

**Le concept statistique clé : confounding (confusion)**
Une variable cachée (ici la catégorie) peut produire des associations
trompeuses. Un test stratifié élimine ce risque en testant séparément.

**Le trade-off : puissance vs pureté**
- Plus on stratifie fin, plus chaque groupe est pur (interprétation nette)
- Mais chaque groupe a moins d'observations, donc moins de puissance statistique
- Avec n < 30 par bin, on supprime (la loi binomiale devient instable)

**Comment lire la heatmap :**
- Rouge = miscalibration positive (marché surestime YES)
- Bleu = miscalibration négative (marché sous-estime YES)
- Plus c'est intense, plus l'écart est grand
- *** = significatif après Bonferroni au sein de la catégorie
- — = bin supprimé pour n < 30

**Trois scénarios d'interprétation :**
1. Même pattern dans toutes les catégories → résultat robuste
2. Pattern concentré sur une catégorie → stratégie ciblée
3. Patterns opposés selon catégorie → biais global = artefact de composition

## Cellules 15-16 — Verdict formel

**Ce qui a changé entre pooled et stratifié :**
Le pooled annonçait 4 bins significatifs. Le stratifié ramène ça à 2 bins
dispersés dans 2 catégories différentes. **La différence est énorme
scientifiquement.**

**Leçon méthodologique majeure :**
Un résultat pooled doit TOUJOURS être vérifié par stratification. Sinon on
risque le **simpson's paradox** : un effet global qui s'inverse ou disparaît
une fois qu'on contrôle pour une variable confondante.

**Verdict articulé en 3 dimensions :**
1. **Pour la théorie** : pas de favorite-longshot bias classique. Pattern
   inattendu de mid-range overconfidence, spécifique à certaines catégories.
2. **Pour la stratégie** : un seul edge crypto est significatif et
   économiquement exploitable (+10.7 cents > 2 cents de frais).
3. **Pour le projet** : on continue (notebook 03 sur H2) avec cette
   candidate strategy à valider en walk-forward.

**Important pour un entretien :**
Si on te demande "tu as validé H1 ?" ta réponse doit être nuancée :
"Partiellement. Pooled : oui. Stratifié : un effet isolé sur crypto.
J'ai préféré documenter l'incohérence entre les deux niveaux d'agrégation
plutôt que de cherry-picker le résultat pooled."

**C'est cette honnêteté qui distingue un chercheur sérieux d'un cueilleur
de p-values.**


---

# 🎓 Comprendre le notebook 02 pour un débutant complet

*Ce texte suppose que tu as déjà lu la version débutant du notebook 01.*

## Le contexte : qu'est-ce qu'on essaie de prouver ?

Dans le notebook 01, on a construit un tableau qui ressemble à ça :

| Tranche de prix | Prix moyen | Taux OUI réel | Écart |
|---|---|---|---|
| 0-10% | 5% | 2% | -3 points |
| 20-30% | 25% | 33% | +8 points |
| 80-90% | 85% | 87% | +2 points |

On voit des **écarts**. Mais la vraie question est :

**Ces écarts sont-ils VRAIMENT des biais du marché, ou juste du hasard dans
notre échantillon ?**

Imagine qu'on lance une pièce 100 fois et qu'on obtienne 54 faces. Est-ce que
la pièce est biaisée, ou est-ce juste un résultat normal ? Tu sens bien que
54 ce n'est pas trop éloigné de 50, donc probablement c'est juste le hasard.
Mais si on obtient 75 faces sur 100, là c'est louche.

**Le rôle des statistiques** : nous dire à partir de quel écart on doit
commencer à soupçonner un vrai biais, compte tenu de la taille de notre
échantillon.

C'est exactement ce que fait le notebook 02.

---

## L'hypothèse H1 précisément formulée

**Hypothèse nulle (H0)** : "Polymarket est parfaitement calibré. Quand le
marché dit 80%, ça arrive exactement 80% du temps. Tous les écarts que je
vois sont du pur hasard."

**Hypothèse alternative (H1)** : "Il existe au moins une tranche de prix où
le marché est biaisé. L'écart qu'on voit n'est pas du hasard."

Le boulot du notebook 02 : **trancher entre H0 et H1**.

---

## Les 5 outils mathématiques qu'on utilise

### Outil 1 : la décomposition de Murphy

Le Brier score (0.17 chez nous) est un chiffre unique qui mesure la qualité
des prédictions. Mais un seul chiffre cache plusieurs choses. Un chercheur
nommé Allan Murphy a montré en 1973 que le Brier score peut se décomposer
en 3 parties :

$$\text{Brier} = \text{Reliability} - \text{Resolution} + \text{Uncertainty}$$

Pour comprendre, prends l'image de deux météorologistes qui prédisent s'il
va pleuvoir chaque jour :

**Alice dit toujours "30% de pluie".** Il pleut effectivement 30 jours sur
100. Alice est **parfaitement calibrée** (quand elle dit 30%, il pleut 30%
du temps) mais elle est **inutile** — elle ne te dit jamais "prends ton
parapluie" ou "pars en pique-nique sans risque", elle dit toujours 30%.

**Bob dit 0% 70 jours, et 100% les 30 autres jours.** S'il a raison à 90%
dans les deux cas, il est très **informatif** (il te donne des prédictions
différentes) mais légèrement **mal calibré** (quand il dit 100%, il ne pleut
que 90% du temps).

- **Reliability = mesure du décalage** entre prédictions et réalité. Alice = 0.
- **Resolution = mesure de la variabilité** des prédictions utiles. Bob > Alice.
- **Uncertainty = difficulté intrinsèque** du problème, ici p(1-p) = 0.23.

**Nos résultats** :
- Reliability = 0.0015 (très petit → bien calibré globalement)
- Resolution = 0.0904 (correct → le marché discrimine)
- Uncertainty = 0.2310 (fixe par le dataset)

Vérification : 0.0015 - 0.0904 + 0.2310 = 0.1421 ≈ 0.1414 (notre Brier).
Les chiffres collent, la décomposition est correcte.

**Interprétation** : le marché Polymarket est globalement bien calibré. La
"mauvaise" performance (Brier = 0.17) vient essentiellement du fait que le
problème est intrinsèquement difficile (Uncertainty), pas d'un défaut de
calibration.

### Outil 2 : le test binomial exact

Maintenant on zoome sur chaque tranche de prix pour voir si l'écart observé
est significatif.

**Exemple concret** : la tranche 0.2-0.3 contient 783 marchés. Le prix moyen
est 0.253. Si le marché était parfaitement calibré, chaque marché aurait
25.3% de chances d'être OUI. Donc on s'attendrait à environ 198 OUI.

**Observé** : 252 OUI (taux de 32.2%).

**Question** : quelle est la probabilité d'observer 252 OUI ou plus si la
vraie probabilité est bien 25.3% ?

Le **test binomial exact** calcule cette probabilité directement à partir
de la loi binomiale (loi mathématique qui décrit les tirages répétés de
type pile-ou-face).

**Résultat pour ce bin : p-value = 0.000015 = 0.0015%**

Interprétation : il y a seulement 0.0015% de chances d'observer un écart
aussi extrême si le marché était parfaitement calibré. C'est donc **très
improbable que ce soit du hasard** → on peut conclure à un vrai biais.

### Outil 3 : la correction de Bonferroni

Mais attention à un piège. On ne teste pas une tranche, on en teste **10**
(les 10 déciles de prix).

Si on fait 10 tests indépendants au seuil habituel de 5%, la probabilité
que **au moins un** test se trompe (faux positif) est de **40%**, pas 5%.

Calcul : (1 - 0.95^10) = 40.1%.

**Solution** : la correction de Bonferroni. On divise le seuil par le nombre
de tests. Nouveau seuil : 0.05 / 10 = 0.005 (= 0.5%).

Un test n'est déclaré "significatif" que si sa p-value est inférieure à
0.005. C'est plus strict, mais ça garantit que le taux global de faux
positifs reste à 5%.

**Résultats après Bonferroni sur nos 10 tranches** :
- **4 tranches sur 10** montrent un biais significatif : 0.2-0.3, 0.3-0.4,
  0.4-0.5, et 0.5-0.6.
- Les autres (tranches extrêmes et très hautes) ne sont pas significatives.

### Outil 4 : le bootstrap

Pour donner un intervalle de confiance autour de nos estimations (genre
"le taux OUI réel dans cette tranche est entre 30% et 35% avec 95% de
confiance"), on utilise le **bootstrap**.

**Principe intuitif** : on a 245 marchés dans une tranche. On ne peut pas
aller en chercher 245 autres dans le monde réel. Mais on peut **faire
semblant** : on tire 245 marchés avec remise (on peut tirer plusieurs fois
le même) dans nos 245 marchés, et on calcule le taux OUI sur ce
ré-échantillon. On répète **10 000 fois**.

Résultat : 10 000 valeurs simulées du taux OUI, qui nous donnent la
distribution de ce qu'on aurait pu observer. Les quantiles 2.5% et 97.5%
donnent notre intervalle à 95%.

**Pourquoi c'est mieux qu'un intervalle classique** : le bootstrap ne
suppose pas que la distribution est gaussienne. Il marche même avec des
petits échantillons ou des proportions extrêmes (près de 0 ou 1).

### Outil 5 : la stratification

La question finale : le biais qu'on observe vient-il de **tout le marché**
ou d'une **catégorie particulière** ?

Pour répondre, on refait les mêmes tests **séparément** par catégorie :
- Crypto (n = 1 049)
- Sports (n = 2 416)
- Politics (n = 325)
- Other (n = 3 602)

C'est la **stratification**.

**Résultats étonnants** :
- **Sports (n=2 416)** : 0 tranche significative. Le sport est parfaitement
  calibré.
- **Crypto (n=1 049)** : 1 tranche significative (0.5-0.6), mais avec un
  écart énorme de +10.7%.
- **Other (n=3 602)** : 1 tranche significative (0.2-0.3), écart de -11%.
- **Politics (n=325)** : pas assez de données pour conclure.

**Leçon majeure** : le résultat "4 tranches significatives en pooled" était
en partie un **artefact d'agrégation**. Quand on sépare par catégorie, les
biais ne sont plus les mêmes. Ils sont **concentrés dans certaines catégories
seulement**.

---

## La conclusion scientifique honnête

**H1 est partiellement acceptée, mais prudemment.**

### Ce qu'on peut dire de solide

1. Le fameux "favorite-longshot bias" des paris hippiques n'existe PAS dans
   Polymarket. Les tranches extrêmes (près de 0 et près de 1) sont bien
   calibrées.

2. Il existe un biais spécifique dans la catégorie **crypto** autour du prix
   0.5-0.6 : les marchés surestiment la probabilité de OUI de ~11 centimes.
   Si ce biais est stable dans le temps, une stratégie simple serait de
   **vendre des parts OUI** (= acheter des parts NON) dans ce cas précis.

3. La catégorie **sports** est remarquablement bien calibrée. Inutile d'y
   chercher un edge facile.

### Ce qu'on doit encore vérifier

1. Le biais crypto est-il stable dans le temps ou disparaît-il selon les
   années ? → **walk-forward validation** dans un futur notebook.

2. Peut-on vraiment exécuter la stratégie sans que notre propre achat/vente
   ne fasse bouger les prix ? → **test de liquidité**.

3. Les 2% de frais de transaction de Polymarket vont-ils manger l'edge ?
   → **calcul de rentabilité nette**.

---

## Pourquoi cette approche est valorisante pour un CV

Un recruteur quant en finance cherche trois qualités :

1. **Rigueur méthodologique** : savoir faire un test statistique proprement,
   avec correction pour tests multiples, intervalle de confiance robuste,
   stratification pour éviter les artefacts. Ce projet coche ces cases.

2. **Honnêteté scientifique** : ne pas cherry-picker les résultats qui
   arrangent. Accepter que son résultat soit plus nuancé que ce qu'on aurait
   voulu. Notre verdict "H1 partiellement acceptée" est exactement ce niveau.

3. **Compréhension économique** : ne pas confondre "biais statistiquement
   significatif" et "biais exploitable en trading". Un écart de 1% avec
   p-value = 0.001 est significatif mais mangé par les frais de 2%. Il faut
   les deux.

En entretien, si on te demande "raconte-moi ce projet", tu pourras dire :

*"J'ai testé le favorite-longshot bias sur 8 306 marchés Polymarket. La
littérature classique prédit un biais aux extrêmes ; je n'en ai trouvé
aucun. En revanche, j'ai détecté un biais mid-range concentré sur la
catégorie crypto (+10.7% sur le bin 0.5-0.6, p=0.004). La stratification
a révélé que l'effet pooled agrégé était partiellement un artefact de
composition, ce qui m'a conduit à nuancer ma conclusion. Cette distinction
entre effet réel et artefact est cruciale pour éviter le p-hacking."*

Cette réponse vaut beaucoup plus que "j'ai gagné X% en backtest".

---

## Vocabulaire clé introduit dans ce notebook

**Décomposition de Murphy** : découpage du Brier score en Reliability +
Resolution + Uncertainty. Permet de voir d'où vient la "mauvaise" performance
d'un prédicteur.

**Reliability** : mesure de la calibration. "Quand tu dis 30%, ça arrive 30%
du temps ?" Parfait = 0.

**Resolution** : mesure du pouvoir discriminant. "Tes prédictions varient-elles
de façon informative ?" Plus c'est haut, mieux.

**Uncertainty** : difficulté intrinsèque du problème, indépendante du
prédicteur. p × (1-p).

**Test binomial exact** : test statistique qui utilise directement la loi
binomiale pour calculer la probabilité d'observer un écart donné sous H0.
Plus précis que le test chi² pour les petits échantillons.

**P-value** : probabilité d'observer un écart au moins aussi extrême sous
H0. Plus c'est petit, plus c'est improbable que l'écart soit du hasard.

**Correction de Bonferroni** : division du seuil α par le nombre de tests,
pour contrôler le taux de faux positifs global. Indispensable dès qu'on
fait plusieurs tests.

**Bootstrap** : technique de ré-échantillonnage avec remise pour estimer la
distribution d'une statistique. Sert à construire des intervalles de
confiance robustes.

**Stratification** : refaire la même analyse séparément par sous-groupes.
Permet de détecter si un résultat global est uniforme ou concentré dans
une catégorie.

**Artefact d'agrégation (Simpson's paradox)** : phénomène où un effet
observé en agrégé disparaît ou s'inverse quand on stratifie. Raison pour
laquelle on doit toujours stratifier ses tests.

**Odds ratio** : exp(coefficient d'une régression logistique). Interprétation
multiplicative de l'effet d'une variable sur les chances.

**Edge (avantage)** : en trading, l'espérance de gain par trade. Doit être
positive après coûts (frais, slippage) pour qu'une stratégie soit rentable.
---