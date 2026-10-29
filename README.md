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
- **Portefeuille virtuel** : comptes utilisateurs, 100 000 crédits virtuels, achat/vente de calls et puts sur de vrais titres (bid/ask, marge pour la vente, règlement à l'échéance), positions valorisées en direct avec greeks, historique et classement des joueurs.
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
│   ├── app/
│   │   ├── main.py         # API FastAPI + service du frontend
│   │   ├── db.py           # accès base (SQLite en local, PostgreSQL si DATABASE_URL)
│   │   ├── auth.py         # comptes, mots de passe hachés (PBKDF2), sessions
│   │   ├── portfolio.py    # règles du portefeuille virtuel
│   │   └── routes_portfolio.py
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
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | Comptes (cookie de session HttpOnly) |
| GET | `/api/portfolio`, `/api/portfolio/history` | Portefeuille valorisé, historique |
| POST | `/api/portfolio/quote`, `/api/portfolio/orders` | Cotation, passage d'ordre |
| POST | `/api/portfolio/positions/{id}/close` | Clôture d'une position |
| GET | `/api/leaderboard` | Classement des joueurs |

## Base de données

En local, sans configuration, les comptes sont stockés dans `backend/optionlab.db` (SQLite, ignoré par Git).
En production, définir la variable d'environnement `DATABASE_URL` avec l'URL PostgreSQL (ex. Neon) :
`postgresql://utilisateur:motdepasse@hote/base?sslmode=require`. Les tables sont créées au démarrage.

## Conventions

- `T` en années, `r`, `q` et `sigma` en décimal (0.03 = 3 %).
- Vega et rho pour +1 point de %, theta par jour calendaire.
- Prime d'une jambe calculée par Black-Scholes aux paramètres du marché, sauf si `premium` est fourni.

## Pistes d'amélioration

- Smile de volatilité à partir de chaînes d'options réelles.
- Surface P&L 3D (spot × temps), heatmap des greeks.
- Ordres à cours limité, historique de la valeur du portefeuille, ligues entre amis.
- Couverture delta-gamma, options exotiques (barrières, asiatiques) en Monte-Carlo.
