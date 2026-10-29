import pytest

from optionlab.hedging import run_hedging, simulate_paths, hedge_pnl
from optionlab import bs_price

BASE = dict(S0=100, K=100, T=0.5, r=0.03, implied_vol=0.2)


def test_trajectoires_forme_et_depart():
    p = simulate_paths(100, 1, 0.05, 0.2, 52, 300, seed=1)
    assert p.shape == (300, 53)
    assert (p[:, 0] == 100).all() and (p > 0).all()


def test_couverture_neutre_quand_vol_realisee_egale_implicite():
    res = run_hedging(**BASE, realized_vol=0.2, rebalance=252, n_paths=4000)
    s = res["stats"]
    assert abs(s["mean"]) < 0.1                     # P&L moyen ~ 0
    assert s["std"] < 0.15 * res["premium"]         # bien plus petit que la prime


def test_ecart_type_decroit_avec_la_frequence():
    conv = run_hedging(**BASE, realized_vol=0.2, rebalance=52, n_paths=1000)["convergence"]
    stds = [c["std"] for c in conv]                 # mensuelle, hebdo, quotidienne
    assert stds[0] > stds[1] > stds[2]
    # en 1/sqrt(N) : passer de 52 à 252 pas divise l'écart-type par ~2.2
    assert stds[1] / stds[2] == pytest.approx((252 / 52) ** 0.5, rel=0.3)


def test_vendeur_perd_si_vol_realisee_superieure():
    res = run_hedging(**BASE, realized_vol=0.35, rebalance=252, n_paths=3000)
    gap = bs_price(100, 100, 0.5, 0.03, 0.35) - bs_price(100, 100, 0.5, 0.03, 0.2)
    assert res["stats"]["mean"] == pytest.approx(-gap, rel=0.15)
    long = run_hedging(**BASE, realized_vol=0.35, rebalance=252, n_paths=3000, side="long")
    assert long["stats"]["mean"] == pytest.approx(gap, rel=0.15)


def test_la_tendance_n_a_presque_pas_d_effet():
    a = run_hedging(**BASE, realized_vol=0.2, mu=-0.3, rebalance=252, n_paths=3000)["stats"]["mean"]
    b = run_hedging(**BASE, realized_vol=0.2, mu=0.4, rebalance=252, n_paths=3000)["stats"]["mean"]
    assert abs(a) < 0.15 and abs(b) < 0.15


def test_frais_de_transaction_coutent():
    sans = run_hedging(**BASE, realized_vol=0.2, rebalance=252, n_paths=2000)["stats"]
    avec = run_hedging(**BASE, realized_vol=0.2, rebalance=252, n_paths=2000, cost_rate=0.002)["stats"]
    assert avec["mean"] < sans["mean"] and avec["avg_costs"] > 0


def test_put_couvert_et_trajectoire_coherente():
    res = run_hedging(**BASE, realized_vol=0.2, option="put", rebalance=52, n_paths=500)
    path = res["path"]
    n = res["n_steps"] + 1
    assert all(len(path[k]) == n for k in ("t", "S", "delta", "option_value", "pnl"))
    assert all(-1 <= d <= 0 for d in path["delta"])
    assert path["pnl"][0] == pytest.approx(0, abs=1e-9)   # P&L nul à l'instant initial


def test_parametres_invalides():
    with pytest.raises(ValueError):
        run_hedging(**BASE, realized_vol=0.2, n_paths=50)
    with pytest.raises(ValueError):
        hedge_pnl(simulate_paths(100, 1, 0, .2, 10, 100), 100, 1, 0, .2, side="neutre")
