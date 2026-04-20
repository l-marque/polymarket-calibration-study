# Notes en français — Notebook 04 (Cross-Market Arbitrage Analysis)

> Document de révision personnel. Explications en français de chaque cellule
> du notebook, avec questions potentielles en entretien.
>
> Voir aussi `concepts_theoriques.md` pour les définitions détaillées.

---

## Objectif du notebook 04

**Question scientifique centrale :** les marchés Polymarket qui portent sur
des événements liés (même catégorie, même semaine de résolution) montrent-ils
des mouvements de prix cohérents, comme le prédirait la théorie de l'arbitrage ?

**Méthode formelle :** on teste H3 (préenregistrée) via une version proxy :
1. Identification des "clusters" de marchés (même catégorie + même semaine)
2. Calcul de la concordance de signe des dérives au sein de chaque cluster
3. Test t one-sample contre H0 : concordance = 0.5 (indépendance)
4. Stratification par catégorie

**Sortie attendue :** verdict formel H3 acceptée, rejetée ou inconclusive.

---

## Résumé cellule par cellule

### Cellule 1 — Markdown d'en-tête

Déclaration formelle de H3 en version proxy. On explique pourquoi on ne
peut pas faire le test idéal (identifier des paires complémentaires exactes
P(A) + P(~A) = 1) avec nos données actuelles.

### Cellule 2 — Imports

Importations classiques + `itertools.combinations` pour générer les paires
de marchés au sein de chaque cluster.

### Cellule 3 — Chargement et clustering

**Ce qu'on fait :** on charge les données comme dans les notebooks précédents,
puis on crée un identifiant de cluster par concaténation de la catégorie et
de la semaine ISO de résolution.

Exemple : `crypto_2026-W15` = tous les marchés crypto qui se résolvent dans
la 15e semaine de 2026.

**Résultat :** 221 clusters identifiés, dont 171 à au moins 5 marchés
(taille minimum pour un test de concordance sensé). Les plus gros clusters
sont "other_*" avec jusqu'à 336 marchés.

**Pourquoi on filtre à ≥ 5 marchés :** en-dessous, les statistiques de
concordance sont trop instables (peu de paires = énorme variance).

### Cellules 4-5 — Calcul des concordances

**Métrique utilisée : sign concordance**

Pour chaque cluster, on prend toutes les paires possibles de marchés. Pour
chaque paire (i, j), on regarde si leurs dérives `drift_i` et `drift_j` ont
le même signe.

Formule : concordance = (nombre de paires avec même signe) / (nombre total de paires avec drift non-nul)

Sous H0 (marchés indépendants), la concordance attendue est 0.5 (50/50
chances que deux marchés aléatoires aient même signe).

**Résultat :**
- Mean concordance = 0.534
- Median concordance = 0.504
- Std = 0.166 (très hétérogène entre clusters)

**Test formel : t-test one-sample**
- t-statistic = 2.55
- p-value = 0.012
- Verdict : rejet de H0 au seuil 5%, mais PAS au seuil 1%

**Stratification par catégorie :**
- Weather : 0.67 (mais n=5, trop petit)
- Sports : 0.55 (léger excès positif)
- Crypto : 0.55 (léger excès positif)
- Other : 0.51 (quasi indifférent)
- Politics : 0.52 (quasi indifférent)
- Esports : 0.48 (légèrement négatif, mais n=9 donc bruit)

### Cellule 6 — Visualisation

**Panel gauche :** histogramme de la distribution des concordances par
cluster. On voit un pic centré sur 0.5, avec une queue à 1.0 (quelques
clusters où tout bouge ensemble).

**Panel droit :** concordance en fonction de la taille du cluster. Les
gros clusters (n > 100) convergent tous vers 0.5 (effet moyenne), les
petits clusters sont très dispersés (variance).

### Cellule 7 — Verdict JSON

Sauvegarde `h3_verdict.json` avec status = "inconclusive".

### Cellule 8 — Conclusion formelle

**H3 est inconclusive dans sa forme forte, faiblement supportée dans sa
forme faible.**

Les marchés co-bougent légèrement plus que le hasard (+3.4 pp), mais :
- L'effet est trop petit pour être exploitable (frais 2%)
- La variance entre clusters est énorme
- C'est un test proxy, pas un vrai test d'arbitrage

---

## 🎓 Comprendre le notebook 04 pour un débutant complet

*Ce texte suppose que tu as lu les versions débutant des notebooks 01, 02 et 03.*

## Le contexte : qu'est-ce qu'on teste ici ?

Dans le notebook 01 on a collecté et exploré les données.
Dans le notebook 02 on a testé si les prix étaient bien calibrés (H1).
Dans le notebook 03 on a testé si les mouvements de prix étaient informatifs (H2).

**Maintenant (notebook 04), on se demande :** est-ce que les marchés qui
portent sur des événements liés bougent de façon cohérente ?

### Exemple concret

Imagine le week-end de la NFL. Polymarket a **20 marchés ouverts** ce
week-end, tous sur des matchs de foot américain qui vont se jouer dimanche.

Quand un match commence, plein de choses changent en même temps :
- Le marché "Chiefs vont-ils gagner ?" bouge selon le score
- Le marché "Plus de 45 points au total ?" bouge aussi (parce que c'est
  le même match)
- Le marché "Chiefs vont-ils marquer plus de 28 points ?" aussi

**Question H3 simplifiée** : quand un marché bouge dans un sens, est-ce que
les marchés voisins bougent aussi dans un sens cohérent ? Ou chacun fait-il
sa vie tout seul ?

Si chacun fait sa vie → il peut y avoir de **l'arbitrage** (incohérences
exploitables). Si tout le monde bouge ensemble → marché efficient.

---

## Pourquoi c'est compliqué à tester

**Le vrai test idéal** serait de prendre une paire comme "Chiefs gagnent"
(à disons 0.65) et "Bills gagnent" (à 0.38). Si on suppose qu'il n'y a pas
de match nul, P(Chiefs) + P(Bills) devrait = 1.

Mais ici on a 0.65 + 0.38 = 1.03. **Il y a un arbitrage de 3 centimes** :
vendre les deux parts "OUI" donne 1.03 $ mais on ne paiera que 1 $ quand
l'un des deux gagne. Profit garanti de 3 centimes par paire (moins les frais).

**Le problème** : pour faire ce test, il faudrait **identifier les vraies
paires complémentaires** dans nos 100 000 marchés. C'est très compliqué
sans que Polymarket nous le dise directement.

---

## La solution adoptée : une version "proxy"

Au lieu de chercher des paires complémentaires exactes, on fait une
approximation :

**On groupe les marchés par "cluster"** = même catégorie (sport, crypto...)
et même semaine de résolution.

Ça donne des groupes comme :
- crypto_2026-W15 : tous les marchés crypto qui se résolvent en semaine 15 de 2026
- sports_2026-W05 : tous les marchés sport qui se résolvent en semaine 5

**Hypothèse** : les marchés dans un même cluster sont "liés" (ils portent
sur le même événement ou des événements proches).

**Test** : est-ce que les dérives T-48h → T-24h des marchés d'un cluster
bougent dans le même sens plus souvent que le hasard ?

---

## La métrique utilisée : "sign concordance"

On regarde juste le **signe** de la dérive (positif ou négatif), pas sa
magnitude.

Pour chaque paire de marchés (i, j) dans un cluster, on se demande : est-ce
que `drift_i` et `drift_j` ont le même signe ?

- Les deux ont monté → même signe positif → **concordant**
- Les deux ont baissé → même signe négatif → **concordant**
- Un a monté, l'autre a baissé → **discordant**

On calcule la fraction de paires concordantes dans le cluster.

**Sous H0 (indépendance)** : cette fraction devrait être 0.5. C'est comme
deux pièces qu'on lance : 50% de chances d'obtenir les deux face (même signe).

**Sous H1 (marchés liés)** : cette fraction devrait être > 0.5. Si les
marchés sont vraiment liés, ils tendent à bouger dans le même sens.

---

## Le test statistique : t-test one-sample

**Question formelle** : est-ce que la moyenne des concordances observées
sur les 171 clusters est significativement supérieure à 0.5 ?

On utilise un **t-test one-sample** (test de Student) qui répond à ça.

**Formule intuitive** : t = (moyenne_observée - 0.5) / (std / sqrt(n_clusters))

- Si t est grand (en valeur absolue), l'écart à 0.5 est "trop gros pour être
  du hasard"
- Si t est petit, ça peut facilement venir du bruit

On traduit t en p-value (comme on l'a fait pour H1 et H2).

---

## Les résultats : un résultat "entre les deux"

**Mean concordance = 0.534**, p-value = 0.012.

**Traduction** : les marchés dans un même cluster bougent ensemble
**3.4 points de pourcentage plus que le hasard**. C'est **statistiquement
significatif** (p < 0.05) mais **économiquement faible**.

Pourquoi économiquement faible ? Parce que :
1. Pour exploiter 3.4% d'edge directionnel, il faudrait une stratégie très
   précise (détecter quelle direction, avec quelle confiance)
2. Polymarket prend 2% de frais → on perd la moitié de l'edge dès le start
3. La variance entre clusters est énorme (std = 0.166) : certains clusters
   à 100%, d'autres à 0%

---

## Conclusion : H3 est "inconclusive"

**On ne rejette pas H0 au sens fort.** Le léger écart observé peut venir :
1. D'une vraie efficience approximative (les marchés liés coordonnent leurs
   prix, léger biais résiduel)
2. De notre proxy imparfait (certains clusters groupent des marchés non vraiment liés)
3. D'une inefficience réelle mais trop petite pour être exploitée

Pour trancher, il faudrait un vrai test de paires complémentaires, ce qui
est hors scope du projet actuel.

**Dans le papier final** : on présente H3 comme une **limitation du dataset
actuel** plutôt qu'un résultat fort.

---

## Ce que ce résultat dit quand même

**Même "inconclusive", c'est une information utile :**

1. **Polymarket n'est pas massivement inefficient.** Si les marchés liés
   bougeaient n'importe comment indépendamment les uns des autres, on verrait
   une concordance vers 0.5 avec gros écart. Ce qu'on voit est cohérent avec
   une efficience approximative.

2. **Pas de stratégie d'arbitrage évidente.** Si on avait trouvé concordance
   = 0.35 (plus bas que 0.5 de façon significative), ça aurait suggéré que
   les marchés liés bougent de façon **anti-corrélée**, ce qui serait un
   signal d'arbitrage énorme. On ne voit pas ça.

3. **Le résultat est cohérent avec H2.** H2 disait que les dérives sont
   informatives. Si elles sont informatives et que les marchés d'un cluster
   reçoivent la même information, ils devraient tendre à bouger ensemble.
   C'est exactement ce qu'on observe (légèrement).

---

## Limites à citer en entretien

Si on te questionne sur H3 :

1. **"C'est un test proxy"** : tu as fait au mieux avec les données disponibles,
   mais un vrai test nécessiterait de connaître les paires complémentaires.

2. **"Le clustering par catégorie + semaine est imparfait"** : certains
   clusters regroupent des marchés vraiment liés (même match), d'autres des
   marchés indépendants (deux matchs différents dans la même semaine).

3. **"La métrique de concordance ne capture que la direction, pas la
   magnitude"** : une corrélation de Pearson sur les dérives donnerait
   plus d'information, mais nécessite plus de données par cluster pour
   être stable.

**Ta réponse idéale** : "J'ai choisi une méthode proxy simple mais
défendable, et j'ai documenté honnêtement ses limites. Dans une extension
du projet, j'intégrerais un matching de slugs plus sophistiqué pour
identifier les vraies paires complémentaires."

---

## Vocabulaire clé introduit dans ce notebook

**Cluster** : groupe de marchés qui partagent une caractéristique commune
(ici : catégorie + semaine de résolution). Proxy des "événements liés".

**Arbitrage** : opportunité de profit sans risque, créée par des prix
incohérents entre marchés liés. Exemple : P(A) + P(non-A) > 1 permet de
vendre les deux et gagner la différence.

**Test t one-sample** : test statistique qui compare la moyenne d'un
échantillon à une valeur théorique fixée (ici 0.5). Retourne un t-statistic
et une p-value.

**Sign concordance** : métrique simple qui mesure si deux variables tendent
à avoir le même signe. Vaut 0.5 sous indépendance, 1 sous corrélation
parfaite positive, 0 sous corrélation parfaite négative.

**Proxy** : mesure indirecte utilisée à défaut d'une mesure idéale. Ici :
co-mouvement de cluster comme proxy d'arbitrage entre marchés complémentaires.

**Efficience approximative** : idée que les marchés incorporent la plupart
(mais pas toute) l'information disponible. Concept standard en finance
empirique (Fama 1970 définit plusieurs niveaux d'efficience).

---

## Fin du notebook 04

**Résultat principal** : H3 inconclusive — léger co-mouvement cohérent avec
efficience approximative, pas d'inefficience exploitable détectée.

**Bilan des 3 hypothèses du projet** :
- H1 : partiellement acceptée (biais crypto 0.5-0.6 significatif)
- H2 : acceptée avec hétérogénéité (drift informative dans crypto/other)
- H3 : inconclusive (pas d'arbitrage flagrant détecté)

**Implication générale** : Polymarket est approximativement efficient, avec
une poche résiduelle d'inefficience concentrée dans la catégorie crypto.