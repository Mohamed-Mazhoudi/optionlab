"""Données de marché « pro » via l'API Finnhub : actualités, consensus des analystes, profil, résultats.

Variable d'environnement : FINNHUB_API_KEY (clé gratuite sur finnhub.io). Sans clé, tout renvoie
available = False et le site fonctionne normalement. L'offre gratuite couvre surtout les actions
américaines : pour les titres européens, indices et cryptos on l'indique simplement.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Callable

BASE = "https://finnhub.io/api/v1"
CACHE_TTL = 30 * 60          # secondes
MAX_CALLS_PER_MIN = 50       # l'offre gratuite autorise 60 appels/minute
_US_RE = re.compile(r"^[A-Z]{1,5}(-[A-Z])?$")

Fetcher = Callable[[str, dict], object]

_cache: dict[str, tuple[float, dict]] = {}
_calls: list[float] = []
_lock = threading.Lock()


def api_key() -> str:
    return os.environ.get("FINNHUB_API_KEY", "").strip()


def enabled() -> bool:
    return bool(api_key())


def _http_get(path: str, params: dict) -> object:
    """Appel HTTP réel (bibliothèque standard, clé dans l'en-tête pour ne pas l'exposer dans les logs d'URL)."""
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-Finnhub-Token": api_key(), "User-Agent": "OptionLab"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())


def _budget() -> bool:
    """Limiteur global : protège le quota gratuit si quelqu'un tape des dizaines de tickers."""
    now = time.time()
    with _lock:
        while _calls and now - _calls[0] > 60:
            _calls.pop(0)
        if len(_calls) >= MAX_CALLS_PER_MIN:
            return False
        _calls.append(now)
        return True


def finnhub_symbol(ticker: str) -> str | None:
    """Symbole Finnhub pour les actions américaines (BRK-B -> BRK.B) ; None si non couvert gratuitement."""
    t = ticker.strip().upper()
    if not _US_RE.match(t):
        return None
    return t.replace("-", ".")


def _safe_url(u: str) -> str:
    return u if isinstance(u, str) and u.startswith(("https://", "http://")) else ""


def _news(items, limit: int) -> list[dict]:
    out = []
    for n in items if isinstance(items, list) else []:
        if not n.get("headline"):
            continue
        out.append({
            "headline": str(n["headline"])[:300],
            "summary": str(n.get("summary") or "")[:500],
            "source": str(n.get("source") or "")[:60],
            "url": _safe_url(n.get("url")),
            "date": datetime.fromtimestamp(int(n.get("datetime") or 0), timezone.utc).date().isoformat(),
        })
        if len(out) >= limit:
            break
    return out


def fetch_insights(ticker: str, fetch: Fetcher | None = None, today: date | None = None) -> dict:
    """Actualités (7 derniers jours), consensus analystes, profil et prochaine publication de résultats."""
    sym = finnhub_symbol(ticker)
    base = {"ticker": ticker.strip().upper(), "available": False}
    if fetch is None:
        if not enabled():
            return {**base, "reason": "Données pro non configurées sur ce serveur."}
        fetch = _http_get
    if sym is None:
        return {**base, "reason": "Actualités disponibles pour les actions américaines (ex. AAPL, NVDA, TSLA)."}

    hit = _cache.get(sym)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    if not _budget():
        return {**base, "reason": "Trop de demandes en ce moment, réessaie dans une minute."}

    today = today or datetime.now(timezone.utc).date()
    out = {**base, "available": True, "symbol": sym, "news": [], "recommendation": None,
           "profile": None, "earnings": None}

    def safe(path, params):
        try:
            return fetch(path, params)
        except Exception:
            return None

    news = safe("/company-news", {"symbol": sym, "from": (today - timedelta(days=7)).isoformat(),
                                  "to": today.isoformat()})
    out["news"] = _news(news, 6)

    rec = safe("/stock/recommendation", {"symbol": sym})
    if isinstance(rec, list) and rec:
        r = rec[0]
        keys = ("strongBuy", "buy", "hold", "sell", "strongSell")
        out["recommendation"] = {k: int(r.get(k) or 0) for k in keys} | {"period": r.get("period")}

    prof = safe("/stock/profile2", {"symbol": sym})
    if isinstance(prof, dict) and prof.get("name"):
        out["profile"] = {"name": prof.get("name"), "industry": prof.get("finnhubIndustry"),
                          "country": prof.get("country"), "market_cap_musd": prof.get("marketCapitalization"),
                          "currency": prof.get("currency")}

    cal = safe("/calendar/earnings", {"symbol": sym, "from": today.isoformat(),
                                      "to": (today + timedelta(days=120)).isoformat()})
    events = (cal or {}).get("earningsCalendar") if isinstance(cal, dict) else None
    if events:
        nxt = min(events, key=lambda e: e.get("date") or "9999")
        out["earnings"] = {"date": nxt.get("date"), "eps_estimate": nxt.get("epsEstimate")}

    if not (out["news"] or out["recommendation"] or out["profile"]):
        return {**base, "reason": f"Aucune donnée Finnhub pour {sym}."}
    _cache[sym] = (time.time(), out)
    return out


def consensus_label(rec: dict | None) -> str | None:
    """Résumé lisible du consensus (part d'analystes à l'achat / neutres / à la vente)."""
    if not rec:
        return None
    buy = rec["strongBuy"] + rec["buy"]
    sell = rec["sell"] + rec["strongSell"]
    total = buy + rec["hold"] + sell
    if total == 0:
        return None
    return f"{total} analystes : {buy / total:.0%} achat, {rec['hold'] / total:.0%} neutre, {sell / total:.0%} vente"
