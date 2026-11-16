"""Çalıştır: python -m pytest  (veya: python tests/test_model.py)"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iddia import markets, model  # noqa: E402


def synthetic(n_rounds: int = 6, seed: int = 1) -> pd.DataFrame:
    """Gücü bilinen 10 takımdan sahte lig: T0 en güçlü, T9 en zayıf."""
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(10)]
    strength = np.linspace(1.6, 0.6, 10)
    rows, day = [], pd.Timestamp("2024-08-01")
    for _ in range(n_rounds):
        for i, h in enumerate(teams):
            for j, a in enumerate(teams):
                if i == j:
                    continue
                rows.append((day, h, a,
                             rng.poisson(1.2 * 1.25 * strength[i] / strength[j]),
                             rng.poisson(1.2 * strength[j] / strength[i])))
                day += pd.Timedelta(hours=8)
    return pd.DataFrame(rows, columns=["date", "home", "away", "hg", "ag"])


def test_probabilities_are_consistent():
    mdl = model.fit(synthetic())
    p = markets.probabilities(mdl.score_matrix("T0", "T9"))
    assert abs(p["1"] + p["x"] + p["2"] - 1) < 1e-9
    assert abs(p["kg_var"] + p["kg_yok"] - 1) < 1e-9
    assert abs(p["ust"] + p["alt"] - 1) < 1e-9
    assert abs(p["1x"] - (p["1"] + p["x"])) < 1e-9


def test_model_recovers_strength_order():
    mdl = model.fit(synthetic())
    assert mdl.att[mdl.teams["T0"]] > mdl.att[mdl.teams["T5"]] > mdl.att[mdl.teams["T9"]]
    assert mdl.gamma > 1  # ev sahibi avantajı
    strong = markets.probabilities(mdl.score_matrix("T0", "T9"))
    weak = markets.probabilities(mdl.score_matrix("T9", "T0"))
    assert strong["1"] > 0.7 and weak["1"] < 0.2


def test_fit_ignores_future_matches():
    df = synthetic()
    cut = df["date"].iloc[len(df) // 2]
    a = model.fit(df, as_of=cut)
    b = model.fit(df[df["date"] < cut], as_of=cut)
    assert np.allclose(a.att, b.att)


def test_value_rules():
    probs = {"1": 0.60, "x": 0.22, "2": 0.18, "ust": 0.5, "alt": 0.5}
    found = markets.value_bets(probs, {"1": 1.85, "x": 3.5, "2": 9.0, "ust": 1.9, "alt": 1.9})
    assert [v["market"] for v in found] == ["1"]          # 0.60 x 1.85 = +%11
    assert 0 < found[0]["stake"] <= 0.02
    assert markets.value_bets(probs, {"1": 1.60}) == []   # avantaj yok
    assert markets.value_bets(probs, {"1": 2.50}) == []   # şüpheli derecede büyük avantaj


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
