"""Analyse automatique du risque d'un portefeuille virtuel (règles déterministes, sans IA).

Entrée : le dictionnaire renvoyé par portfolio.portfolio(). Sortie : alertes classées par gravité,
exposition par sous-jacent et suggestions de couverture chiffrées. Sert aussi de contexte au coach IA.
"""
from __future__ import annotations

from collections import defaultdict

from .portfolio import MULTIPLIER

LEVELS = ("danger", "warning", "info", "ok")


def _fmt(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", " ")


def exposures(positions: list[dict]) -> list[dict]:
    """Greeks agrégés par sous-jacent. delta_value = delta (en actions) × cours = exposition en crédits."""
    by: dict[str, dict] = defaultdict(lambda: {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0,
                                               "value": 0.0, "positions": 0, "spot": 0.0, "name": ""})
    for p in positions:
        e = by[p["ticker"]]
        for k in ("delta", "gamma", "vega", "theta"):
            e[k] += p["greeks"][k]
        e["value"] += p["value"]
        e["positions"] += 1
        e["spot"], e["name"] = p["spot"], p.get("name") or p["ticker"]
    rows = [{"ticker": t, **e, "delta_value": e["delta"] * e["spot"]} for t, e in by.items()]
    rows.sort(key=lambda r: abs(r["delta_value"]), reverse=True)
    return rows


def _naked_short_calls(positions: list[dict]) -> list[str]:
    """Sous-jacents où l'on a vendu plus de calls qu'on n'en a achetés : perte théoriquement illimitée."""
    net: dict[str, int] = defaultdict(int)
    for p in positions:
        if p["kind"] == "call":
            net[p["ticker"]] += p["quantity"] if p["side"] == "long" else -p["quantity"]
    return sorted(t for t, n in net.items() if n < 0)


def analyze(pf: dict) -> dict:
    positions = pf["positions"]
    equity = max(pf["equity"], 1.0)
    alerts: list[dict] = []

    def add(level, title, text):
        alerts.append({"level": level, "title": title, "text": text})

    if not positions:
        add("info", "Portefeuille vide",
            "Aucune position ouverte. Commence par une stratégie simple (achat de call si tu es haussier, "
            "achat de put si tu es baissier) avec 1 ou 2 contrats pour voir comment réagissent les greeks.")
        return {"alerts": alerts, "exposures": [], "risk_level": "ok"}

    for t in _naked_short_calls(positions):
        add("danger", f"Call vendu à découvert sur {t}",
            "Tu as vendu plus de calls que tu n'en détiens : si le titre s'envole, la perte n'a pas de limite. "
            "Pour la plafonner, achète un call de strike plus élevé (tu obtiens un bear call spread).")

    margin_ratio = pf["margin_used"] / equity
    if margin_ratio > 0.8:
        add("danger", "Marge presque saturée",
            f"La marge immobilisée représente {margin_ratio:.0%} de ton portefeuille. Un mouvement défavorable "
            "pourrait t'empêcher de passer de nouveaux ordres. Réduis ou couvre les ventes d'options.")
    elif margin_ratio > 0.5:
        add("warning", "Marge élevée", f"{margin_ratio:.0%} de ton portefeuille est immobilisé en marge.")

    soon = [p for p in positions if p["days_left"] <= 7]
    if soon:
        names = ", ".join(sorted({f"{p['ticker']} {p['kind']} {p['strike']:g}" for p in soon}))
        add("warning", "Échéances proches",
            f"{len(soon)} position(s) expirent dans 7 jours ou moins ({names}). Le theta s'accélère : "
            "décide si tu clôtures maintenant ou si tu laisses aller à l'échéance.")

    theta = pf["greeks"]["theta"]
    if theta < -0.003 * equity:
        add("warning", "Érosion du temps importante",
            f"Ton portefeuille perd environ {_fmt(-theta)} crédits par jour si rien ne bouge "
            f"({-theta / equity:.2%} par jour). Les options achetées coûtent du temps : il faut que le mouvement "
            "arrive vite.")

    expo = exposures(positions)
    gross = sum(abs(e["delta_value"]) for e in expo)
    for e in expo:
        lev = e["delta_value"] / equity
        if abs(lev) > 1:
            sens = "haussière" if lev > 0 else "baissière"
            atm = "put" if lev > 0 else "call"   # delta positif : on achète des puts, négatif : des calls
            n =max(1, round(abs(e["delta"]) / (0.5 * MULTIPLIER)))
            add("warning", f"Forte exposition {sens} sur {e['ticker']}",
                f"Ton delta sur {e['ticker']} équivaut à {_fmt(e['delta'])} actions, soit {_fmt(e['delta_value'])} "
                f"crédits ({abs(lev):.1f} fois ton portefeuille). Une baisse de 5 % du titre ferait varier ton "
                f"portefeuille d'environ {_fmt(abs(e['delta_value']) * 0.05)} crédits. Pour neutraliser le delta, "
                f"il faudrait acheter environ {n} contrat(s) de {atm} à la monnaie (delta ≈ 0,5).")
    if len(expo) == 1 and len(positions) >= 2:
        add("info", "Tout sur un seul titre",
            f"Toutes tes positions portent sur {expo[0]['ticker']}. Une mauvaise nouvelle sur ce titre "
            "touche tout ton portefeuille d'un coup.")
    elif gross > 0 and len(expo) > 1 and abs(expo[0]["delta_value"]) / gross > 0.75:
        add("info", "Exposition concentrée",
            f"{abs(expo[0]['delta_value']) / gross:.0%} de ton exposition directionnelle vient de {expo[0]['ticker']}.")

    vega = pf["greeks"]["vega"]
    if abs(vega) > 0.01 * equity:
        sens = "gagne" if vega > 0 else "perd"
        add("info", "Sensibilité à la volatilité",
            f"Si la volatilité monte de 1 point, ton portefeuille {sens} environ {_fmt(abs(vega))} crédits. "
            + ("Tu es acheteur de volatilité : les annonces et les crises te profitent."
               if vega > 0 else "Tu es vendeur de volatilité : un marché calme te profite, un choc te coûte."))

    for p in positions:
        if p["side"] == "long" and p["entry_price"] > 0 and p["mid"] < 0.2 * p["entry_price"]:
            add("info", f"Option presque sans valeur : {p['ticker']} {p['kind']} {p['strike']:g}",
                f"Elle a perdu plus de 80 % ({p['mid']:.2f} contre {p['entry_price']:.2f} à l'achat). "
                "Il est rarement utile de la revendre au bid : la perte maximale est déjà presque atteinte.")

    if not alerts:
        add("ok", "Rien d'alarmant", "Aucun risque particulier détecté : marge raisonnable, pas de vente à découvert "
            "de calls, exposition mesurée.")
    alerts.sort(key=lambda a: LEVELS.index(a["level"]))
    return {"alerts": alerts, "exposures": expo, "risk_level": alerts[0]["level"]}
