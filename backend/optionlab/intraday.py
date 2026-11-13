"""Bougies intrajournalières réelles (yfinance) pour le simulateur de trading débutant.

Les cours viennent de Yahoo Finance : ils peuvent être retardés (jusqu'à 15 min selon la place)
et Yahoo ne fournit pas de carnet d'ordres. Le spread affiché par le simulateur est donc modélisé
côté navigateur autour du dernier cours réel.
"""
from __future__ import annotations

import math
import time

from .marketdata import KNOWN_NAMES

# Marchés proposés dans le simulateur (liste fermée : l'API ne sert pas de relais Yahoo général)
TRADING_TICKERS = {
    "AAPL": "Apple", "NVDA": "NVIDIA", "^GSPC": "S&P 500",
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
}
# intervalle -> (période demandée à Yahoo, durée du cache en secondes)
INTERVALS = {"1m": ("5d", 60), "5m": ("1mo", 300), "1h": ("3mo", 900), "1d": ("1y", 900)}
_CACHE: dict[tuple[str, str], tuple[float, list]] = {}


def clean_bars(rows) -> list[tuple[int, float, float, float, float]]:
    """Nettoie des bougies (t, ouverture, haut, bas, clôture) : retire les valeurs manquantes ou
    négatives, trie par date, garde la dernière version d'une même minute et force haut/bas à
    encadrer l'ouverture et la clôture."""
    by_time: dict[int, tuple[int, float, float, float, float]] = {}
    for row in rows:
        t, o, h, l, c = int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4])
        if any(math.isnan(x) or x <= 0 for x in (o, h, l, c)):
            continue
        by_time[t] = (t, o, max(h, o, c), min(l, o, c), c)
    return [by_time[t] for t in sorted(by_time)]


def _yahoo_fetch(ticker: str, period: str, interval: str) -> list:
    try:
        import yfinance as yf
    except ImportError as e:  # pragma: no cover
        raise ValueError("Le module yfinance n'est pas installé (pip install yfinance)") from e
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False, actions=False)
    except Exception as e:  # réseau, limite de requêtes Yahoo…
        raise ValueError(f"Cours indisponibles pour le moment ({type(e).__name__})") from e
    if hist is None or hist.empty:
        return []
    return [(int(ts.timestamp()), o, h, l, c)
            for ts, o, h, l, c in zip(hist.index, hist["Open"], hist["High"], hist["Low"], hist["Close"])]


def fetch_candles(ticker: str, interval: str = "1m", since: int | None = None, fetch=None, now=None) -> dict:
    """Bougies réelles d'un marché du simulateur. `since` (secondes Unix) ne renvoie que les bougies
    à partir de cette date, incluse : la dernière bougie est souvent encore en cours de formation.
    `fetch` et `now` servent aux tests (aucun appel réseau)."""
    ticker = ticker.strip().upper()
    if ticker not in TRADING_TICKERS:
        raise ValueError("Ce marché n'est pas disponible dans le simulateur")
    if interval not in INTERVALS:
        raise ValueError("Intervalle invalide (1m, 5m, 1h ou 1d)")
    period, ttl = INTERVALS[interval]
    now = time.time() if now is None else now
    key = (ticker, interval)
    if key in _CACHE and now - _CACHE[key][0] < ttl:
        bars = _CACHE[key][1]
    else:
        bars = clean_bars((fetch or _yahoo_fetch)(ticker, period, interval))
        if not bars:
            raise ValueError(f"Aucun cours disponible pour {TRADING_TICKERS[ticker]} pour le moment")
        _CACHE[key] = (now, bars)
    if since is not None:
        bars = [b for b in bars if b[0] >= since]
    return {
        "ticker": ticker,
        "name": KNOWN_NAMES.get(ticker, TRADING_TICKERS[ticker]),
        "interval": interval,
        "t": [b[0] for b in bars],
        "o": [round(b[1], 6) for b in bars],
        "h": [round(b[2], 6) for b in bars],
        "l": [round(b[3], 6) for b in bars],
        "c": [round(b[4], 6) for b in bars],
    }
