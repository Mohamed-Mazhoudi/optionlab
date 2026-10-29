"""Routes de l'API : comptes, portefeuille virtuel, ordres et classement."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import auth
from . import portfolio as pf

router = APIRouter(prefix="/api")
COOKIE = "ol_session"


# ---------- schémas ----------
class RegisterIn(BaseModel):
    email: str = Field(..., max_length=254)
    username: str = Field(..., max_length=20)
    password: str = Field(..., max_length=200)


class LoginIn(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=200)


class OrderIn(BaseModel):
    ticker: str = Field(..., max_length=20)
    kind: Literal["call", "put"]
    side: Literal["long", "short"]
    strike: float = Field(..., gt=0)
    maturity: Literal["1M", "3M", "6M", "1A"]
    quantity: int = Field(..., ge=1, le=pf.MAX_CONTRACTS)


# ---------- dépendances ----------
def get_db(request: Request):
    return request.app.state.db


def get_provider(request: Request):
    return getattr(request.app.state, "provider", pf.default_provider)


def current_user(request: Request, db=Depends(get_db)) -> dict:
    user = auth.user_from_token(db, request.cookies.get(COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Connecte-toi pour accéder à ton portefeuille.")
    return user


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "inconnu")


def _set_session(request: Request, response: Response, token: str) -> None:
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(COOKIE, token, max_age=auth.SESSION_DAYS * 86400, httponly=True,
                        samesite="lax", secure=https, path="/")


def _guard(fn):
    try:
        return fn()
    except (auth.AuthError, pf.TradeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- comptes ----------
@router.post("/auth/register")
def register(body: RegisterIn, request: Request, response: Response, db=Depends(get_db)):
    def run():
        auth.check_rate_limit("register:" + _client_ip(request))
        user = auth.register(db, body.email, body.username, body.password)
        _set_session(request, response, auth.create_session(db, user["id"]))
        return {"user": user}
    return _guard(run)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db=Depends(get_db)):
    def run():
        auth.check_rate_limit("login:" + _client_ip(request))
        user, token = auth.login(db, body.email, body.password)
        _set_session(request, response, token)
        return {"user": user}
    return _guard(run)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    auth.logout(db, request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request, db=Depends(get_db)):
    return {"user": auth.user_from_token(db, request.cookies.get(COOKIE))}


# ---------- portefeuille ----------
@router.get("/portfolio")
def get_portfolio(user=Depends(current_user), db=Depends(get_db), provider=Depends(get_provider)):
    return _guard(lambda: pf.portfolio(db, user["id"], provider))


@router.post("/portfolio/quote")
def get_quote(body: OrderIn, user=Depends(current_user), provider=Depends(get_provider)):
    return _guard(lambda: pf.quote(provider, body.ticker, body.kind, body.strike, body.maturity,
                                   body.side, body.quantity))


@router.post("/portfolio/orders")
def place_order(body: OrderIn, user=Depends(current_user), db=Depends(get_db), provider=Depends(get_provider)):
    return _guard(lambda: pf.open_position(db, user["id"], provider, **body.model_dump()))


@router.post("/portfolio/positions/{position_id}/close")
def close(position_id: int, user=Depends(current_user), db=Depends(get_db), provider=Depends(get_provider)):
    return _guard(lambda: pf.close_position(db, user["id"], position_id, provider))


@router.get("/portfolio/history")
def get_history(user=Depends(current_user), db=Depends(get_db)):
    return pf.history(db, user["id"])


@router.get("/leaderboard")
def get_leaderboard(db=Depends(get_db), provider=Depends(get_provider)):
    return pf.leaderboard(db, provider)
