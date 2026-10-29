"""Simulation de couverture en delta (delta hedging) d'une option européenne.

Le teneur de marché vend (ou achète) une option au prix Black-Scholes calculé avec la
volatilité implicite, puis se couvre en détenant delta actions, réajusté à intervalles
réguliers. Le sous-jacent suit un mouvement brownien géométrique avec la volatilité
RÉALISÉE (qui peut différer de l'implicite) et une tendance mu.

Idées illustrées :
- si vol réalisée = vol implicite, le P&L moyen est ~0 et son écart-type décroît en 1/sqrt(N) ;
- si vol réalisée > vol implicite, le vendeur d'option couvert perd (il est short gamma) ;
- la tendance mu n'a (presque) aucun effet : c'est tout l'intérêt de la couverture ;
- les frais de transaction rendent la couverture très fréquente coûteuse.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from .pricing import bs_price, CALL, PUT, _check, _validate

FREQUENCIES = {"mensuelle": 12, "hebdomadaire": 52, "quotidienne": 252}


def _delta_vec(S: np.ndarray, K: float, tau: float, r: float, sigma: float,
               option: str, q: float) -> np.ndarray:
    """Delta Black-Scholes vectorisé (tau > 0)."""
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * tau) / (sigma * math.sqrt(tau))
    df_q = math.exp(-q * tau)
    return df_q * norm.cdf(d1) if option == CALL else -df_q * norm.cdf(-d1)


def simulate_paths(S0: float, T: float, mu: float, sigma: float, n_steps: int,
                   n_paths: int, q: float = 0.0, seed: int | None = 0) -> np.ndarray:
    """Trajectoires de mouvement brownien géométrique, forme (n_paths, n_steps + 1)."""
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    z = rng.standard_normal((n_paths, n_steps))
    increments = (mu - q - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z
    log_paths = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(increments, axis=1)], axis=1)
    return S0 * np.exp(log_paths)


def hedge_pnl(paths: np.ndarray, K: float, T: float, r: float, implied_vol: float,
              option: str = CALL, q: float = 0.0, side: str = "short",
              cost_rate: float = 0.0, keep_path: bool = False) -> dict:
    """P&L actualisé (valeur en 0) de la position couverte pour chaque trajectoire."""
    _check(option)
    if side not in ("short", "long"):
        raise ValueError("side doit valoir 'short' ou 'long'")
    n_paths, n_cols = paths.shape
    n_steps = n_cols - 1
    dt = T / n_steps
    S0 = float(paths[0, 0])
    premium = bs_price(S0, K, T, r, implied_vol, option, q)
    sgn = 1.0 if side == "short" else -1.0  # short option -> on achète delta actions

    growth, div = math.exp(r * dt), math.expm1(q * dt)
    shares = sgn * _delta_vec(paths[:, 0], K, T, r, implied_vol, option, q)
    cash = sgn * premium - shares * paths[:, 0] - cost_rate * np.abs(shares) * paths[:, 0]
    total_costs = cost_rate * np.abs(shares) * paths[:, 0]

    track = None
    if keep_path:
        track = {"delta": [float(shares[0] * sgn)], "cash": [float(cash[0])]}

    for i in range(1, n_steps):
        S = paths[:, i]
        cash = cash * growth + shares * paths[:, i - 1] * div * growth  # intérêts + dividendes
        tau = T - i * dt
        new_shares = sgn * _delta_vec(S, K, tau, r, implied_vol, option, q)
        trade = new_shares - shares
        fees = cost_rate * np.abs(trade) * S
        cash -= trade * S + fees
        total_costs += fees
        shares = new_shares
        if keep_path:
            track["delta"].append(float(shares[0] * sgn))
            track["cash"].append(float(cash[0]))

    ST = paths[:, -1]
    cash = cash * growth + shares * paths[:, -2] * div * growth
    payoff = np.maximum(ST - K, 0) if option == CALL else np.maximum(K - ST, 0)
    pnl_T = cash + shares * ST - sgn * payoff
    out = {"premium": premium, "pnl": pnl_T * math.exp(-r * T), "costs": total_costs}

    if keep_path:
        # détail de la 1re trajectoire : valeur de l'option et P&L cumulé au fil du temps
        times = np.linspace(0, T, n_cols)
        S_path = paths[0]
        opt_val = [bs_price(float(S_path[i]), K, T - times[i], r, implied_vol, option, q)
                   if i < n_steps else float(payoff[0]) for i in range(n_cols)]
        deltas = track["delta"] + [track["delta"][-1]]
        cashes = track["cash"] + [float(cash[0])]
        hedge_val = [cashes[i] + sgn * deltas[i] * float(S_path[i]) for i in range(n_cols)]
        cum_pnl = [(hedge_val[i] - sgn * opt_val[i]) * math.exp(-r * times[i]) for i in range(n_cols)]
        out["path"] = {"t": times.tolist(), "S": S_path.tolist(), "delta": deltas,
                       "option_value": opt_val, "pnl": cum_pnl}
    return out


def run_hedging(S0: float, K: float, T: float, r: float, implied_vol: float,
                realized_vol: float, mu: float = 0.05, option: str = CALL, q: float = 0.0,
                side: str = "short", rebalance: int = 52, n_paths: int = 2000,
                cost_rate: float = 0.0, seed: int | None = 7, bins: int = 40) -> dict:
    """Simulation complète : trajectoire exemple, distribution du P&L, convergence."""
    _validate(S0, K, T, implied_vol)
    if T <= 0 or implied_vol <= 0 or realized_vol <= 0:
        raise ValueError("T et les volatilités doivent être strictement positifs")
    if not (1 <= rebalance <= 2000):
        raise ValueError("Fréquence de rebalancement hors limites (1 à 2000 par an)")
    if not (100 <= n_paths <= 20000):
        raise ValueError("Nombre de trajectoires entre 100 et 20 000")

    n_steps = max(1, round(rebalance * T))
    if n_steps * n_paths > 3_000_000:
        raise ValueError("Simulation trop lourde : réduis la fréquence ou le nombre de trajectoires")

    paths = simulate_paths(S0, T, mu, realized_vol, n_steps, n_paths, q, seed)
    res = hedge_pnl(paths, K, T, r, implied_vol, option, q, side, cost_rate, keep_path=True)
    pnl = res["pnl"]

    counts, edges = np.histogram(pnl, bins=bins)
    # écart-type du P&L selon la fréquence (même graine, moins de trajectoires)
    convergence = []
    for label, freq in FREQUENCIES.items():
        steps = max(1, round(freq * T))
        p = simulate_paths(S0, T, mu, realized_vol, steps, 1000, q, seed)
        r_ = hedge_pnl(p, K, T, r, implied_vol, option, q, side, cost_rate)["pnl"]
        convergence.append({"label": label, "per_year": freq, "steps": steps,
                            "mean": float(r_.mean()), "std": float(r_.std(ddof=1))})

    # P&L théorique moyen quand vol réalisée ≠ implicite (approximation : vega × écart de vol)
    vega = (bs_price(S0, K, T, r, implied_vol + 1e-4, option, q)
            - bs_price(S0, K, T, r, implied_vol - 1e-4, option, q)) / 2e-4
    sgn = 1.0 if side == "short" else -1.0
    return {
        "premium": res["premium"],
        "n_steps": n_steps,
        "stats": {
            "mean": float(pnl.mean()), "std": float(pnl.std(ddof=1)),
            "p5": float(np.percentile(pnl, 5)), "p95": float(np.percentile(pnl, 95)),
            "prob_loss": float((pnl < 0).mean()), "avg_costs": float(res["costs"].mean()),
            "expected_vol_pnl": float(-sgn * vega * (realized_vol - implied_vol)),
        },
        "histogram": {"counts": counts.tolist(), "edges": edges.tolist()},
        "path": res["path"],
        "convergence": convergence,
    }
