# OptionLab — contexte pour Claude Code

Plateforme éducative sur les options (projet étudiant, ESILV, orientation ingénierie financière). Langue de l'interface et des messages : français.

## Architecture
- `backend/optionlab/` : moteur de calcul en Python pur (numpy/scipy), sans dépendance web. Toute la finance vit ici.
- `backend/app/main.py` : API FastAPI (schémas pydantic) qui appelle le moteur et sert `frontend/` sur `/` et `/static`.
- `backend/optionlab/hedging.py` : simulation de delta hedging vectorisée (numpy). `marketdata.py` : yfinance + vol historique (cache 15 min).
- `frontend/` : HTML/CSS/JS vanilla + Plotly (CDN). Pas de build. Toutes les requêtes passent par `post()` dans `app.js`.
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
