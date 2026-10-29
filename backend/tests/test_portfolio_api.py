"""Tests de bout en bout des routes du portefeuille (s'exécutent si FastAPI est installé)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app import auth  # noqa: E402


class FakeMarket:
    def __call__(self, ticker):
        if ticker != "AAPL":
            raise ValueError("indisponible")
        return {"price": 200.0, "vol_1y": 0.25, "dividend_yield": 0.0, "name": "Apple"}


@pytest.fixture
def client():
    app.state.provider = FakeMarket()
    auth._ATTEMPTS.clear()
    with TestClient(app) as c:
        yield c
    del app.state.provider


ORDER = {"ticker": "AAPL", "kind": "call", "side": "long", "strike": 200, "maturity": "3M", "quantity": 1}


def test_parcours_complet(client):
    assert client.get("/api/portfolio").status_code == 401
    r = client.post("/api/auth/register", json={"email": "zoe@example.com", "username": "zoe",
                                                "password": "motdepasse"})
    assert r.status_code == 200 and "ol_session" in r.cookies
    assert client.get("/api/auth/me").json()["user"]["username"] == "zoe"

    q = client.post("/api/portfolio/quote", json=ORDER).json()
    assert q["ask"] > q["bid"]
    order = client.post("/api/portfolio/orders", json=ORDER).json()
    pf = client.get("/api/portfolio").json()
    assert len(pf["positions"]) == 1 and pf["cash"] == pytest.approx(order["cash"])

    closed = client.post(f"/api/portfolio/positions/{order['position_id']}/close").json()
    assert closed["realized_pnl"] < 0                       # aller-retour immédiat : on paie la fourchette
    assert [h["action"] for h in client.get("/api/portfolio/history").json()] == ["close", "open"]
    assert any(r["username"] == "zoe" for r in client.get("/api/leaderboard").json())

    client.post("/api/auth/logout")
    assert client.get("/api/portfolio").status_code == 401


def test_erreurs_lisibles(client):
    client.post("/api/auth/register", json={"email": "leo@example.com", "username": "leo", "password": "motdepasse"})
    r = client.post("/api/portfolio/orders", json={**ORDER, "ticker": "ZZZ"})
    assert r.status_code == 400 and "indisponible" in r.json()["detail"]
    assert client.post("/api/portfolio/orders", json={**ORDER, "quantity": 0}).status_code == 422
    r = client.post("/api/auth/login", json={"email": "leo@example.com", "password": "faux"})
    assert r.status_code == 400 and "incorrect" in r.json()["detail"]
