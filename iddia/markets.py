"""Skor matrisinden bahis pazarı olasılıkları ve değerli oran taraması."""
from __future__ import annotations

import numpy as np

from . import config

# pazar anahtarı -> raporda görünen ad
LABELS = {
    "1": "MS 1", "x": "MS X", "2": "MS 2",
    "1x": "ÇŞ 1-X", "12": "ÇŞ 1-2", "x2": "ÇŞ X-2",
    "kg_var": "KG Var", "kg_yok": "KG Yok",
    "ust": "2.5 Üst", "alt": "2.5 Alt",
}
# Veri kaynağında oranı bulunan pazarlar (diğerleri için "en az oran" gösterilir)
PRICED = ["1", "x", "2", "ust", "alt"]


def probabilities(m: np.ndarray) -> dict:
    p1 = float(np.tril(m, -1).sum())
    px = float(np.trace(m))
    p2 = float(np.triu(m, 1).sum())
    kg = float(m[1:, 1:].sum())
    i, j = np.indices(m.shape)
    ust = float(m[i + j >= 3].sum())
    return {
        "1": p1, "x": px, "2": p2,
        "1x": p1 + px, "12": p1 + p2, "x2": px + p2,
        "kg_var": kg, "kg_yok": 1 - kg,
        "ust": ust, "alt": 1 - ust,
    }


def min_odds(p: float) -> float:
    """Bu olasılıkta bahsin değerli sayılması için gereken en düşük oran."""
    return (1 + config.MIN_EDGE) / p


def stake(p: float, odds: float) -> float:
    """Kasanın yüzde kaçı: çeyrek Kelly, üst sınırlı."""
    kelly = (p * odds - 1) / (odds - 1)
    return max(0.0, min(kelly * config.KELLY_FRACTION, config.MAX_STAKE))


def value_bets(probs: dict, odds: dict) -> list[dict]:
    """Oranı bilinen pazarlarda kuralları geçen seçimler."""
    out = []
    for key in PRICED:
        o = odds.get(key)
        if o is None or not np.isfinite(o) or o < config.MIN_ODDS:
            continue
        p = probs[key]
        edge = p * o - 1
        if p >= config.MIN_PROB and config.MIN_EDGE <= edge <= config.MAX_EDGE:
            out.append({"market": key, "p": p, "odds": float(o), "edge": edge, "stake": stake(p, o)})
    return out


def implied(o1: float, ox: float, o2: float) -> tuple[float, float, float]:
    """Bahis sitesinin payı çıkarılmış 1/X/2 olasılıkları."""
    inv = np.array([1 / o1, 1 / ox, 1 / o2])
    return tuple(inv / inv.sum())
