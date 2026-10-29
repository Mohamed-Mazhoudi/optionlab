import pytest

from optionlab import Leg, Market, Strategy, PRESETS, build_preset, bs_price

M = Market(S=100, T=0.5, r=0.03, sigma=0.25)


def test_long_call_perte_max_egale_prime():
    st = Strategy([Leg("call", "long", 100)], M)
    prime = bs_price(100, 100, 0.5, 0.03, 0.25, "call")
    assert st.net_cost() == pytest.approx(prime)
    res = st.max_profit_loss()
    assert res["max_profit"] is None            # gain illimité
    assert res["max_loss"] == pytest.approx(-prime)
    assert st.breakevens() == [pytest.approx(100 + prime, abs=0.05)]


def test_short_call_perte_illimitee():
    res = Strategy([Leg("call", "short", 100)], M).max_profit_loss()
    assert res["max_loss"] is None and res["max_profit"] > 0


def test_straddle_deux_points_morts_symetriques():
    st = build_preset("long_straddle", M)
    be = st.breakevens()
    assert len(be) == 2
    assert be[0] == pytest.approx(100 - st.net_cost(), abs=0.05)
    assert be[1] == pytest.approx(100 + st.net_cost(), abs=0.05)


def test_bull_spread_gain_et_perte_bornes():
    st = build_preset("bull_call_spread", M)  # strikes 100 / 105
    res = st.max_profit_loss()
    assert res["max_loss"] == pytest.approx(-st.net_cost(), abs=1e-6)
    assert res["max_profit"] == pytest.approx(5 - st.net_cost(), abs=1e-6)


def test_iron_condor_est_un_credit():
    st = build_preset("iron_condor", M)
    assert st.net_cost() < 0
    res = st.max_profit_loss()
    assert res["max_profit"] == pytest.approx(-st.net_cost(), abs=1e-6)
    assert res["max_loss"] is not None


def test_covered_call_delta_entre_0_et_1():
    d = build_preset("covered_call", M).greeks()["delta"]
    assert 0 < d < 1


def test_butterfly_greeks_proches_de_zero_et_gain_au_centre():
    st = build_preset("butterfly", M)
    assert st.pnl(100) == pytest.approx(st.max_profit_loss()["max_profit"], abs=0.05)


def test_pnl_aujourd_hui_egal_zero_au_spot():
    # Sans mouvement de marché, la valeur d'aujourd'hui = coût d'entrée -> P&L nul
    for key in PRESETS:
        st = build_preset(key, M)
        assert st.pnl(M.S, M.T) == pytest.approx(0, abs=1e-9), key


def test_prime_imposee():
    st = Strategy([Leg("put", "long", 95, premium=2.0)], M)
    assert st.net_cost() == 2.0
    assert st.pnl(90) == pytest.approx(3.0)


def test_validation():
    with pytest.raises(ValueError):
        Strategy([Leg("call", "long", None)], M)
    with pytest.raises(ValueError):
        build_preset("inconnue", M)


def test_strikes_des_presets_arrondis():
    st = build_preset("iron_condor", Market(S=349.67, T=0.5))
    assert all(l.strike == round(l.strike, 2) and len(repr(l.strike)) < 10 for l in st.legs)
