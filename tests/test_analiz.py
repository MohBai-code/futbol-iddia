"""Maç analizi testleri (sahte veriyle, internetsiz)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iddia import analiz, data  # noqa: E402
from test_model import synthetic  # noqa: E402

NAMES = {"T0": "Galatasaray", "T1": "Fenerbahce", "T2": "Besiktas", "T3": "Trabzonspor"}


@pytest.fixture
def fake_data(monkeypatch):
    df = synthetic()
    df["home"] = df["home"].replace(NAMES)
    df["away"] = df["away"].replace(NAMES)
    df["div"] = "T1"

    def load_results(div):
        if div != "T1":
            raise FileNotFoundError(div)
        return df.copy()

    monkeypatch.setattr(data, "load_results", load_results)
    monkeypatch.setattr(data, "load_fixtures", lambda: pd.DataFrame(columns=["div", "date", "home", "away"]))
    return df


def test_turkce_ad_eslesir(fake_data):
    assert analiz.find_team("Fenerbahçe") == ("T1", "Fenerbahce")
    assert analiz.find_team("beşiktaş") == ("T1", "Besiktas")
    assert analiz.find_team("Trabzon") == ("T1", "Trabzonspor")


def test_bilinmeyen_takim_durur(fake_data):
    with pytest.raises(SystemExit):
        analiz.find_team("Real Madrid")


def test_analiz_metni(fake_data):
    text = analiz.analyze("Galatasaray", "Fenerbahçe")
    assert "# Maç Analizi: Galatasaray – Fenerbahce" in text
    for bolum in ("## Kısa yorum", "## Model tahmini", "## Son form", "## Aralarındaki son maçlar"):
        assert bolum in text
    assert "Galatasaray" in text.split("## Kısa yorum")[1].split("##")[0]  # en güçlü takım favori
