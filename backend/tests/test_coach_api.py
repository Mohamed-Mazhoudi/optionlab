"""Routes du coach et des données pro (s'exécutent si FastAPI est installé)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app import auth  # noqa: E402


class FakeMarket:
    def __call__(self, ticker):
        return {"price": 200.0, "vol_1y": 0.25, "dividend_yield": 0.0, "name": "Apple"}


def fake_claude(payload):
    return {"content": [{"type": "text", "text": "Analyse."},
                        {"type": "tool_use", "id": "t", "name": "proposer_strategie",
                         "input": {"preset": "long_put", "ticker": "AAPL", "raison": "Protection"}}]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    app.state.provider = FakeMarket()
    app.state.coach_caller = fake_claude
    app.state.news_fetch = lambda t: {"ticker": t, "available": False, "reason": "test"}
    auth._ATTEMPTS.clear()
    with TestClient(app) as c:
        yield c
    for k in ("provider", "coach_caller", "news_fetch"):
        delattr(app.state, k)


def test_coach_de_bout_en_bout(client):
    assert client.post("/api/coach", json={"question": "Salut"}).status_code == 401
    client.post("/api/auth/register", json={"email": "cam@example.com", "username": "cam",
                                            "password": "motdepasse"})
    a = client.get("/api/coach/analysis").json()
    assert a["coach_enabled"] and a["alerts"][0]["title"] == "Portefeuille vide"
    r = client.post("/api/coach", json={"question": "Que faire ?", "view": "prudent",
                                        "history": [{"role": "user", "content": "Bonjour"},
                                                    {"role": "assistant", "content": "Salut !"}]})
    assert r.status_code == 200 and r.json()["suggestions"][0]["preset"] == "long_put"
    assert client.post("/api/coach", json={"question": "x", "view": "fou"}).status_code == 422


def test_insights_route(client):
    assert client.get("/api/insights/AAPL").json()["available"] is False
    assert client.get("/api/insights/AA%3BPL").status_code == 400
