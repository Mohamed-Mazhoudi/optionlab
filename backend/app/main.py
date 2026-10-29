"""API FastAPI d'OptionLab. Lancer : uvicorn app.main:app --reload (depuis backend/)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from optionlab import (Leg, Market, Strategy, PRESETS, build_preset, bs_price, bs_greeks,
                       implied_vol, binomial_price, monte_carlo_price)
from optionlab.hedging import run_hedging
from optionlab.marketdata import fetch_market

app = FastAPI(title="OptionLab API", version="1.0.0",
              description="Pricing Black-Scholes, greeks et stratégies d'options (simulation éducative).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------- schémas ----------
class MarketIn(BaseModel):
    S: float = Field(100, gt=0, description="Spot")
    T: float = Field(0.5, ge=0, description="Maturité en années")
    r: float = Field(0.03, description="Taux sans risque")
    sigma: float = Field(0.2, ge=0, description="Volatilité")
    q: float = Field(0.0, description="Rendement du dividende")


class OptionIn(MarketIn):
    K: float = Field(100, gt=0)
    option: Literal["call", "put"] = "call"


class ImpliedVolIn(OptionIn):
    price: float = Field(..., gt=0)


class LegIn(BaseModel):
    kind: Literal["call", "put", "stock"]
    side: Literal["long", "short"] = "long"
    strike: float | None = Field(None, gt=0)
    quantity: float = Field(1, gt=0)
    premium: float | None = None


class StrategyIn(BaseModel):
    market: MarketIn
    legs: list[LegIn] = Field(..., min_length=1, max_length=8)
    name: str = "Stratégie personnalisée"
    points: int = Field(201, ge=21, le=1001)


class HedgingIn(BaseModel):
    S0: float = Field(100, gt=0)
    K: float = Field(100, gt=0)
    T: float = Field(0.5, gt=0, le=3)
    r: float = 0.03
    q: float = 0.0
    implied_vol: float = Field(0.2, gt=0, le=2)
    realized_vol: float = Field(0.2, gt=0, le=2)
    mu: float = Field(0.05, ge=-1, le=1)
    option: Literal["call", "put"] = "call"
    side: Literal["short", "long"] = "short"
    rebalance: int = Field(52, ge=1, le=2000)
    n_paths: int = Field(2000, ge=100, le=20000)
    cost_rate: float = Field(0.0, ge=0, le=0.05)
    seed: int | None = 7


def _bad_request(fn):
    try:
        return fn()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- endpoints ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/price")
def price(o: OptionIn):
    def run():
        bs = bs_price(o.S, o.K, o.T, o.r, o.sigma, o.option, o.q)
        out = {"black_scholes": bs,
               "greeks": bs_greeks(o.S, o.K, o.T, o.r, o.sigma, o.option, o.q).to_dict()}
        if o.T > 0 and o.sigma > 0:
            mc, se = monte_carlo_price(o.S, o.K, o.T, o.r, o.sigma, o.option, o.q, n_paths=50_000)
            out["binomial"] = binomial_price(o.S, o.K, o.T, o.r, o.sigma, o.option, o.q, steps=300)
            out["binomial_american"] = binomial_price(o.S, o.K, o.T, o.r, o.sigma, o.option, o.q,
                                                      steps=300, american=True)
            out["monte_carlo"] = {"price": mc, "std_error": se}
        return out
    return _bad_request(run)


@app.post("/api/implied-vol")
def iv(o: ImpliedVolIn):
    return _bad_request(lambda: {"implied_vol": implied_vol(o.price, o.S, o.K, o.T, o.r, o.option, o.q)})


@app.post("/api/greeks-curve")
def greeks_curve(o: OptionIn, points: int = 121):
    """Évolution du prix et des greeks quand le spot varie (± 50 %)."""
    def run():
        spots = np.linspace(0.5 * o.K, 1.5 * o.K, points)
        rows = [bs_greeks(float(s), o.K, o.T, o.r, o.sigma, o.option, o.q).to_dict() for s in spots]
        return {"spots": spots.tolist(),
                "price": [bs_price(float(s), o.K, o.T, o.r, o.sigma, o.option, o.q) for s in spots],
                **{k: [row[k] for row in rows] for k in ("delta", "gamma", "vega", "theta", "rho")}}
    return _bad_request(run)


@app.get("/api/presets")
def presets():
    return PRESETS


@app.post("/api/presets/{key}")
def preset(key: str, market: MarketIn):
    def run():
        st = build_preset(key, Market(**market.model_dump()))
        return st.to_dict()
    return _bad_request(run)


@app.post("/api/strategy")
def strategy(s: StrategyIn):
    def run():
        m = Market(**s.market.model_dump())
        st = Strategy([Leg(**l.model_dump()) for l in s.legs], m, s.name)
        spots = st.default_grid(s.points)
        return {
            **st.summary(),
            "spots": spots.tolist(),
            "pnl_expiry": st.pnl_curve(spots, 0.0).tolist(),
            "pnl_today": st.pnl_curve(spots, m.T).tolist(),
            "pnl_half": st.pnl_curve(spots, m.T / 2).tolist(),
        }
    return _bad_request(run)


@app.post("/api/hedging")
def hedging(h: HedgingIn):
    return _bad_request(lambda: run_hedging(**h.model_dump()))


@app.get("/api/market/{ticker}")
def market_data(ticker: str):
    return _bad_request(lambda: fetch_market(ticker))


# ---------- frontend statique ----------
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    def index():
        return FileResponse(FRONTEND / "index.html")
