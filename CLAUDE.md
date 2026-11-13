# OptionLab — contexte pour Claude Code

Plateforme éducative sur les options (projet étudiant, ESILV, orientation ingénierie financière). Langue de l'interface et des messages : français.

## Architecture
- `backend/optionlab/` : moteur de calcul en Python pur (numpy/scipy), sans dépendance web. Toute la finance vit ici.
- `backend/app/main.py` : API FastAPI (schémas pydantic) qui appelle le moteur et sert `frontend/` sur `/` et `/static`.
- `backend/optionlab/hedging.py` : simulation de delta hedging vectorisée (numpy). `marketdata.py` : yfinance + vol historique (cache 15 min).
- `frontend/` : HTML/CSS/JS vanilla + Plotly (CDN). Pas de build. Toutes les requêtes passent par `post()` dans `app.js`.
- `backend/app/db.py` : adaptateur maison sans ORM (SQLite local/tests, PostgreSQL via psycopg si DATABASE_URL). Requêtes avec « ? ».
- `backend/app/auth.py`, `portfolio.py` : logique métier testée sans FastAPI ; `routes_portfolio.py` : routes. `frontend/portfolio.js` : onglet Portefeuille.
- `backend/app/advisor.py` (alertes déterministes), `coach.py` (API Claude via urllib, outils proposer_strategie / proposer_ordre, quotas dans la table coach_usage), `insights.py` (Finnhub, cache 30 min) ; routes dans `routes_coach.py`. Tests avec appels simulés (`caller`, `news_fetch`), jamais d'appel réseau en test.
- `frontend/trading.html` (page d'accueil, servie sur `/` ; le labo `index.html` est sur `/labo`, `/trading` redirige vers `/`) : page autonome « Trading Pas à Pas » (cours débutant, lexique, simulateur). Elle lit les bougies réelles d'une minute via `/api/trading/candles/{ticker}` (`backend/optionlab/intraday.py`, yfinance, cache 1 min, liste fermée TRADING_TICKERS) et repasse en prix simulés si l'API ne répond pas. Le compte du simulateur vit dans le navigateur, pas en base.
- `frontend/lessons.js` : contenu des cours (tableau LESSONS). Les chiffres cités dans les leçons doivent être recalculés avec le moteur si on les modifie.

## Commandes
- Lancer : `cd backend && uvicorn app.main:app --reload`
- Tests : `cd backend && pytest -q` (lancer après chaque modification du moteur)

## Règles
- Conventions financières : T en années, taux/vol en décimal, vega et rho pour 1 %, theta par jour.
- Toute nouvelle formule de pricing doit avoir un test (valeur de référence, parité, ou comparaison avec une autre méthode).
- Les erreurs métier lèvent `ValueError` (message en français) ; l'API les convertit en HTTP 400.
- Garder le moteur indépendant de FastAPI.
- Mention « outil éducatif, pas de conseil en investissement » à conserver.
- Ne jamais stocker de mot de passe en clair ; ne jamais exposer l'email dans le classement.
- Le coach ne passe jamais d'ordre lui-même : il propose, le joueur valide. Ne jamais envoyer l'email du joueur au modèle ; le contenu externe (actualités) reste encadré comme données.
- Les clés API (ANTHROPIC_API_KEY, FINNHUB_API_KEY) vivent uniquement dans les variables d'environnement de Render, jamais dans le code.
