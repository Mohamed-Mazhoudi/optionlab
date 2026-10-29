import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
MARKET = {"S": 100, "T": 0.5, "r": 0.03, "sigma": 0.25, "q": 0}


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_price():
    data = client.post("/api/price", json={**MARKET, "K": 100, "option": "call"}).json()
    assert data["black_scholes"] > 0
    assert abs(data["binomial"] - data["black_scholes"]) < 0.05
    assert set(data["greeks"]) == {"delta", "gamma", "vega", "theta", "rho"}


def test_implied_vol_aller_retour():
    p = client.post("/api/price", json={**MARKET, "K": 105, "option": "put"}).json()["black_scholes"]
    iv = client.post("/api/implied-vol", json={**MARKET, "K": 105, "option": "put", "price": p}).json()
    assert iv["implied_vol"] == pytest.approx(0.25, abs=1e-6)


def test_preset_puis_strategy():
    legs = client.post("/api/presets/iron_condor", json=MARKET).json()["legs"]
    data = client.post("/api/strategy", json={"market": MARKET, "legs": legs}).json()
    assert len(data["spots"]) == len(data["pnl_expiry"]) == len(data["pnl_today"])
    assert data["net_cost"] < 0


def test_erreur_400():
    r = client.post("/api/implied-vol", json={**MARKET, "K": 100, "option": "call", "price": 500})
    assert r.status_code == 400


def test_hedging():
    data = client.post("/api/hedging", json={"S0": 100, "K": 100, "T": 0.5, "implied_vol": 0.2,
                                             "realized_vol": 0.2, "rebalance": 52, "n_paths": 500}).json()
    assert len(data["histogram"]["counts"]) == 40
    assert len(data["convergence"]) == 3
    assert abs(data["stats"]["mean"]) < 0.5


def test_hedging_validation():
    r = client.post("/api/hedging", json={"realized_vol": -1})
    assert r.status_code == 422


def test_market_ticker_invalide():
    assert client.get("/api/market/AAPL;DROP").status_code == 400


def test_redirection_ancienne_adresse():
    r = client.get("/lecons?x=1", headers={"host": "optionlab-mlpk.onrender.com"}, follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "https://optionlab.fr/lecons?x=1"
    r = client.get("/", headers={"host": "www.optionlab.fr"}, follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "https://optionlab.fr/"
    # l'API n'est jamais redirigée (UptimeRobot surveille /api/health sur l'ancienne adresse)
    assert client.get("/api/health", headers={"host": "optionlab-mlpk.onrender.com"}).status_code == 200
    assert client.get("/api/health", headers={"host": "optionlab.fr"}).status_code == 200
