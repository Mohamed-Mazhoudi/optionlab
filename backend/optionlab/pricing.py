"""Moteur de pricing d'options européennes.

Conventions :
- S : prix du sous-jacent, K : strike, T : maturité en années
- r : taux sans risque (continu, ex. 0.03), q : rendement du dividende (continu)
- sigma : volatilité annuelle (ex. 0.20)
- vega et rho sont donnés pour +1 point de % (0.01), theta par jour calendaire (/365).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np
from scipy.stats import norm

CALL = "call"
PUT = "put"


def _check(option: str) -> None:
    if option not in (CALL, PUT):
        raise ValueError("option doit valoir 'call' ou 'put'")


def _validate(S: float, K: float, T: float, sigma: float) -> None:
    if S <= 0 or K <= 0:
        raise ValueError("S et K doivent être strictement positifs")
    if T < 0:
        raise ValueError("T ne peut pas être négatif")
    if sigma < 0:
        raise ValueError("sigma ne peut pas être négatif")


def intrinsic(S: float, K: float, option: str = CALL) -> float:
    """Valeur intrinsèque (= payoff à l'échéance)."""
    _check(option)
    return max(S - K, 0.0) if option == CALL else max(K - S, 0.0)


def d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> tuple[float, float]:
    vol_sqrt_t = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def bs_price(S: float, K: float, T: float, r: float, sigma: float,
             option: str = CALL, q: float = 0.0) -> float:
    """Prix Black-Scholes-Merton d'un call ou d'un put européen."""
    _check(option)
    _validate(S, K, T, sigma)
    # Cas limites : à l'échéance ou volatilité nulle -> valeur actualisée du forward
    if T == 0 or sigma == 0:
        fwd = S * math.exp(-q * T) - K * math.exp(-r * T)
        return max(fwd, 0.0) if option == CALL else max(-fwd, 0.0)

    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    df_r, df_q = math.exp(-r * T), math.exp(-q * T)
    if option == CALL:
        return S * df_q * norm.cdf(d1) - K * df_r * norm.cdf(d2)
    return K * df_r * norm.cdf(-d2) - S * df_q * norm.cdf(-d1)


@dataclass
class Greeks:
    delta: float
    gamma: float
    vega: float   # pour +1 % de vol
    theta: float  # par jour
    rho: float    # pour +1 % de taux

    def to_dict(self) -> dict:
        return asdict(self)


def bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
              option: str = CALL, q: float = 0.0) -> Greeks:
    """Greeks analytiques de Black-Scholes-Merton."""
    _check(option)
    _validate(S, K, T, sigma)
    if T == 0 or sigma == 0:
        # À l'échéance : delta = 0 ou 1 (ou -1), le reste est nul
        itm = (S > K) if option == CALL else (S < K)
        delta = (1.0 if option == CALL else -1.0) if itm else 0.0
        return Greeks(delta, 0.0, 0.0, 0.0, 0.0)

    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    df_r, df_q = math.exp(-r * T), math.exp(-q * T)
    pdf_d1 = norm.pdf(d1)
    sqrt_t = math.sqrt(T)

    gamma = df_q * pdf_d1 / (S * sigma * sqrt_t)
    vega = S * df_q * pdf_d1 * sqrt_t
    common_theta = -S * df_q * pdf_d1 * sigma / (2 * sqrt_t)

    if option == CALL:
        delta = df_q * norm.cdf(d1)
        theta = common_theta - r * K * df_r * norm.cdf(d2) + q * S * df_q * norm.cdf(d1)
        rho = K * T * df_r * norm.cdf(d2)
    else:
        delta = -df_q * norm.cdf(-d1)
        theta = common_theta + r * K * df_r * norm.cdf(-d2) - q * S * df_q * norm.cdf(-d1)
        rho = -K * T * df_r * norm.cdf(-d2)

    return Greeks(delta=delta, gamma=gamma, vega=vega / 100, theta=theta / 365, rho=rho / 100)


def implied_vol(price: float, S: float, K: float, T: float, r: float,
                option: str = CALL, q: float = 0.0,
                tol: float = 1e-8, max_iter: int = 100) -> float:
    """Volatilité implicite : Newton-Raphson, avec repli sur la dichotomie."""
    _check(option)
    _validate(S, K, T, 0.0)
    if T == 0:
        raise ValueError("Volatilité implicite non définie à l'échéance")

    lower = bs_price(S, K, T, r, 0.0, option, q)          # prix minimal (vol nulle)
    upper = S * math.exp(-q * T) if option == CALL else K * math.exp(-r * T)
    if not (lower - 1e-12 <= price < upper):
        raise ValueError(f"Prix hors des bornes d'arbitrage ]{lower:.4f} ; {upper:.4f}[")

    # 1) Newton-Raphson
    sigma = 0.2
    for _ in range(max_iter):
        diff = bs_price(S, K, T, r, sigma, option, q) - price
        if abs(diff) < tol:
            return sigma
        vega = bs_greeks(S, K, T, r, sigma, option, q).vega * 100
        if vega < 1e-10:
            break
        sigma -= diff / vega
        if not (1e-6 < sigma < 10):
            break

    # 2) Dichotomie (toujours convergente car le prix croît avec sigma)
    lo, hi = 1e-6, 10.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, T, r, mid, option, q) > price:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def binomial_price(S: float, K: float, T: float, r: float, sigma: float,
                   option: str = CALL, q: float = 0.0, steps: int = 500,
                   american: bool = False) -> float:
    """Arbre binomial de Cox-Ross-Rubinstein (européen ou américain)."""
    _check(option)
    _validate(S, K, T, sigma)
    if T == 0 or sigma == 0:
        return bs_price(S, K, T, r, sigma, option, q)

    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    j = np.arange(steps + 1)
    prices = S * u ** (steps - j) * d ** j
    values = np.maximum(prices - K, 0) if option == CALL else np.maximum(K - prices, 0)

    for i in range(steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        if american:
            prices = prices[:-1] / u
            exercise = np.maximum(prices - K, 0) if option == CALL else np.maximum(K - prices, 0)
            values = np.maximum(values, exercise)
    return float(values[0])


def monte_carlo_price(S: float, K: float, T: float, r: float, sigma: float,
                      option: str = CALL, q: float = 0.0, n_paths: int = 100_000,
                      seed: int | None = 42) -> tuple[float, float]:
    """Monte-Carlo (variables antithétiques). Renvoie (prix, erreur standard)."""
    _check(option)
    _validate(S, K, T, sigma)
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths // 2)
    z = np.concatenate([z, -z])
    ST = S * np.exp((r - q - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
    payoff = np.maximum(ST - K, 0) if option == CALL else np.maximum(K - ST, 0)
    disc_payoff = math.exp(-r * T) * payoff
    return float(disc_payoff.mean()), float(disc_payoff.std(ddof=1) / math.sqrt(len(z)))
