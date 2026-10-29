"""Portefeuille virtuel d'options : cotation, ordres, marge, échéance, valorisation, classement.

Règles du jeu
- Capital de départ : 100 000 crédits virtuels (aucune conversion de devise : tout est en crédits).
- Options européennes sur de vrais sous-jacents ; 1 contrat = 100 options.
- Prix : Black-Scholes avec le cours réel, la volatilité historique 1 an et le dividende du titre, r = 3 %.
  On achète au prix « ask » (mid + 1 %) et on vend au prix « bid » (mid − 1 %), écart minimum 0,01.
- Vente d'options : marge exigée = (20 % du cours + prime) × 100 par contrat vendu.
  Un ordre est refusé si, après l'ordre, la trésorerie ne couvre pas la marge totale exigée.
- À l'échéance, les options sont réglées en cash à leur valeur intrinsèque.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable

from optionlab import bs_price, bs_greeks, intrinsic
from optionlab.marketdata import fetch_market

from .auth import STARTING_CASH
from .db import Database

MULTIPLIER = 100
RISK_FREE = 0.03
HALF_SPREAD = 0.01
MIN_HALF_SPREAD = 0.01
MARGIN_RATE = 0.20
MAX_CONTRACTS = 50
MATURITIES = {"1M": 30, "3M": 91, "6M": 182, "1A": 365}

PriceProvider = Callable[[str], dict]


class TradeError(ValueError):
    """Ordre refusé (message affichable)."""


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _money(x: float) -> float:
    return round(float(x), 2)


def _sign(side: str) -> int:
    return 1 if side == "long" else -1


def _years(expiry: str, today: date) -> float:
    return max((date.fromisoformat(expiry) - today).days, 0) / 365


def _bid_ask(mid: float) -> tuple[float, float]:
    hs = max(MIN_HALF_SPREAD, HALF_SPREAD * mid)
    return max(0.0, mid - hs), mid + hs


def describe(p: dict) -> str:
    sens = "Achat" if p["side"] == "long" else "Vente"
    return f"{sens} {p['quantity']} {p['kind']} {p['ticker']} K={p['strike']:g} éch. {p['expiry']}"


class Market:
    """Récupère les données de marché avec un cache local à la requête et un repli sur le dernier cours connu."""

    def __init__(self, provider: PriceProvider):
        self.provider = provider
        self._cache: dict[str, dict] = {}

    def get(self, ticker: str) -> dict:
        if ticker not in self._cache:
            d = self.provider(ticker)
            self._cache[ticker] = {
                "price": float(d["price"]), "vol": float(d.get("vol_1y") or 0.25),
                "q": float(d.get("dividend_yield") or 0.0), "name": d.get("name") or ticker,
            }
        return self._cache[ticker]

    def get_or_last(self, pos: dict) -> tuple[dict, bool]:
        """Données à jour si possible, sinon les dernières stockées sur la position (bool = à jour)."""
        try:
            return self.get(pos["ticker"]), True
        except Exception:
            return {"price": pos["last_spot"], "vol": pos["last_vol"], "q": pos["last_q"], "name": pos["name"]}, False


def _mark(pos: dict, m: dict, today: date) -> dict:
    """Valorise une position ouverte : prix milieu, valeur, P&L latent, greeks (× contrats × 100)."""
    T = _years(pos["expiry"], today)
    S, vol, q = m["price"], m["vol"], m["q"]
    sign, n = _sign(pos["side"]), pos["quantity"] * MULTIPLIER
    mid = bs_price(S, pos["strike"], T, RISK_FREE, vol, pos["kind"], q)
    g = bs_greeks(S, pos["strike"], T, RISK_FREE, vol, pos["kind"], q).to_dict()
    return {
        **pos, "spot": S, "vol": vol, "days_left": max((date.fromisoformat(pos["expiry"]) - today).days, 0),
        "mid": mid, "value": sign * mid * n,
        "unrealized_pnl": sign * (mid - pos["entry_price"]) * n,
        "greeks": {k: sign * v * n for k, v in g.items()},
        "margin": (MARGIN_RATE * S + mid) * n if sign < 0 else 0.0,
    }


# ---------- cotation ----------
def quote(provider: PriceProvider, ticker: str, kind: str, strike: float, maturity: str,
          side: str, quantity: int, today: date | None = None) -> dict:
    today = today or _today()
    ticker = ticker.strip().upper()
    if kind not in ("call", "put"):
        raise TradeError("Type d'option inconnu.")
    if side not in ("long", "short"):
        raise TradeError("Sens inconnu.")
    if maturity not in MATURITIES:
        raise TradeError("Échéance inconnue.")
    if not (isinstance(quantity, int) and 1 <= quantity <= MAX_CONTRACTS):
        raise TradeError(f"Quantité entre 1 et {MAX_CONTRACTS} contrats.")
    try:
        m = Market(provider).get(ticker)
    except Exception as e:
        raise TradeError(f"Cours indisponible pour {ticker} : {e}") from e
    S = m["price"]
    if not (0.5 * S <= strike <= 2 * S):
        raise TradeError(f"Strike entre {0.5 * S:.2f} et {2 * S:.2f} (50 % à 200 % du cours).")

    expiry = (today + timedelta(days=MATURITIES[maturity])).isoformat()
    T = MATURITIES[maturity] / 365
    mid = bs_price(S, strike, T, RISK_FREE, m["vol"], kind, m["q"])
    bid, ask = _bid_ask(mid)
    price = ask if side == "long" else bid
    if price <= 0:
        raise TradeError("Option sans valeur au prix acheteur : choisis un autre strike.")
    n = quantity * MULTIPLIER
    g = bs_greeks(S, strike, T, RISK_FREE, m["vol"], kind, m["q"]).to_dict()
    return {
        "ticker": ticker, "name": m["name"], "kind": kind, "side": side, "strike": float(strike),
        "maturity": maturity, "expiry": expiry, "quantity": quantity,
        "spot": S, "vol": m["vol"], "q": m["q"], "mid": mid, "bid": bid, "ask": ask, "price": price,
        "cash_flow": _money(-_sign(side) * price * n),
        "margin": _money((MARGIN_RATE * S + mid) * n) if side == "short" else 0.0,
        "greeks": {k: _sign(side) * v * n for k, v in g.items()},
    }


# ---------- ordres ----------
def _margin_used(cur, user_id: int, mkt: Market, today: date) -> float:
    rows = cur.execute("SELECT * FROM positions WHERE user_id = ? AND status = 'open' AND side = 'short'",
                       (user_id,)).all()
    return sum(_mark(p, mkt.get_or_last(p)[0], today)["margin"] for p in rows)


def open_position(db: Database, user_id: int, provider: PriceProvider, *, ticker: str, kind: str,
                  strike: float, maturity: str, side: str, quantity: int, today: date | None = None) -> dict:
    today = today or _today()
    settle_expired(db, user_id, provider, today)
    qt = quote(provider, ticker, kind, strike, maturity, side, quantity, today)
    mkt = Market(provider)
    with db.transaction() as cur:
        user = cur.lock_user(user_id)
        if user is None:
            raise TradeError("Utilisateur introuvable.")
        cash_after = user["cash"] + qt["cash_flow"]
        margin_after = _margin_used(cur, user_id, mkt, today) + qt["margin"]
        if cash_after < margin_after - 1e-6:
            raise TradeError(f"Trésorerie insuffisante : il faudrait {margin_after:,.2f} de marge "
                             f"et il resterait {cash_after:,.2f} crédits.".replace(",", " "))
        pid = cur.insert(
            "INSERT INTO positions (user_id, ticker, name, kind, side, strike, expiry, quantity, entry_price, "
            "entry_spot, last_spot, last_vol, last_q, status, opened_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)",
            (user_id, qt["ticker"], qt["name"], kind, side, qt["strike"], qt["expiry"], quantity, qt["price"],
             qt["spot"], qt["spot"], qt["vol"], qt["q"], _ts()),
        )
        cur.execute("UPDATE users SET cash = ? WHERE id = ?", (_money(cash_after), user_id))
        cur.insert(
            "INSERT INTO trades (user_id, position_id, action, description, price, quantity, cash_flow, created_at) "
            "VALUES (?, ?, 'open', ?, ?, ?, ?, ?)",
            (user_id, pid, describe(qt), qt["price"], quantity, qt["cash_flow"], _ts()),
        )
    return {**qt, "position_id": pid, "cash": _money(cash_after)}


def close_position(db: Database, user_id: int, position_id: int, provider: PriceProvider,
                   today: date | None = None) -> dict:
    today = today or _today()
    settle_expired(db, user_id, provider, today)
    mkt = Market(provider)
    with db.transaction() as cur:
        user = cur.lock_user(user_id)
        pos = cur.execute("SELECT * FROM positions WHERE id = ? AND user_id = ?", (position_id, user_id)).one()
        if pos is None:
            raise TradeError("Position introuvable.")
        if pos["status"] != "open":
            raise TradeError("Cette position est déjà fermée.")
        try:
            m = mkt.get(pos["ticker"])
        except Exception as e:
            raise TradeError(f"Cours indisponible pour {pos['ticker']}, réessaie plus tard.") from e
        mark = _mark(pos, m, today)
        bid, ask = _bid_ask(mark["mid"])
        sign, n = _sign(pos["side"]), pos["quantity"] * MULTIPLIER
        price = bid if sign > 0 else ask          # on revend un long au bid, on rachète un short à l'ask
        cash_flow = _money(sign * price * n)
        realized = _money(sign * (price - pos["entry_price"]) * n)
        cash_after = _money(user["cash"] + cash_flow)
        cur.execute("UPDATE positions SET status = 'closed', exit_price = ?, realized_pnl = ?, closed_at = ?, "
                    "last_spot = ? WHERE id = ?", (price, realized, _ts(), m["price"], position_id))
        cur.execute("UPDATE users SET cash = ? WHERE id = ?", (cash_after, user_id))
        cur.insert(
            "INSERT INTO trades (user_id, position_id, action, description, price, quantity, cash_flow, created_at) "
            "VALUES (?, ?, 'close', ?, ?, ?, ?, ?)",
            (user_id, position_id, "Clôture : " + describe(pos), price, pos["quantity"], cash_flow, _ts()),
        )
    return {"position_id": position_id, "price": price, "cash_flow": cash_flow,
            "realized_pnl": realized, "cash": cash_after}


def settle_expired(db: Database, user_id: int, provider: PriceProvider, today: date | None = None) -> int:
    """Règle en cash, à la valeur intrinsèque, les options arrivées à échéance. Renvoie le nombre réglé."""
    today = today or _today()
    mkt = Market(provider)
    with db.transaction() as cur:
        rows = cur.execute("SELECT * FROM positions WHERE user_id = ? AND status = 'open' AND expiry <= ?",
                           (user_id, today.isoformat())).all()
        if not rows:
            return 0
        user = cur.lock_user(user_id)
        cash = user["cash"]
        for pos in rows:
            S = mkt.get_or_last(pos)[0]["price"]
            payoff = intrinsic(S, pos["strike"], pos["kind"])
            sign, n = _sign(pos["side"]), pos["quantity"] * MULTIPLIER
            cash_flow = _money(sign * payoff * n)
            realized = _money(sign * (payoff - pos["entry_price"]) * n)
            cash = _money(cash + cash_flow)
            cur.execute("UPDATE positions SET status = 'expired', exit_price = ?, realized_pnl = ?, closed_at = ?, "
                        "last_spot = ? WHERE id = ?", (payoff, realized, _ts(), S, pos["id"]))
            cur.insert(
                "INSERT INTO trades (user_id, position_id, action, description, price, quantity, cash_flow, created_at) "
                "VALUES (?, ?, 'expiry', ?, ?, ?, ?, ?)",
                (user_id, pos["id"], f"Échéance (cours {S:.2f}) : " + describe(pos), payoff, pos["quantity"],
                 cash_flow, _ts()),
            )
        cur.execute("UPDATE users SET cash = ? WHERE id = ?", (cash, user_id))
    return len(rows)


# ---------- consultation ----------
def portfolio(db: Database, user_id: int, provider: PriceProvider, today: date | None = None) -> dict:
    today = today or _today()
    settled = settle_expired(db, user_id, provider, today)
    mkt = Market(provider)
    with db.transaction() as cur:
        user = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).one()
        open_rows = cur.execute("SELECT * FROM positions WHERE user_id = ? AND status = 'open' ORDER BY id",
                                (user_id,)).all()
        realized = cur.execute("SELECT COALESCE(SUM(realized_pnl), 0) AS s FROM positions "
                               "WHERE user_id = ? AND status <> 'open'", (user_id,)).one()["s"]
        positions, stale = [], []
        for pos in open_rows:
            m, fresh = mkt.get_or_last(pos)
            if fresh:
                cur.execute("UPDATE positions SET last_spot = ?, last_vol = ?, last_q = ? WHERE id = ?",
                            (m["price"], m["vol"], m["q"], pos["id"]))
            else:
                stale.append(pos["ticker"])
            positions.append(_mark(pos, m, today))

    cash = user["cash"]
    value = sum(p["value"] for p in positions)
    equity = cash + value
    greeks = {k: sum(p["greeks"][k] for p in positions) for k in ("delta", "gamma", "vega", "theta", "rho")}
    return {
        "username": user["username"], "cash": _money(cash), "positions_value": _money(value),
        "equity": _money(equity), "starting_cash": STARTING_CASH,
        "total_pnl": _money(equity - STARTING_CASH), "return_pct": (equity / STARTING_CASH - 1) * 100,
        "unrealized_pnl": _money(sum(p["unrealized_pnl"] for p in positions)),
        "realized_pnl": _money(realized), "margin_used": _money(sum(p["margin"] for p in positions)),
        "greeks": greeks, "positions": positions, "settled_now": settled, "stale_tickers": sorted(set(stale)),
    }


def history(db: Database, user_id: int, limit: int = 100) -> list[dict]:
    with db.transaction() as cur:
        return cur.execute("SELECT action, description, price, quantity, cash_flow, created_at FROM trades "
                           "WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)).all()


def leaderboard(db: Database, provider: PriceProvider, today: date | None = None, limit: int = 50) -> list[dict]:
    """Classement par valeur totale du portefeuille (positions valorisées au dernier cours connu)."""
    today = today or _today()
    mkt = Market(provider)
    with db.transaction() as cur:
        users = cur.execute("SELECT id, username, cash FROM users").all()
        pos = cur.execute("SELECT * FROM positions WHERE status = 'open'").all()
    by_user: dict[int, list] = {}
    for p in pos:
        by_user.setdefault(p["user_id"], []).append(p)
    rows = []
    for u in users:
        value = 0.0
        for p in by_user.get(u["id"], []):
            m = mkt.get_or_last(p)[0]
            if p["expiry"] <= today.isoformat():   # échue mais pas encore réglée : valeur intrinsèque
                value += _sign(p["side"]) * intrinsic(m["price"], p["strike"], p["kind"]) * p["quantity"] * MULTIPLIER
            else:
                value += _mark(p, m, today)["value"]
        equity = u["cash"] + value
        rows.append({"username": u["username"], "equity": _money(equity),
                     "return_pct": (equity / STARTING_CASH - 1) * 100, "positions": len(by_user.get(u["id"], []))})
    rows.sort(key=lambda r: r["equity"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows[:limit]


def default_provider(ticker: str) -> dict:
    return fetch_market(ticker)
