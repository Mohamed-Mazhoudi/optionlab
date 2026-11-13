import math

import pytest

from optionlab import intraday
from optionlab.intraday import clean_bars, fetch_candles, TRADING_TICKERS
from optionlab.marketdata import _TICKER_RE


@pytest.fixture(autouse=True)
def vider_le_cache():
    intraday._CACHE.clear()
    yield
    intraday._CACHE.clear()


def faux_cours(n=5, start=1_700_000_000):
    return lambda ticker, period, interval: [(start + 60 * i, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(n)]


def test_nettoyage_des_bougies():
    rows = [(120, 10, 11, 9, 10.5), (60, 10, float("nan"), 9, 10), (60, 10, 10.2, 9.9, 10.1),
            (180, 10, 9, 11, 12), (240, -1, 2, 1, 1)]
    bars = clean_bars(rows)
    assert [b[0] for b in bars] == [60, 120, 180]          # triées, valeurs invalides retirées
    assert bars[0] == (60, 10, 10.2, 9.9, 10.1)            # la dernière version d'une minute gagne
    assert bars[2][2] == 12 and bars[2][3] == 10           # haut/bas encadrent ouverture et clôture


def test_bougies_et_filtre_since():
    data = fetch_candles("aapl", fetch=faux_cours())
    assert data["ticker"] == "AAPL" and data["name"] == "Apple" and len(data["t"]) == 5
    assert all(l <= min(o, c) and h >= max(o, c) for o, h, l, c in zip(data["o"], data["h"], data["l"], data["c"]))
    suite = fetch_candles("AAPL", since=data["t"][3], fetch=faux_cours())
    assert suite["t"] == data["t"][3:]                     # borne incluse


def test_cache_evite_un_second_appel():
    appels = []

    def fetch(ticker, period, interval):
        appels.append((ticker, period, interval))
        return faux_cours()(ticker, period, interval)

    fetch_candles("BTC-USD", fetch=fetch, now=1000)
    fetch_candles("BTC-USD", fetch=fetch, now=1030)
    assert appels == [("BTC-USD", "5d", "1m")]
    fetch_candles("BTC-USD", fetch=fetch, now=1061)        # cache d'une minute expiré
    assert len(appels) == 2


def test_refus_sans_appel_reseau():
    def interdit(*a):
        raise AssertionError("aucun appel réseau attendu")

    with pytest.raises(ValueError):
        fetch_candles("TSLA", fetch=interdit)              # hors de la liste du simulateur
    with pytest.raises(ValueError):
        fetch_candles("AAPL", interval="2m", fetch=interdit)


def test_aucune_donnee():
    with pytest.raises(ValueError):
        fetch_candles("AAPL", fetch=lambda *a: [])
    with pytest.raises(ValueError):
        fetch_candles("AAPL", fetch=lambda *a: [(60, math.nan, 1, 1, 1)])


def test_tickers_du_simulateur_valides():
    assert all(_TICKER_RE.match(k) and k == k.upper() for k in TRADING_TICKERS)
