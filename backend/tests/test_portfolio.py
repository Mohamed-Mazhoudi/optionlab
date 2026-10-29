"""Tests du portefeuille virtuel : base SQLite en mémoire et faux fournisseur de cours."""
from datetime import date, timedelta

import pytest

from app import auth
from app.db import Database
from app.portfolio import (TradeError, MULTIPLIER, quote, open_position, close_position, settle_expired,
                           portfolio, history, leaderboard)
from optionlab import bs_price

TODAY = date(2026, 11, 2)


class FakeMarket:
    """Cours modifiables à la main ; lève une erreur pour les tickers inconnus ou « en panne »."""

    def __init__(self):
        self.prices = {"AAPL": 200.0, "TTE.PA": 60.0}
        self.down = set()

    def __call__(self, ticker):
        if ticker in self.down or ticker not in self.prices:
            raise ValueError("indisponible")
        return {"price": self.prices[ticker], "vol_1y": 0.25, "dividend_yield": 0.0, "name": ticker}


@pytest.fixture
def env():
    db = Database("sqlite:///:memory:")
    db.init_schema()
    auth._ATTEMPTS.clear()
    user = auth.register(db, "alice@example.com", "alice", "motdepasse1")
    return db, user["id"], FakeMarket()


def buy_call(db, uid, mkt, **kw):
    args = dict(ticker="AAPL", kind="call", strike=200, maturity="3M", side="long", quantity=2, today=TODAY)
    args.update(kw)
    return open_position(db, uid, mkt, **args)


# ---------- comptes ----------
def test_inscription_connexion_session(env):
    db, uid, _ = env
    user, token = auth.login(db, "Alice@Example.com ", "motdepasse1")
    assert user["username"] == "alice"
    assert auth.user_from_token(db, token)["id"] == uid
    auth.logout(db, token)
    assert auth.user_from_token(db, token) is None


def test_mot_de_passe_jamais_en_clair(env):
    db, uid, _ = env
    with db.transaction() as cur:
        row = cur.execute("SELECT pw_hash FROM users WHERE id = ?", (uid,)).one()
    assert "motdepasse1" not in row["pw_hash"] and len(row["pw_hash"]) == 64


@pytest.mark.parametrize("email,username,pwd,msg", [
    ("alice@example.com", "bob", "motdepasse1", "existe déjà"),
    ("bob@example.com", "ALICE", "motdepasse1", "déjà pris"),
    ("pas-un-email", "bob", "motdepasse1", "email invalide"),
    ("bob@example.com", "b", "motdepasse1", "Pseudo invalide"),
    ("bob@example.com", "bob", "court", "8 caractères"),
])
def test_inscription_refusee(env, email, username, pwd, msg):
    db, _, _ = env
    with pytest.raises(auth.AuthError, match=msg):
        auth.register(db, email, username, pwd)


def test_mauvais_mot_de_passe_et_limitation(env):
    db, _, _ = env
    with pytest.raises(auth.AuthError, match="incorrect"):
        auth.login(db, "alice@example.com", "mauvais")
    with pytest.raises(auth.AuthError):
        for _ in range(20):
            auth.check_rate_limit("1.2.3.4")


def test_jeton_invalide(env):
    db, _, _ = env
    assert auth.user_from_token(db, "nimportequoi") is None
    assert auth.user_from_token(db, None) is None


# ---------- cotation ----------
def test_cotation_bid_ask_et_flux():
    q = quote(FakeMarket(), "aapl", "call", 200, "3M", "long", 2, TODAY)
    mid = bs_price(200, 200, 91 / 365, 0.03, 0.25, "call")
    assert q["ticker"] == "AAPL" and q["mid"] == pytest.approx(mid)
    assert q["ask"] == pytest.approx(mid * 1.01) and q["bid"] == pytest.approx(mid * 0.99)
    assert q["cash_flow"] == pytest.approx(-q["ask"] * 2 * MULTIPLIER, abs=0.01)
    assert q["expiry"] == (TODAY + timedelta(days=91)).isoformat()
    assert q["margin"] == 0
    short = quote(FakeMarket(), "AAPL", "put", 180, "1M", "short", 1, TODAY)
    # put vendu : delta positif (on gagne si le cours monte)
    assert short["cash_flow"] > 0 and short["margin"] > 0 and short["greeks"]["delta"] > 0


@pytest.mark.parametrize("kw,msg", [
    (dict(quantity=0), "Quantité"), (dict(quantity=51), "Quantité"), (dict(strike=50), "Strike entre"),
    (dict(maturity="2A"), "Échéance"), (dict(kind="digital"), "Type"), (dict(ticker="ZZZ"), "indisponible"),
])
def test_cotation_refusee(kw, msg):
    args = dict(ticker="AAPL", kind="call", strike=200, maturity="3M", side="long", quantity=1)
    args.update(kw)
    with pytest.raises(TradeError, match=msg):
        quote(FakeMarket(), args.pop("ticker"), today=TODAY, **args)


# ---------- ordres ----------
def test_achat_debite_la_tresorerie(env):
    db, uid, mkt = env
    res = buy_call(db, uid, mkt)
    assert res["cash"] == pytest.approx(100_000 + res["cash_flow"])
    pf = portfolio(db, uid, mkt, TODAY)
    assert len(pf["positions"]) == 1
    # valorisé au mid : la seule perte immédiate est la demi-fourchette
    assert pf["equity"] == pytest.approx(100_000 - 0.01 * pf["positions"][0]["mid"] * 2 * MULTIPLIER, abs=0.02)
    assert pf["greeks"]["delta"] == pytest.approx(pf["positions"][0]["greeks"]["delta"])
    assert 0 < pf["greeks"]["delta"] < 200


def test_hausse_du_cours_et_cloture_avec_gain(env):
    db, uid, mkt = env
    buy_call(db, uid, mkt)
    mkt.prices["AAPL"] = 230.0
    pf = portfolio(db, uid, mkt, TODAY + timedelta(days=10))
    pos = pf["positions"][0]
    assert pos["unrealized_pnl"] > 0
    res = close_position(db, uid, pos["id"], mkt, TODAY + timedelta(days=10))
    assert res["realized_pnl"] > 0
    pf2 = portfolio(db, uid, mkt, TODAY + timedelta(days=10))
    assert pf2["positions"] == [] and pf2["realized_pnl"] == pytest.approx(res["realized_pnl"])
    assert pf2["equity"] == pytest.approx(pf2["cash"])
    with pytest.raises(TradeError, match="déjà fermée"):
        close_position(db, uid, pos["id"], mkt, TODAY)


def test_aller_retour_immediat_coute_la_fourchette(env):
    db, uid, mkt = env
    res = buy_call(db, uid, mkt, quantity=1)
    out = close_position(db, uid, res["position_id"], mkt, TODAY)
    mid = res["mid"]
    assert out["realized_pnl"] == pytest.approx(-2 * 0.01 * mid * MULTIPLIER, abs=0.02)


def test_vente_avec_marge(env):
    db, uid, mkt = env
    res = open_position(db, uid, mkt, ticker="AAPL", kind="put", strike=180, maturity="1M", side="short",
                        quantity=5, today=TODAY)
    assert res["cash"] > 100_000                       # la prime est encaissée
    pf = portfolio(db, uid, mkt, TODAY)
    assert pf["margin_used"] == pytest.approx(res["margin"], rel=1e-3)
    assert pf["positions"][0]["value"] < 0             # une option vendue est une dette


def test_marge_insuffisante_refusee(env):
    db, uid, mkt = env
    mkt.prices["AAPL"] = 2000.0                        # marge par contrat ≈ 0,2 × 2000 × 100 = 40 000
    open_position(db, uid, mkt, ticker="AAPL", kind="call", strike=2400, maturity="1M", side="short",
                  quantity=2, today=TODAY)
    with pytest.raises(TradeError, match="insuffisante"):
        open_position(db, uid, mkt, ticker="AAPL", kind="call", strike=2400, maturity="1M", side="short",
                      quantity=2, today=TODAY)


def test_achat_trop_cher_refuse(env):
    db, uid, mkt = env
    mkt.prices["AAPL"] = 5000.0
    with pytest.raises(TradeError, match="insuffisante"):
        buy_call(db, uid, mkt, strike=5000, maturity="1A", quantity=50)
    assert portfolio(db, uid, mkt, TODAY)["cash"] == 100_000   # rien n'a été débité


def test_reglement_a_l_echeance(env):
    db, uid, mkt = env
    res = buy_call(db, uid, mkt, strike=200, maturity="1M", quantity=1)
    mkt.prices["AAPL"] = 215.0
    later = TODAY + timedelta(days=31)
    assert settle_expired(db, uid, mkt, later) == 1
    pf = portfolio(db, uid, mkt, later)
    assert pf["positions"] == []
    assert pf["cash"] == pytest.approx(res["cash"] + 15 * MULTIPLIER)
    assert pf["realized_pnl"] == pytest.approx((15 - res["price"]) * MULTIPLIER, abs=0.01)
    actions = [h["action"] for h in history(db, uid)]
    assert actions == ["expiry", "open"]


def test_put_vendu_expire_sans_valeur(env):
    db, uid, mkt = env
    res = open_position(db, uid, mkt, ticker="AAPL", kind="put", strike=180, maturity="1M", side="short",
                        quantity=1, today=TODAY)
    pf = portfolio(db, uid, mkt, TODAY + timedelta(days=40))
    assert pf["positions"] == [] and pf["cash"] == pytest.approx(res["cash"])
    assert pf["realized_pnl"] == pytest.approx(res["cash_flow"])


def test_cours_indisponible_utilise_le_dernier_connu(env):
    db, uid, mkt = env
    buy_call(db, uid, mkt)
    mkt.down.add("AAPL")
    pf = portfolio(db, uid, mkt, TODAY)
    assert pf["stale_tickers"] == ["AAPL"] and pf["positions"][0]["spot"] == 200.0
    with pytest.raises(TradeError, match="indisponible"):
        close_position(db, uid, pf["positions"][0]["id"], mkt, TODAY)


def test_on_ne_ferme_pas_la_position_d_un_autre(env):
    db, uid, mkt = env
    res = buy_call(db, uid, mkt)
    bob = auth.register(db, "bob@example.com", "bob", "motdepasse2")
    with pytest.raises(TradeError, match="introuvable"):
        close_position(db, bob["id"], res["position_id"], mkt, TODAY)


def test_classement(env):
    db, uid, mkt = env
    bob = auth.register(db, "bob@example.com", "bob", "motdepasse2")
    buy_call(db, uid, mkt, quantity=5)
    mkt.prices["AAPL"] = 260.0                          # le call d'Alice s'envole
    board = leaderboard(db, mkt, TODAY)
    assert [r["username"] for r in board] == ["alice", "bob"]
    assert board[0]["rank"] == 1 and board[0]["return_pct"] > 0 and board[1]["equity"] == 100_000
    assert "email" not in board[0]
