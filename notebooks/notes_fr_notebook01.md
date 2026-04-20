# Notes en français — Notebook 01 (Data Exploration)

> Document de révision personnel. À chaque cellule du notebook, j'explique en français
> ce que je fais, pourquoi je le fais, et ce qu'un recruteur pourrait me demander.

---

## Vue d'ensemble du notebook 01

**Objectif global :** explorer le dataset Phase 0 avant tout test statistique.
On regarde combien de marchés on a, dans quelles catégories, sur quelle période,
avec quels résultats, quelles tailles, quelles durées. Le but est de **détecter
les problèmes de qualité de données AVANT** de tester des hypothèses, sinon on
risque de conclure n'importe quoi.

**Règle d'or scientifique :** explore → comprends → décide des filtres → teste les hypothèses.
Pas l'inverse.

---

## Cellule 1 — En-tête Markdown

**Ce que c'est :** un titre de notebook avec mon nom, la date, le projet, et l'objectif.

**Pourquoi c'est important :** un notebook sans en-tête est illisible quand on
le retrouve dans 6 mois ou quand un recruteur l'ouvre sur GitHub. Toujours
documenter qui, quand, pourquoi.

---

## Cellule 2 — Imports et configuration

**Ce que je fais :**
- J'importe pandas, numpy, matplotlib, seaborn (la stack scientifique standard Python)
- Je définis le chemin de la base SQLite explicitement (`PROJECT_ROOT / "polymarket.db"`)
- Je règle l'affichage de pandas pour voir toutes les colonnes et formater les nombres
- J'applique un thème seaborn pour des graphes propres

**Pourquoi explicitement le chemin de la DB ?**  
Parce qu'on a découvert un bug : `config/settings.py` utilise `Path("./polymarket.db")`
qui résout par rapport au dossier courant. Comme le notebook est dans `notebooks/`,
le `./` pointe vers `notebooks/polymarket.db` qui n'existe pas. On contourne en
définissant `DB_PATH = PROJECT_ROOT / "polymarket.db"` dans le notebook.
**TODO carry-over : fixer ça dans `config/settings.py` proprement.**

**Question recruteur potentielle :** "Pourquoi tu utilises seaborn et pas juste matplotlib ?"  
Réponse : seaborn est une couche au-dessus de matplotlib qui fournit des thèmes
cohérents et des fonctions statistiques de plus haut niveau (regplot, violinplot,
heatmap). On garde matplotlib pour le contrôle bas-niveau, seaborn pour les
visualisations statistiques.

---

## Cellule 3 — Markdown : "1. Database Schema and Coverage"

**Ce que c'est :** juste un titre de section qui annonce qu'on va inspecter la base.

**Pourquoi en Markdown :** pour structurer le notebook. Un notebook professionnel
alterne Markdown (explications) et Code (exécution). Sans Markdown, c'est juste
un script Python long et illisible.

---

## Cellule 4 — Inspection du schéma

**Ce que je fais :**
J'écris une fonction `inspect_db()` qui :
1. Liste toutes les tables via `sqlite_master` (table système SQLite)
2. Pour chaque table, compte les lignes et liste les colonnes via `PRAGMA table_info`
3. Affiche le tout proprement formaté

**Pourquoi cette inspection :**
Avant d'analyser, je dois savoir ce qu'il y a dans la base. Si `markets` est vide,
ou si `price_history` n'existe pas, aucune analyse downstream ne marchera. C'est
le sanity check de base.

**Concepts techniques importants :**
- **`sqlite_master`** : table système qui contient les métadonnées (équivalent
  d'`information_schema` en PostgreSQL). Permet de lister les tables d'une base
  sans connaître leur nom.
- **`PRAGMA`** : commandes SQLite spéciales pour l'introspection (équivalent
  des `DESCRIBE` MySQL ou `\d` PostgreSQL).
- **`try / finally`** : pattern qui garantit que la connexion DB se ferme même
  si une erreur survient. Sans ça, on a des locks fantômes sur la base.

**Question recruteur potentielle :** "Pourquoi tu as fait une fonction au lieu
d'écrire le code inline ?"  
Réponse : réutilisabilité (je peux re-vérifier la base à tout moment), testabilité
(je pourrais ajouter un test unitaire), lisibilité du notebook.

**Mes résultats actuels :**
- 5 tables (`markets`, `price_history`, `macro_series`, `collection_runs`, `sqlite_sequence`)
- `markets` : 99 999 lignes (collecte plafonnée par `max_pages=200 × limit=500`)
- `macro_series` : 10 830 lignes (8 séries FRED × ~1350 jours)
- `collection_runs` : 5 lignes (audit log)
- `sqlite_sequence` : table système ignorée


## Cellule 5 — Markdown : "2. Temporal Coverage"

**Ce que c'est :** titre de la section qui explique pourquoi on regarde la
distribution temporelle.

**Pourquoi c'est important :** si 90% des marchés viennent d'un seul événement
(ex: élection US 2024), nos conclusions ne se généralisent pas. C'est un
risque de **biais de sélection temporel**.

---

## Cellule 6 — Chargement des marchés et conversion des dates

**Ce que je fais :**
1. J'ouvre une connexion SQLite
2. Je charge la table `markets` avec `pd.read_sql_query()` dans un DataFrame
3. Je convertis les timestamps Unix (secondes depuis 1970) en datetime pandas
4. J'affiche les comptages clés et la plage de dates

**Pourquoi `pd.to_datetime(..., unit="s")` :**
La base stocke les dates en Unix timestamp (entier de secondes) par souci
de compacité et performance des requêtes SQL. Pour l'analyse en pandas, on
convertit en datetime qui permet `.year`, `.month`, des opérations temporelles, etc.

**Pourquoi `errors="coerce"` :**
Certains marchés peuvent avoir des `end_ts = NULL`. `coerce` transforme ces
NULL en `NaT` (Not a Time) au lieu de planter avec une erreur. Plus robuste.

**Concept important : holdout vs eligible**
- `closed = 1` : le marché est fermé et résolu
- `holdout = 1` : il a été résolu il y a moins de 30 jours, on l'exclut
  pour préserver un set de test futur (anti-leakage)
- **Eligible = closed=1 AND holdout=0** : c'est ce qu'on peut analyser

**Question recruteur potentielle :** "Pourquoi tu réserves un holdout dès la
collecte plutôt qu'au moment du modèle ?"  
Réponse : si je décidais le holdout après avoir vu les données, je risquerais
inconsciemment de choisir un split qui m'arrange. Le pré-engagement (avant
toute analyse) garantit l'intégrité statistique. C'est de la discipline
scientifique, pas de la paranoïa.

## Cellule 7 — Diagnostic d'anomalies temporelles

**Pourquoi cette cellule existe :**
En affichant la plage de dates, j'ai constaté deux anomalies :

1. La date la plus tardive est en 2028, alors qu'on est en avril 2026.
   Impossible qu'un marché "fermé" se résolve dans le futur.
2. Le compteur `holdout` est passé de 32,379 (juste après collecte) à
   75,932 maintenant. Cause : les `UPDATE` SQL qu'on a faits pour filtrer
   par volume ont écrasé le sens original du flag.

**Ce que je teste :**
- Diagnostic 1 : combien de marchés par année de `end_ts` ? Si 2027-2028
  sont représentés, c'est qu'on a des marchés "futurs" classés closed.
- Diagnostic 2 : compte explicite des marchés avec `end_ts > maintenant`.
- Diagnostic 3 : tableau croisé entre l'âge réel des marchés et le flag
  holdout pour voir si les deux concepts ont été décorrélés.

**Pourquoi c'est crucial scientifiquement :**
Si je calcule "miscalibration à T-24h avant résolution" sur un marché qui
n'a pas vraiment été résolu (annulé, archivé, futur), le calcul est faux.
Mes tests d'hypothèse seront contaminés par du bruit qui n'a aucun sens.

**Leçon méthodologique :**
**Ne jamais faire confiance aux flags hérités.** Toujours vérifier que la
sémantique d'un champ correspond à ce qu'on croit, surtout après des
opérations SQL en masse. C'est un piège classique en data science.

## Cellule 8 — Recalcul propre des flags

**Diagnostic confirmé :** le flag `holdout` original ne signifie plus
"résolu il y a < 30 jours" mais un mélange de "récent" et "petit volume",
suite aux UPDATEs SQL qu'on a faits pour filtrer la collecte de prix.

**Ce que je fais :**
Je **ne modifie PAS la base** (principe : ne pas écraser des données brutes).
J'ajoute 4 colonnes calculées au DataFrame en mémoire :

1. `truly_resolved` = closed=1 ET end_ts <= maintenant ET outcome valide
2. `resolution_age_days` = combien de jours depuis la résolution
3. `truly_holdout` = truly_resolved ET résolu il y a < 30 jours
4. `analysis_set` = truly_resolved ET PAS truly_holdout

**Pourquoi cette discipline :**
- Les colonnes brutes `closed` et `holdout` sont préservées (audit trail)
- Mes calculs sont **transparents et reproductibles** : n'importe qui lisant
  le notebook comprend exactement comment `analysis_set` est défini
- Si demain je change la définition (ex: 60 jours au lieu de 30), je modifie
  une seule ligne et tout se recalcule automatiquement

**Concept général : "computed columns in-memory":**
C'est un pattern standard en data science. On ne modifie jamais la source
brute (la DB), on dérive des colonnes calculées dans le DataFrame d'analyse.
La traçabilité est préservée, et on peut toujours revenir en arrière.

**Question recruteur potentielle :** "Pourquoi tu n'as pas juste fait un
UPDATE SQL pour corriger le flag dans la base ?"  
Réponse : (1) ça écraserait des données brutes, perte d'information, (2) le
notebook ne serait plus reproductible par quelqu'un qui clone le repo et
lance la collecte from scratch, (3) la définition du holdout est une
décision d'analyse qui doit vivre dans le notebook d'analyse, pas dans la
couche stockage.

## Cellules 9-10 — Distribution des résultats YES/NO

**Question scientifique :** est-ce que les marchés se résolvent à ~50%
comme on s'y attendrait naïvement, ou y a-t-il un biais ?

**Ce que je trouve :** YES = 41.3%, NO = 58.7%. **Déséquilibre clair de 17
points de pourcentage.**

**Pourquoi c'est important :**
1. **Pour H1 (calibration)** : si je teste "les prix à 50% sous-estiment",
   il faut comparer à 41.3% (la base rate réelle) et pas à 50%. Sinon je
   conclus à un biais qui n'existe pas.
2. **Pour une stratégie naïve** : "tout acheter NO à 50%" aurait un EV positif
   en moyenne mais c'est trop simple — ça reflète juste la base rate, pas
   un edge informatif.
3. **Pour la sélection de marchés** : certaines catégories sont à 80% NO
   (questions "spéculatives") et d'autres à 50% (sports). Ne pas mélanger.

**Choix de design du graphique :**
- **Pie chart** pour l'overview : adapté à 2 catégories simples (YES/NO).
  Au-delà de 4 catégories, un pie chart devient illisible — on prendrait
  des barres.
- **Barres empilées horizontales par catégorie** : permet de comparer les
  proportions plutôt que les volumes. La ligne pointillée à 50% donne le
  repère visuel.
- **Filtre `n_markets >= 100`** : éviter de classer en "extrême" une catégorie
  avec 5 marchés où l'effet est purement du au hasard.

**Concept statistique : base rate fallacy**
Si je vois un marché à 60% YES et qu'il se résout YES, je pourrais croire
que "60% c'est sous-évalué". Mais si la base rate de la catégorie est de
70%, alors 60% est en fait sur-évalué. **Toujours comparer à la base rate
conditionnelle, pas à 50%.**

**Question recruteur potentielle :** "Comment tu interprètes ce 41% global ?"  
Réponse : trois hypothèses non exclusives — (1) biais de framing par les
créateurs de marchés (les questions sont plus souvent formulées en mode
"est-ce que X va arriver" où la réponse par défaut est NO), (2) sélection
adverse (les marchés où il y a doute sont plus créés que ceux où c'est
évident), (3) biais de catégorie (mix des catégories favorisant les
"questions spéculatives"). Pour discriminer, il faudrait analyser le mix
de catégories au cours du temps et la distribution des prix d'ouverture.


## Cellule 11 — Dérivation des catégories depuis les slugs

**Problème détecté :** la colonne `category` est NULL pour 100% des marchés.
Le champ `tags_json` brut renvoyé par Gamma est vide (`[]`). L'API a
probablement déprécié les tags individuels au profit des tags d'events.

**Solution adoptée :** classifier par règles sur le slug du marché.

**Pourquoi par règles et pas par ML :**
- 67 081 marchés à classer, pas un volume justifiant l'ML
- Les slugs ont des préfixes très réguliers (`btc-`, `nba-`, `atp-`, etc.)
- Interprétable et débogable : si une règle est mal calibrée, je vois
  exactement laquelle dans le code
- Reproductible à 100% : pas de dépendance à un modèle ou une seed

**Catégories définies :**
crypto, esports, sports, politics, geopolitics, macro, entertainment, other

**Limites assumées :**
- "other" capturera les marchés qui ne matchent aucun pattern
- Quelques faux positifs possibles (ex : un slug contenant "trump" mais
  parlant d'un projet immobilier — peu probable mais possible)
- Pas exhaustif : on raffinera si on voit des patterns importants dans
  l'échantillon "other"

**Discipline scientifique :** on ne modifie PAS la base. La catégorie
dérivée est une **colonne calculée en mémoire** dans le DataFrame.
Si plus tard on change les règles, il suffit de ré-exécuter cette cellule.

**Pour le journal de recherche (TODO) :**
- [ ] Patcher `data/collector.py` pour extraire la catégorie depuis
      `events[0].title` ou un mapping slug → category lors de la collecte
- [ ] Considérer d'enrichir avec les events groups Polymarket pour
      avoir des catégories plus fines

## Cellule 12 — Amélioration des règles de catégorisation

**Constat de la v1 :** 44% des marchés en "other", trop élevé.
**Cause :** mes règles initiales avaient oublié plein de patterns courants
(solana, valorant, college basketball, soccer européen, météo, célébrités).

**Ce que je fais :** version 2 du classifier avec :
- Plus de préfixes crypto (solana, ada, bnb, matic, etc.)
- Plus de préfixes esports (val, r6, apex, ow)
- Beaucoup plus de préfixes sports (cbb, ncaaf, mls, golf, rugby)
- Nouvelle catégorie "weather" (météo) qu'on avait ratée
- Nouvelle catégorie "celebrity" (Elon Musk, etc.)
- Mots-clés en plus du préfixe (équipes de foot, stars du tennis)

**Objectif :** descendre "other" sous 20%.

**Pourquoi c'est important :** une catégorie utile pour la stat doit être
précise. Si "other" reste à 40% et contient un mix de tout, mes tests
catégorie-par-catégorie sur "other" seront ininterprétables.

**Méthode itérative assumée :** on regarde, on raffine, on regarde, on
raffine. C'est normal en data engineering. Pas de honte à itérer ;
la honte c'est de prétendre avoir tout bien fait du premier coup.

## Cellule 12bis — Décision : on s'arrête à 76% de coverage

**Coverage atteinte :** 75.7% des marchés catégorisés.
**"Other" restant :** 16 292 marchés (24%).

**Pourquoi on n'itère pas plus :**
- Les 4 grandes catégories sont bien capturées
- Itérer pour passer de 76% à 90% prendrait 30 min pour un gain analytique marginal
- "Other" peut être traité comme une catégorie à part entière dans les tests
  stratifiés, sans biaiser les conclusions sur les autres catégories
- Le perfectionnisme sur la catégorisation distrait du vrai objectif (tester
  les hypothèses scientifiques)

**Limite assumée :** dans le rapport final, on mentionnera que "other"
contient probablement un mix de stocks individuels, ligues sportives mineures,
et questions atypiques. Les conclusions par catégorie ne s'appliqueront pas
à "other".

---

## Cellule 10 (relancée) — Visualisation YES/NO par catégorie

**Ce qui change :** on utilise `category_derived` au lieu de `category`
(NULL), et on exclut "other" du graphique pour ne montrer que les catégories
informatives.

**Ce qu'on cherche à voir :**
1. Est-ce que la base rate YES varie significativement selon la catégorie ?
2. Quelles catégories sont les plus déséquilibrées (donc à analyser séparément
   dans les tests d'hypothèse) ?

**Pourquoi c'est important pour H1 :**
H1 teste si "les marchés à 80% se résolvent à 80%". Mais si la base rate de
crypto est à 30% YES et celle de sports à 50% YES, alors un marché crypto à
80% n'est pas comparable à un marché sports à 80%. La stratification par
catégorie est essentielle.

## Section 4 — Distribution des volumes

**Question :** combien d'argent a vraiment été échangé sur ces marchés ?

**Pourquoi c'est crucial :**
- Les marchés à très faible volume ont des prix peu informatifs (peu de monde
  a "voté avec son portefeuille")
- Pour H1 (calibration), on voudra probablement filtrer sur volume > seuil
  pour ne tester que des marchés où le prix reflète une vraie agrégation
- Pour le backtest futur, on ne pourra pas trader sur des marchés sans
  liquidité (impossible d'entrer/sortir des positions)

**Pourquoi log scale :**
La distribution est probablement très étendue (de $1 à $10M+). Sur une échelle
linéaire, on ne verrait que la queue à droite et tout serait écrasé à zéro.
**Le log10 transforme une distribution étendue sur 7 ordres de grandeur en
une distribution exploitable visuellement.**

**Le CDF (Cumulative Distribution Function) :**
Pour chaque valeur x, le CDF montre la fraction des observations ≤ x. Si la
courbe est lisse, la distribution est continue. **Si elle a des marches
plates (= des sauts verticaux brusques), ça signale qu'il y a des valeurs
"interdites" entre les marches** = bucketisation.

**Concept statistique : heavy-tailed distribution**
Quand la moyenne est très supérieure à la médiane, ça révèle une distribution
où quelques observations extrêmes tirent la moyenne vers le haut. C'est la
loi de Pareto en action : 1% des marchés concentre 80% du volume.

**Question recruteur potentielle :** "Comment tu choisirais le seuil de
volume pour ton analyse ?"  
Réponse : trade-off entre puissance statistique (plus de marchés = mieux)
et qualité du signal (volume trop bas = bruit). Je regarderais où la courbe
de Brier score se stabilise en fonction du seuil de volume — c'est le point
où ajouter des marchés moins liquides ne dégrade plus la qualité de mes prix.

## Section 4 (suite) — Bucketisation confirmée

**Résultat majeur :** le champ `volume_total_usd` de Gamma API est bucketisé
en seulement ~4 paliers :
- Bucket 1 : < $100 (40k marchés)
- Bucket 2 : $100-$999 (16k marchés)
- Bucket 3 : $1k-$9k (24k marchés)
- Bucket 4 : $10k-$99k (16k marchés)
- Bucket 5 : $100k+ (2.5k marchés)

**Preuve :** `count(vol >= $1k) = count(vol >= $5k) = 43,069`. Impossible
statistiquement si la distribution était continue.

**Implication méthodologique :**
Ce champ ne peut PAS être utilisé comme variable continue dans une régression.
Il doit être traité comme une variable catégorielle ordinale (low, medium,
high, very-high). Dans un éventuel modèle de scoring, cette information
est toujours utile comme signal de liquidité — juste pas comme mesure
précise du volume.

**À inclure dans le papier final :** c'est un résultat méthodologique
valable à documenter. Les futurs chercheurs utilisant l'API Gamma doivent
savoir que ce champ est bucketisé.

---

## Section 5 — Durées de marché

**Question :** sur quels horizons temporels ces marchés opèrent-ils ?

**Pourquoi c'est crucial :**
- Un marché de 2h ("BTC > $X à 16h") est très différent d'un marché de 6 mois
  ("Trump élu 2028"). Les mécanismes de prix ne sont pas les mêmes.
- H2 (late resolution drift à T-48h) n'a aucun sens sur un marché de 24h
  total. On devra filtrer.
- Les marchés très courts sont souvent dominés par des bots de market-making,
  pas par de l'information agrégée. Prix peu informatif.

**Méthode :**
- Histogramme log(durée) pour voir la distribution sur toute l'échelle
- Boxplots par catégorie pour comparer les profils temporels
- Statistiques par bucket de durée pour décider des seuils d'analyse

**Concept statistique : log scale pour les données très étendues**
Les durées vont de quelques heures à 2 ans = 4 ordres de grandeur.
Sur échelle linéaire, on ne verrait que la queue droite. Sur log, tout
est visible et on peut comparer les modes de la distribution.

## Section 6 — Prix à T-24h (cellule 18)

**Ce que je fais :**
Pour chaque marché résolu, je récupère le prix YES 24 heures avant la
clôture. Ce sera la "prédiction du marché" que je comparerai à l'issue
réelle dans le notebook 02.

**Méthode utilisée : `pandas.merge_asof`**
C'est une fonction pandas conçue spécifiquement pour les jointures
temporelles. Pour chaque marché, elle cherche le prix le plus récent
dont le timestamp est ≤ (end_ts - 24h). Jamais de prix du futur.
Complexité O(n log n), en pratique <5 secondes sur 1.4M prix.

**Point critique — anti-leakage :**
Le paramètre `direction="backward"` garantit qu'on ne prend que des prix
antérieurs à la cible. Si je me trompais et prenais un prix à T-23h30
(plus récent que T-24h), j'utiliserais une information future par
rapport à mon moment de décision théorique. **C'est exactement le look-ahead
bias qu'il faut éviter en finance quantitative.**

**Bug rencontré :** `MergeError: incompatible merge keys dtype('float64')
and dtype('int64')`. Cause : quand une colonne int contient un seul NaN,
pandas la convertit silencieusement en float. Solution : forcer `.astype("int64")`
sur les deux colonnes de fusion après nettoyage.

**Leçon :** avant tout `merge_asof`, imprimer `df.dtypes` des deux côtés.
C'est le 1er réflexe à prendre.

---

## Section 7 — Sanity Checks (cellule 21)

**Ce que je teste :**
6 vérifications de cohérence avant de passer à l'analyse statistique :
1. Durées négatives ou nulles → 764 marchés problématiques (à exclure)
2. Prix hors de [0,1] → 0 ✓
3. Duplicate market_ids → 0 ✓
4. Outcomes NULL dans analysis_set → 0 ✓
5. Prix aux extrêmes exacts (0.0, 0.5, 1.0)
6. Corrélation prix-outcome et Brier score (preview de H1)

**Résultats clés :**
- Corrélation = 0.54 : prix **informatifs mais imparfaits**. Exactement ce
  qu'il nous faut pour avoir une chance de détecter un biais exploitable.
- Brier score = 0.17 : meilleur qu'aléatoire (0.25) mais pas parfait (0.0).
- 2 731 marchés exactement à 0.5 : symptôme fort d'illiquidité. Il faudra
  probablement les exclure ou les traiter à part dans les analyses.

**Aperçu de H1 dans le tableau des déciles :**
Calibration globale correcte, deux anomalies potentielles aux extrêmes.
Le vrai test formel (chi², intervalles de confiance bootstrap, correction
de Bonferroni) se fait dans le notebook 02.

**Pourquoi le Brier score est un outil puissant :**
C'est l'équivalent du "mean squared error" pour les probabilités binaires.
Il combine calibration (est-ce que 80% veut dire 80% ?) et résolution
(les prédictions sont-elles différenciées ?). Décomposition de Murphy :
Brier = Reliability - Resolution + Uncertainty.

---

## Section 8 — Conclusion (cellule 22)

Synthèse des résultats et roadmap pour les notebooks 02/03/04.

---

# 🎓 Comprendre le notebook 01 pour un débutant complet

*Si tu lis ce document sans rien connaître à la finance ni aux statistiques,
commence par ici. Tout est expliqué avec des mots simples et des exemples.*

## Le contexte : c'est quoi Polymarket ?

Imagine un site internet où tu peux parier sur tout ce qui va se passer
dans le monde. Par exemple :

- "Est-ce que Marseille va gagner la Ligue 1 cette saison ?"
- "Est-ce que le prix du Bitcoin va dépasser 150 000 $ avant fin 2026 ?"
- "Est-ce que Trump va faire une visite en Russie avant juin ?"

Sur Polymarket, chaque question a deux réponses possibles : **OUI** (YES)
ou **NON** (NO). Tu peux acheter des "parts OUI" ou des "parts NON".

**Le mécanisme des prix :**
- Chaque part coûte entre 0 centime et 1 dollar
- Si tu achètes une part OUI à 30 centimes et que la réponse est finalement OUI,
  tu gagnes 1 dollar (donc un profit de 70 centimes)
- Si la réponse est NON, tu perds tes 30 centimes

**Le prix reflète une probabilité :**
Si beaucoup de gens achètent des parts OUI, leur prix monte. Si beaucoup
achètent NON, le prix OUI baisse. Donc **le prix d'une part OUI représente
ce que le marché estime être la probabilité que la réponse soit OUI**.

- Prix OUI à 0.80 = le marché pense qu'il y a 80% de chances que ce soit OUI
- Prix OUI à 0.15 = le marché pense qu'il y a 15% de chances

Ces prix ressemblent aux cotes des bookmakers sportifs, sauf qu'ici ce sont
les parieurs eux-mêmes qui fixent les prix par leurs achats et leurs ventes.

---

## La question centrale du projet

**Est-ce que les prix Polymarket sont "bien calibrés" ?**

Traduit simplement : quand le marché dit "80% de chances", est-ce que ça
arrive vraiment 80% du temps ? Ou y a-t-il un biais systématique ?

### Pourquoi c'est intéressant

Si on trouve un biais systématique, on peut le **transformer en stratégie
rentable**. Exemple imaginaire :

*"Quand le marché dit 80%, ça arrive en fait 85% du temps."*

Alors acheter des parts OUI à 0.80 serait rentable en moyenne, parce que
la vraie probabilité est 0.85 et pas 0.80. On gagnerait 5 centimes d'espérance
par trade.

Ce genre de biais existe dans la littérature académique sur les paris
hippiques (le "favorite-longshot bias" découvert en 1949 par Griffith).
On veut voir s'il existe sur Polymarket.

---

## Ce qu'on a fait dans le notebook 01 : raconté comme une enquête

### Étape 1 : collecter les données

J'ai utilisé l'API publique de Polymarket (un accès programmatique gratuit
aux données) pour télécharger les informations de **99 999 marchés qui se
sont terminés**. Pour chacun, j'ai récupéré :

- La question posée ("Will Bitcoin exceed $110k on September 26?")
- La catégorie (sport, crypto, politique...)
- La date d'ouverture et de fermeture
- Le résultat final (OUI ou NON)
- L'historique des prix (le prix à chaque moment, toutes les 12 heures)

Total récupéré : **1.36 million de points de prix** à travers 46 930 séries
temporelles. Ça représente plusieurs heures de téléchargement.

### Étape 2 : nettoyer les données

Les données brutes ne sont jamais utilisables directement. J'ai découvert :

**Problème A** : l'API m'a donné 99 999 marchés alors que je demandais seulement
les 12 derniers mois. Cause : un bug de pagination côté API. J'ai décidé de
garder tous les marchés, ça me fait plus de données = meilleure statistique.

**Problème B** : Polymarket a un "drapeau holdout" qui marque les marchés
résolus très récemment (moins de 30 jours), qu'on ne doit PAS utiliser pour
nos tests (sinon on risque de "tricher" en ayant vu l'issue).

Mais en faisant des filtres SQL pour ne garder que les gros marchés, j'ai
**accidentellement écrasé ce drapeau**. Résultat : 75 000 marchés étaient
marqués "holdout" alors qu'ils ne devaient pas l'être.

J'ai reconstruit un drapeau propre à partir des dates de résolution. Leçon :
ne jamais faire confiance à un drapeau calculé, toujours le recalculer à
partir des données brutes.

**Problème C** : la colonne "catégorie" était **vide pour tous les marchés**
(l'API a changé son format). J'ai donc construit un petit classifieur basé
sur l'URL de chaque marché. Par exemple :
- `btc-above-100k-2025` → catégorie "crypto"
- `nba-lakers-vs-celtics` → catégorie "sports"
- `will-temperature-exceed-80f` → catégorie "weather"

Couverture obtenue : 76% des marchés correctement catégorisés.

### Étape 3 : explorer les données avec des graphiques

Maintenant qu'on a un dataset propre de **67 081 marchés**, on regarde
à quoi ça ressemble.

**Découverte 1 : les issues sont déséquilibrées**

Sur les 67 081 marchés, seulement **41% se résolvent OUI**. Les 59% restants
se résolvent NON. Pourquoi ? Deux explications plausibles :

- **Biais de formulation** : les questions sont souvent formulées "Est-ce que
  X va arriver ?" où la réponse par défaut est NON.
- **Biais de catégorie** : certaines catégories sont très déséquilibrées.
  Par exemple "weather" (météo) est à 85% NON parce que les questions
  demandent des valeurs précises (ex: température entre 76 et 77°F) qui
  arrivent rarement.

**Conséquence importante** : on ne peut pas naïvement dire "un marché à 50%
devrait être OUI 50% du temps". Il faut comparer au **taux de base de la
catégorie**, pas à 50%.

**Découverte 2 : les volumes sont "bucketisés"**

Polymarket affiche pour chaque marché son volume total en dollars (combien
d'argent a été échangé). Normalement cette valeur devrait être continue
(n'importe quel nombre entre 0 et 10 millions).

**Mais** : en regardant les données, j'ai remarqué que **tous les volumes
tombent dans environ 4 "cases" fixes** :
- Moins de 100$
- Entre 1 000$ et 9 999$
- Entre 10 000$ et 99 999$
- Plus de 100 000$

C'est comme si Polymarket arrondissait tous les volumes à ces paliers. On ne
peut donc pas utiliser le volume comme une valeur précise, seulement comme
une indication grossière.

**Découverte 3 : les marchés sont très courts**

29% des marchés durent moins de **24 heures** (questions type "Bitcoin > X
aujourd'hui"). 75% durent moins d'une semaine. Les marchés longue durée
(> 1 mois) sont rares.

Implication : pour tester l'hypothèse H2 (dérive dans les 48h avant
résolution), on devra exclure les 29% de marchés trop courts.

### Étape 4 : le cœur de l'analyse — les prix à T-24h

Pour chaque marché, j'ai extrait le prix exactement **24 heures avant
la fermeture**. C'est ce prix qu'on va comparer au résultat réel.

**Technique utilisée : "merge as-of"**

Imagine que tu as 11 340 marchés et 1.36 million de points de prix. Pour
chaque marché, tu veux trouver le point de prix le plus récent dont le
timestamp est antérieur à (fermeture - 24h). C'est comme chercher une
aiguille dans une botte de foin, pour chaque marché.

Pandas (une bibliothèque Python) a une fonction magique pour ça :
`merge_asof`. Elle fait ce travail en **5 secondes au lieu de 3 minutes**
avec une boucle naïve.

**Pourquoi "as-of" et pas "as-at"** : "as-of" signifie "à la date la plus
récente jusqu'à cette date". On ne doit **jamais** prendre un prix futur
par rapport au moment de la décision, sinon on "triche" (on utilise de
l'information qu'on n'aurait pas eue en vrai).

En finance, utiliser des données du futur pour prédire le passé s'appelle
le "look-ahead bias" et c'est l'erreur numéro 1 des backtests amateur.

### Étape 5 : premiers résultats

Sur les 11 340 marchés avec un prix à T-24h valide :

**Corrélation entre prix et résultat : 0.54**

Traduit : quand le marché prédit 80%, c'est plus souvent OUI que quand il
prédit 20%. Donc le marché n'est pas aveugle, il a une certaine capacité
prédictive. Mais 0.54 n'est pas 1, donc les prédictions sont imparfaites.

**Brier score : 0.17**

Le Brier score mesure l'erreur moyenne des prédictions. Plus c'est bas,
mieux c'est. Pour référence :
- 0.0 = prédiction parfaite
- 0.25 = prédiction aléatoire (pile ou face)
- 0.17 = mieux qu'aléatoire mais pas parfait

Donc oui, le marché a de la valeur prédictive, mais il reste de la place
pour détecter des biais exploitables.

**Tableau par tranche de prix (la donnée centrale)** :

| Tranche de prix | Nombre de marchés | Taux OUI réel |
|---|---|---|
| 0-10% | 2 717 | 2% |
| 10-20% | 551 | 18% |
| 20-30% | 766 | 33% |
| 30-40% | 736 | 41% |
| 40-50% | 3 762 | 50% |
| 50-60% | 1 073 | 48% |
| 60-70% | 465 | 62% |
| 70-80% | 357 | 71% |
| 80-90% | 245 | 87% |
| 90-100% | à venir | à venir |

**Ce qu'on voit** :
- Dans les cases extrêmes (0-10% et 80-90%), le taux réel est **un peu
  différent** du prix prédit. Exemple : cases 20-30% = 33% de OUI au lieu
  de ~25% attendus. Ça semble suggérer que le marché sous-estime les
  outsiders.
- Dans les cases du milieu, c'est plus calibré.

**Est-ce un vrai biais ou du bruit ?** C'est exactement la question que le
notebook 02 va trancher avec des tests statistiques formels.

---

## Ce qu'on n'a PAS fait dans ce notebook

- On n'a pas testé formellement les hypothèses. Tout est en exploration.
- On n'a pas utilisé de modèle prédictif avancé (machine learning).
- On n'a pas backtesté de stratégie de trading.
- On n'a pas touché aux données "holdout" (les 30 derniers jours),
  réservées pour la validation finale.

Le notebook 02 fait le test formel. Le notebook 03 teste la dérive temporelle.
Le backtest arrive plus tard.

---

## Vocabulaire clé introduit dans ce notebook

**Prix à T-24h** : le prix d'une part OUI exactement 24 heures avant la
fermeture du marché. C'est notre "prédiction" que le marché fait.

**Taux de base (base rate)** : la proportion de marchés qui se résolvent OUI
dans l'ensemble du dataset. Chez nous : 41%.

**Bin / Tranche / Décile** : un intervalle dans lequel on regroupe des
valeurs. Exemple : "tous les marchés avec un prix entre 0.8 et 0.9".

**Brier score** : mesure d'erreur des prédictions probabilistes. Formule :
moyenne de (prédiction − réalité)². Parfait = 0, aléatoire = 0.25.

**Holdout** : portion des données qu'on met de côté et qu'on ne regarde
**jamais** avant la validation finale, pour éviter de biaiser nos choix
méthodologiques.

**Merge as-of** : fonction Python qui joint deux séries temporelles en
prenant la valeur la plus récente antérieure ou égale à la date cible.
Standard pour éviter le look-ahead bias.

**Look-ahead bias** : erreur méthodologique consistant à utiliser dans son
analyse une information qui n'était pas disponible au moment où la décision
aurait été prise. Tue la crédibilité de tout backtest.

**Catégorie dérivée** : catégorie calculée par nous à partir de l'URL du
marché, parce que Polymarket ne la fournit plus directement.

