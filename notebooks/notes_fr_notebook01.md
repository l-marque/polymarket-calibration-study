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

---

