"""Construction et analyse de stratégies d'options (combinaisons de jambes)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

import numpy as np

from .pricing import bs_price, bs_greeks, intrinsic

Kind = Literal["call", "put", "stock"]
Side = Literal["long", "short"]


@dataclass
class Market:
    S: float              # spot actuel
    T: float              # maturité (années) des options
    r: float = 0.03
    sigma: float = 0.20
    q: float = 0.0


@dataclass
class Leg:
    kind: Kind
    side: Side = "long"
    strike: float | None = None   # inutile pour 'stock'
    quantity: float = 1.0
    premium: float | None = None  # prix payé/reçu ; calculé par Black-Scholes si absent

    @property
    def sign(self) -> int:
        return 1 if self.side == "long" else -1

    def entry_price(self, m: Market) -> float:
        if self.premium is not None:
            return self.premium
        if self.kind == "stock":
            return m.S
        return bs_price(m.S, self.strike, m.T, m.r, m.sigma, self.kind, m.q)

    def value(self, S: float, T: float, m: Market) -> float:
        """Valeur unitaire de la jambe pour un spot S et un temps restant T."""
        if self.kind == "stock":
            return S
        if T <= 0:
            return intrinsic(S, self.strike, self.kind)
        return bs_price(S, self.strike, T, m.r, m.sigma, self.kind, m.q)


@dataclass
class Strategy:
    legs: list[Leg]
    market: Market
    name: str = "Stratégie personnalisée"
    _premiums: list[float] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        for leg in self.legs:
            if leg.kind != "stock" and (leg.strike is None or leg.strike <= 0):
                raise ValueError("Chaque option doit avoir un strike > 0")
            if leg.quantity <= 0:
                raise ValueError("La quantité doit être > 0")
        self._premiums = [leg.entry_price(self.market) for leg in self.legs]

    # ---------- coût et P&L ----------
    def net_cost(self) -> float:
        """Coût net d'entrée : > 0 = débit (on paie), < 0 = crédit (on encaisse)."""
        return sum(l.sign * l.quantity * p for l, p in zip(self.legs, self._premiums))

    def pnl(self, S: float, T_remaining: float | None = None) -> float:
        """P&L de la position pour un spot S, à un temps restant donné (0 = échéance)."""
        T = 0.0 if T_remaining is None else T_remaining
        value = sum(l.sign * l.quantity * l.value(S, T, self.market) for l in self.legs)
        return value - self.net_cost()

    def pnl_curve(self, spots: np.ndarray, T_remaining: float = 0.0) -> np.ndarray:
        return np.array([self.pnl(float(s), T_remaining) for s in spots])

    # ---------- greeks agrégés ----------
    def greeks(self) -> dict:
        m = self.market
        total = dict(delta=0.0, gamma=0.0, vega=0.0, theta=0.0, rho=0.0)
        for leg in self.legs:
            w = leg.sign * leg.quantity
            if leg.kind == "stock":
                total["delta"] += w
                continue
            g = bs_greeks(m.S, leg.strike, m.T, m.r, m.sigma, leg.kind, m.q).to_dict()
            for k in total:
                total[k] += w * g[k]
        return total

    # ---------- analyse ----------
    def default_grid(self, n: int = 401) -> np.ndarray:
        strikes = [l.strike for l in self.legs if l.strike] or [self.market.S]
        lo = 0.5 * min(min(strikes), self.market.S)
        hi = 1.5 * max(max(strikes), self.market.S)
        return np.linspace(max(lo, 1e-6), hi, n)

    def breakevens(self, spots: np.ndarray | None = None) -> list[float]:
        """Points morts à l'échéance (interpolation linéaire entre changements de signe)."""
        spots = self.default_grid(2001) if spots is None else spots
        pnl = self.pnl_curve(spots)
        result = []
        for i in range(len(spots) - 1):
            a, b = pnl[i], pnl[i + 1]
            if a == 0:
                result.append(float(spots[i]))
            elif a * b < 0:
                result.append(float(spots[i] - a * (spots[i + 1] - spots[i]) / (b - a)))
        return [round(x, 4) for x in result]

    def max_profit_loss(self) -> dict:
        """Gain et perte max à l'échéance. None = illimité (pente non nulle à l'infini)."""
        spots = self.default_grid(2001)
        pnl = self.pnl_curve(spots)
        # pente quand S -> infini : somme des calls et actions (achetés - vendus)
        slope_up = sum(l.sign * l.quantity for l in self.legs if l.kind in ("call", "stock"))
        max_p = None if slope_up > 1e-12 else float(max(pnl.max(), self.pnl(0.0)))
        max_l = None if slope_up < -1e-12 else float(min(pnl.min(), self.pnl(0.0)))
        return {"max_profit": max_p, "max_loss": max_l}

    def summary(self) -> dict:
        return {
            "name": self.name,
            "net_cost": self.net_cost(),
            "premiums": self._premiums,
            "greeks": self.greeks(),
            "breakevens": self.breakevens(),
            **self.max_profit_loss(),
        }

    def to_dict(self) -> dict:
        return {"name": self.name, "market": asdict(self.market),
                "legs": [asdict(l) for l in self.legs]}


# ---------- stratégies toutes prêtes ----------
PRESETS: dict[str, dict] = {
    "long_call": {"label": "Achat de call", "view": "Haussier",
                  "description": "Pari sur la hausse avec une perte limitée à la prime payée."},
    "long_put": {"label": "Achat de put", "view": "Baissier",
                 "description": "Pari sur la baisse, ou assurance d'un portefeuille."},
    "covered_call": {"label": "Covered call", "view": "Neutre à légèrement haussier",
                     "description": "On détient l'action et on vend un call pour encaisser une prime ; gain plafonné."},
    "protective_put": {"label": "Put de protection", "view": "Haussier mais prudent",
                       "description": "Action + achat de put : une assurance contre une forte baisse."},
    "bull_call_spread": {"label": "Bull call spread", "view": "Modérément haussier",
                         "description": "Achat d'un call et vente d'un call plus haut : moins cher, gain plafonné."},
    "bear_put_spread": {"label": "Bear put spread", "view": "Modérément baissier",
                        "description": "Achat d'un put et vente d'un put plus bas."},
    "long_straddle": {"label": "Long straddle", "view": "Forte volatilité attendue",
                      "description": "Call + put au même strike : on gagne si le cours bouge fortement, dans un sens ou l'autre."},
    "long_strangle": {"label": "Long strangle", "view": "Forte volatilité attendue",
                      "description": "Comme le straddle avec des strikes écartés : moins cher, il faut un plus gros mouvement."},
    "short_straddle": {"label": "Short straddle", "view": "Faible volatilité attendue",
                       "description": "Vente call + put : on encaisse les primes, perte potentiellement illimitée."},
    "butterfly": {"label": "Butterfly (calls)", "view": "Cours stable autour du strike central",
                  "description": "1 call bas acheté, 2 calls centraux vendus, 1 call haut acheté. Risque limité."},
    "iron_condor": {"label": "Iron condor", "view": "Cours dans une fourchette",
                    "description": "Bull put spread + bear call spread : crédit encaissé, risque limité des deux côtés."},
}


def build_preset(key: str, market: Market, width: float | None = None) -> Strategy:
    """Construit une stratégie prédéfinie centrée sur le spot (strikes arrondis)."""
    if key not in PRESETS:
        raise ValueError(f"Stratégie inconnue : {key}")
    S = market.S
    w = width if width is not None else round(0.05 * S, 2)  # écart entre strikes : 5 % du spot
    k = round(S, 2)
    legs: dict[str, list[Leg]] = {
        "long_call": [Leg("call", "long", k)],
        "long_put": [Leg("put", "long", k)],
        "covered_call": [Leg("stock", "long"), Leg("call", "short", k + w)],
        "protective_put": [Leg("stock", "long"), Leg("put", "long", k - w)],
        "bull_call_spread": [Leg("call", "long", k), Leg("call", "short", k + w)],
        "bear_put_spread": [Leg("put", "long", k), Leg("put", "short", k - w)],
        "long_straddle": [Leg("call", "long", k), Leg("put", "long", k)],
        "long_strangle": [Leg("put", "long", k - w), Leg("call", "long", k + w)],
        "short_straddle": [Leg("call", "short", k), Leg("put", "short", k)],
        "butterfly": [Leg("call", "long", k - w), Leg("call", "short", k, 2), Leg("call", "long", k + w)],
        "iron_condor": [Leg("put", "long", k - 2 * w), Leg("put", "short", k - w),
                        Leg("call", "short", k + w), Leg("call", "long", k + 2 * w)],
    }
    return Strategy(legs[key], market, PRESETS[key]["label"])
