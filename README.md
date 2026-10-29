# OptionLab — Labo de produits dérivés

Plateforme web éducative pour comprendre les options : pricing Black-Scholes, greeks, volatilité implicite et construction de stratégies (straddle, spreads, butterfly, iron condor…) avec graphiques de P&L interactifs.

> Projet éducatif : modèles théoriques et simulations, aucun conseil en investissement.

## Fonctionnalités

- **Stratégies** : 11 stratégies prêtes à l'emploi ou construction libre (jusqu'à 8 jambes : calls, puts, actions, achat/vente). Courbes de P&L à l'échéance, à mi-parcours et aujourd'hui, coût net, gain/perte max (détection de l'illimité), points morts, greeks agrégés.
- **Pricer** : Black-Scholes-Merton (avec dividende), arbre binomial CRR (européen et américain), Monte-Carlo (variables antithétiques, intervalle de confiance), courbes du prix et des greeks selon le spot.
- **Volatilité implicite** : Newton-Raphson avec repli sur la dichotomie, contrôle des bornes d'arbitrage.
- **Données réelles** : saisie d'un ticker Yahoo Finance (AAPL, TTE.PA, ^GSPC…) qui remplit le spot, la volatilité historique et le dividende.
- **Couverture (delta hedging)** : simulation Monte-Carlo d'une banque qui vend une option et se couvre ; effet de la fréquence de rebalancement, de l'écart vol réalisée / vol implicite, de la tendance et des frais.
- **Apprendre** : 15 leçons en 5 modules (bases, pricing, greeks, stratégies, couverture), 45 questions de quiz corrigées, boutons « essayer dans le labo », progression sauvegardée dans le navigateur.
- **API REST** documentée automatiquement (Swagger sur `/docs`).

## Structure

```
optionlab/
├── backend/
│   ├── optionlab/          # moteur de calcul (Python pur, testé)
│   │   ├── pricing.py      # Black-Scholes, greeks, vol implicite, binomial, Monte-Carlo
│   │   ├── strategies.py   # jambes, stratégies, P&L, points morts, presets
│   │   ├── hedging.py      # simulation de delta hedging
│   │   └── marketdata.py   # données Yahoo Finance, volatilité historique
│   ├── app/main.py         # API FastAPI + service du frontend
│   ├── tests/              # pytest (parité call-put, greeks vs différences finies, etc.)
│   └── requirements.txt
├── frontend/               # HTML/CSS/JS sans framework + Plotly (lessons.js = contenu des cours)
├── render.yaml             # déploiement gratuit sur Render
└── CLAUDE.md               # contexte pour continuer le projet avec Claude Code
```

## Lancer en local

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate    macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Puis ouvrir http://127.0.0.1:8000 (interface) et http://127.0.0.1:8000/docs (API).

## Tests

```bash
cd backend
pytest -q
```

## Déployer sur Render (gratuit)

1. Pousser le projet sur GitHub.
2. Sur render.com : **New → Blueprint**, choisir le dépôt (le fichier `render.yaml` configure tout).
3. L'application est en ligne sur `https://<nom>.onrender.com`. (Sur l'offre gratuite, le premier chargement après une période d'inactivité prend ~30 s.)

## Endpoints

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/price` | Prix BS, binomial, américain, Monte-Carlo + greeks |
| POST | `/api/greeks-curve` | Prix et greeks selon le spot |
| POST | `/api/implied-vol` | Volatilité implicite |
| GET | `/api/presets` | Liste des stratégies prêtes |
| POST | `/api/presets/{key}` | Jambes d'une stratégie centrée sur le spot |
| POST | `/api/strategy` | Analyse complète d'une stratégie |
| POST | `/api/hedging` | Simulation de delta hedging |
| GET | `/api/market/{ticker}` | Cours, vol historique et dividende d'un titre réel |

## Conventions

- `T` en années, `r`, `q` et `sigma` en décimal (0.03 = 3 %).
- Vega et rho pour +1 point de %, theta par jour calendaire.
- Prime d'une jambe calculée par Black-Scholes aux paramètres du marché, sauf si `premium` est fourni.

## Pistes d'amélioration

- Smile de volatilité à partir de chaînes d'options réelles.
- Surface P&L 3D (spot × temps), heatmap des greeks.
- Comptes utilisateurs et portefeuille d'options virtuel (comme MAGAKE, mais en options).
- Couverture delta-gamma, options exotiques (barrières, asiatiques) en Monte-Carlo.
