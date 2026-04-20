# Paper Trading Bot

Bot qui simule la stratégie short-YES identifiée dans le projet, sans engager de capital réel.

## Lancement

```bash
cd paper_trading
python bot.py
```

Le bot tourne en boucle, fait un cycle toutes les heures :
1. Résout les positions ouvertes dont le marché s'est clôturé
2. Cherche les nouveaux marchés crypto à T-24h dans [0.50, 0.60]
3. Ouvre une position paper sur chacun

## Fichiers de log (dans `logs/`)

- `trades.csv` : historique complet des trades (ouverts + clôturés)
- `portfolio.csv` : snapshot du capital à chaque résolution
- `state.json` : état persistant (capital, positions ouvertes)
- `bot.log` : journal d'exécution du bot

## Arrêter le bot

Ctrl+C dans le terminal.

## Relancer

`python bot.py` : le bot reprend l'état depuis `state.json` et continue.

## Paramètres

Voir `config.py` pour :
- Capital initial (1000 USDC virtuels)
- Mise par trade (10 USDC)
- Filtres de la stratégie
- Coûts (fees 2%, slippage 0.5%)

## Analyse après 30 jours

Ouvrir `trades.csv` dans pandas ou Excel pour :
- Calculer le ROI réalisé
- Comparer au backtest (+18.8%)
- Mesurer le slippage réel vs hypothèse