import math

import numpy as np
import pytest

from optionlab.marketdata import historical_vol, dividend_yield, fetch_market, KNOWN_NAMES, _TICKER_RE
from optionlab.hedging import simulate_paths


def test_vol_historique_retrouve_la_vol_simulee():
    # 20 ans de cours quotidiens simulés avec sigma = 30 %
    closes = simulate_paths(100, 20, 0.05, 0.30, 20 * 252, 1, seed=3)[0]
    assert historical_vol(closes) == pytest.approx(0.30, rel=0.03)


def test_vol_nulle_pour_un_cours_constant_ou_exponentiel():
    assert historical_vol([100] * 50) == 0
    assert historical_vol(100 * np.exp(0.001 * np.arange(50))) == pytest.approx(0, abs=1e-12)


def test_fenetre():
    closes = np.concatenate([np.full(200, 100.0), 100 * np.exp(np.cumsum(np.tile([0.02, -0.02], 31)))])
    assert historical_vol(closes, window=62) > historical_vol(closes)


def test_entrees_invalides():
    with pytest.raises(ValueError):
        historical_vol([100, 101])
    with pytest.raises(ValueError):
        historical_vol([100, -5, 101, 102])


def test_rendement_dividende():
    assert dividend_yield([0.5, 0.5, 0.5, 0.5], 100) == pytest.approx(math.log(1.02))
    assert dividend_yield([], 100) == 0


def test_ticker_invalide_rejete_sans_appel_reseau():
    with pytest.raises(ValueError):
        fetch_market("AAPL; rm -rf /")


def test_noms_connus_valides():
    assert KNOWN_NAMES["TTE.PA"] == "TotalEnergies" and KNOWN_NAMES["^FCHI"] == "CAC 40"
    # chaque clé est un ticker accepté et déjà en majuscules (la saisie est mise en majuscules)
    assert all(_TICKER_RE.match(k) and k == k.upper() for k in KNOWN_NAMES)
