"""Routes de l'accompagnement : analyse automatique, coach IA et données Finnhub."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import coach, insights
from . import portfolio as pf
from .advisor import analyze
from .routes_portfolio import current_user, get_db, get_provider

router = APIRouter(prefix="/api")
log = logging.getLogger("optionlab.coach")


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class CoachIn(BaseModel):
    question: str = Field(..., max_length=coach.MAX_QUESTION)
    view: Literal["", "haussier", "baissier", "neutre", "volatil", "prudent"] = ""
    history: list[HistoryItem] = Field(default_factory=list, max_length=12)


@router.get("/coach/analysis")
def coach_analysis(user=Depends(current_user), db=Depends(get_db), provider=Depends(get_provider)):
    try:
        data = pf.portfolio(db, user["id"], provider)
    except pf.TradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {**analyze(data), "coach_enabled": coach.enabled(),
            "remaining": coach.remaining(db, user["id"]) if coach.enabled() else 0}


@router.post("/coach")
def ask_coach(body: CoachIn, request: Request, user=Depends(current_user), db=Depends(get_db),
              provider=Depends(get_provider)):
    caller = getattr(request.app.state, "coach_caller", None)
    news_fetch = getattr(request.app.state, "news_fetch", None)
    try:
        data = pf.portfolio(db, user["id"], provider)
        return coach.ask(db, user["id"], data, body.question, body.view,
                         [h.model_dump() for h in body.history], caller=caller, news_fetch=news_fetch)
    except (coach.CoachError, pf.TradeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        log.exception("Erreur du coach")
        raise HTTPException(status_code=502, detail="Le coach a rencontré un problème, réessaie.")


@router.get("/insights/{ticker}")
def get_insights(ticker: str, request: Request):
    if not coach._TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Ticker invalide.")
    fetch = getattr(request.app.state, "news_fetch", None)
    return fetch(ticker) if fetch else insights.fetch_insights(ticker)
