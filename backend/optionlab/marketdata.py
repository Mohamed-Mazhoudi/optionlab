"""Données de marché réelles via yfinance (Yahoo Finance) : spot, volatilité historique, dividende.

Exemples de tickers : AAPL, MSFT, TSLA, ^GSPC (S&P 500), TTE.PA (TotalEnergies), MC.PA (LVMH),
AIR.PA (Airbus). Les données Yahoo peuvent être retardées ou temporairement indisponibles.
"""
from __future__ import annotations

import math
import re
import time

import numpy as np

TRADING_DAYS = 252
_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 15 * 60  # secondes
_TICKER_RE = re.compile(r"^[\^A-Za-z0-9.\-=]{1,20}$")


def historical_vol(closes, window: int | None = None) -> float:
    """Volatilité historique annualisée : écart-type des rendements logarithmiques × √252."""
    prices = np.asarray(closes, dtype=float)
    prices = prices[~np.isnan(prices)]
    if window is not None:
        prices = prices[-(window + 1):]
    if len(prices) < 3 or (prices <= 0).any():
        raise ValueError("Pas assez de cours valides pour calculer une volatilité")
    log_ret = np.diff(np.log(prices))
    return float(log_ret.std(ddof=1) * math.sqrt(TRADING_DAYS))


def dividend_yield(dividends, price: float) -> float:
    """Rendement du dividende sur 12 mois (somme des dividendes / cours), en taux continu."""
    total = float(np.nansum(np.asarray(dividends, dtype=float)))
    if price <= 0 or total <= 0:
        return 0.0
    return math.log(1 + total / price)


def fetch_market(ticker: str) -> dict:
    """Récupère cours, volatilités historiques et dividende d'un titre (mis en cache 15 min)."""
    ticker = ticker.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise ValueError("Ticker invalide")
    now = time.time()
    if ticker in _CACHE and now - _CACHE[ticker][0] < CACHE_TTL:
        return _CACHE[ticker][1]

    try:
        import yfinance as yf
    except ImportError as e:  # pragma: no cover
        raise ValueError("Le module yfinance n'est pas installé (pip install yfinance)") from e

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y", auto_adjust=False, actions=True)
    except Exception as e:  # réseau, limite de requêtes Yahoo…
        raise ValueError(f"Données indisponibles pour le moment ({type(e).__name__})") from e
    if hist is None or hist.empty or "Close" not in hist:
        raise ValueError(f"Aucune donnée trouvée pour « {ticker} ». Pour Paris, ajoute .PA (ex. TTE.PA)")

    closes = hist["Close"].dropna()
    price = float(closes.iloc[-1])
    name, currency = ticker, ""
    try:
        info = tk.fast_info
        currency = info.get("currency", "") or ""
    except Exception:
        pass
    try:
        name = tk.info.get("shortName") or tk.info.get("longName") or ticker
    except Exception:
        pass

    divs = hist["Dividends"] if "Dividends" in hist else []
    data = {
        "ticker": ticker,
        "name": name,
        "currency": currency,
        "price": price,
        "date": closes.index[-1].strftime("%Y-%m-%d"),
        "vol_1y": historical_vol(closes.values),
        "vol_3m": historical_vol(closes.values, window=63),
        "dividend_yield": dividend_yield(divs, price),
        "history": {"dates": [d.strftime("%Y-%m-%d") for d in closes.index],
                    "close": [round(float(c), 4) for c in closes.values]},
    }
    _CACHE[ticker] = (now, data)
    return data
