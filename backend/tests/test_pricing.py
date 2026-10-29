import math

import pytest

from optionlab import bs_price, bs_greeks, implied_vol, binomial_price, monte_carlo_price

S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2


def test_valeur_de_reference_hull():
    # Exemple classique (Hull) : S=42, K=40, T=0.5, r=10 %, sigma=20 % -> call 4.76, put 0.81
    assert bs_price(42, 40, 0.5, 0.10, 0.20, "call") == pytest.approx(4.7594, abs=1e-3)
    assert bs_price(42, 40, 0.5, 0.10, 0.20, "put") == pytest.approx(0.8086, abs=1e-3)


@pytest.mark.parametrize("q", [0.0, 0.02])
@pytest.mark.parametrize("strike", [80, 100, 120])
def test_parite_call_put(strike, q):
    c = bs_price(S, strike, T, r, sigma, "call", q)
    p = bs_price(S, strike, T, r, sigma, "put", q)
    assert c - p == pytest.approx(S * math.exp(-q * T) - strike * math.exp(-r * T), abs=1e-9)


def test_bornes_d_arbitrage():
    c = bs_price(S, K, T, r, sigma, "call")
    assert max(S - K * math.exp(-r * T), 0) <= c <= S


def test_echeance_egale_valeur_intrinseque():
    assert bs_price(110, 100, 0, r, sigma, "call") == pytest.approx(10)
    assert bs_price(110, 100, 0, r, sigma, "put") == 0


def test_greeks_par_differences_finies():
    h = 1e-3
    for opt in ("call", "put"):
        g = bs_greeks(S, K, T, r, sigma, opt)
        f = lambda s=S, t=T, rr=r, v=sigma: bs_price(s, K, t, rr, v, opt)
        assert g.delta == pytest.approx((f(s=S + h) - f(s=S - h)) / (2 * h), abs=1e-5)
        assert g.gamma == pytest.approx((f(s=S + h) - 2 * f() + f(s=S - h)) / h**2, abs=1e-3)
        assert g.vega == pytest.approx((f(v=sigma + h) - f(v=sigma - h)) / (2 * h) / 100, abs=1e-5)
        assert g.rho == pytest.approx((f(rr=r + h) - f(rr=r - h)) / (2 * h) / 100, abs=1e-5)
        assert g.theta == pytest.approx(-(f(t=T + h) - f(t=T - h)) / (2 * h) / 365, abs=1e-5)


def test_delta_call_moins_delta_put_vaut_un():
    assert bs_greeks(S, K, T, r, sigma, "call").delta - bs_greeks(S, K, T, r, sigma, "put").delta \
        == pytest.approx(1.0)


@pytest.mark.parametrize("vol", [0.05, 0.2, 0.6, 1.5])
@pytest.mark.parametrize("opt", ["call", "put"])
def test_volatilite_implicite_retrouve_sigma(vol, opt):
    price = bs_price(S, 110, 0.75, r, vol, opt)
    assert implied_vol(price, S, 110, 0.75, r, opt) == pytest.approx(vol, abs=1e-6)


def test_volatilite_implicite_prix_impossible():
    with pytest.raises(ValueError):
        implied_vol(150, S, K, T, r, "call")  # un call ne peut pas valoir plus que S


def test_binomial_converge_vers_black_scholes():
    for opt in ("call", "put"):
        assert binomial_price(S, K, T, r, sigma, opt, steps=1000) == \
            pytest.approx(bs_price(S, K, T, r, sigma, opt), abs=0.01)


def test_put_americain_vaut_plus_que_l_europeen():
    eu = binomial_price(S, K, T, r, sigma, "put", steps=500)
    us = binomial_price(S, K, T, r, sigma, "put", steps=500, american=True)
    assert us > eu
    # sans dividende, exercer un call américain avant l'échéance n'est jamais optimal
    assert binomial_price(S, K, T, r, sigma, "call", steps=500, american=True) == \
        pytest.approx(binomial_price(S, K, T, r, sigma, "call", steps=500), abs=1e-9)


def test_monte_carlo_dans_l_intervalle_de_confiance():
    mc, se = monte_carlo_price(S, K, T, r, sigma, "call", n_paths=200_000)
    assert abs(mc - bs_price(S, K, T, r, sigma, "call")) < 4 * se


def test_entrees_invalides():
    with pytest.raises(ValueError):
        bs_price(-1, K, T, r, sigma)
    with pytest.raises(ValueError):
        bs_price(S, K, T, r, sigma, "digital")
