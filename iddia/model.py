"""Zaman ağırlıklı Poisson takım gücü modeli + Dixon-Coles düşük skor düzeltmesi.

Ev sahibi gol beklentisi = mu * gamma * hücum[ev] * savunma[dep]
Deplasman gol beklentisi = mu * hücum[dep] * savunma[ev]
(savunma değeri yüksek = çok gol yiyen takım)
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, factorial

import numpy as np
import pandas as pd

from . import config


@dataclass
class Model:
    teams: dict
    att: np.ndarray
    dfn: np.ndarray
    mu: float
    gamma: float
    n_matches: np.ndarray
    rho: float = config.RHO

    def matches_of(self, team: str) -> int:
        i = self.teams.get(team)
        return 0 if i is None else int(self.n_matches[i])

    def rates(self, home: str, away: str) -> tuple[float, float]:
        hi, ai = self.teams.get(home), self.teams.get(away)
        ah, dh = (self.att[hi], self.dfn[hi]) if hi is not None else (1.0, 1.0)
        aa, da = (self.att[ai], self.dfn[ai]) if ai is not None else (1.0, 1.0)
        return self.mu * self.gamma * ah * da, self.mu * aa * dh

    def score_matrix(self, home: str, away: str) -> np.ndarray:
        """m[i, j] = ev sahibi i, deplasman j gol atma olasılığı."""
        lh, la = self.rates(home, away)
        n = config.MAX_GOALS + 1
        ph = np.array([exp(-lh) * lh**k / factorial(k) for k in range(n)])
        pa = np.array([exp(-la) * la**k / factorial(k) for k in range(n)])
        m = np.outer(ph, pa)
        r = self.rho
        m[0, 0] *= max(1 - lh * la * r, 0)
        m[0, 1] *= max(1 + lh * r, 0)
        m[1, 0] *= max(1 + la * r, 0)
        m[1, 1] *= max(1 - r, 0)
        return m / m.sum()


def fit(df: pd.DataFrame, as_of=None) -> Model:
    """`as_of` tarihinden ÖNCEKİ maçlarla modeli kurar (geleceğe bakmaz)."""
    as_of = pd.Timestamp(as_of) if as_of is not None else df["date"].max() + pd.Timedelta(days=1)
    df = df[df["date"] < as_of]
    if len(df) < 50:
        raise ValueError("Model için yeterli maç yok (en az 50).")
    names = sorted(set(df["home"]) | set(df["away"]))
    idx = {t: i for i, t in enumerate(names)}
    n = len(names)
    h = df["home"].map(idx).to_numpy()
    a = df["away"].map(idx).to_numpy()
    hg = df["hg"].to_numpy(float)
    ag = df["ag"].to_numpy(float)
    days = (as_of - df["date"]).dt.days.to_numpy(float)
    w = 0.5 ** (days / config.HALF_LIFE_DAYS)

    mu = (w * ag).sum() / w.sum()
    gamma = (w * hg).sum() / (w * ag).sum()
    att, dfn = np.ones(n), np.ones(n)
    k = config.PRIOR_GOALS
    for _ in range(200):
        num = np.bincount(h, w * hg, n) + np.bincount(a, w * ag, n)
        den = np.bincount(h, w * mu * gamma * dfn[a], n) + np.bincount(a, w * mu * dfn[h], n)
        new_att = (num + k) / (den + k)
        new_att /= new_att.mean()
        num = np.bincount(h, w * ag, n) + np.bincount(a, w * hg, n)
        den = np.bincount(h, w * mu * new_att[a], n) + np.bincount(a, w * mu * gamma * new_att[h], n)
        new_dfn = (num + k) / (den + k)
        delta = max(abs(new_att - att).max(), abs(new_dfn - dfn).max())
        att, dfn = new_att, new_dfn
        if delta < 1e-7:
            break
    counts = np.bincount(h, minlength=n) + np.bincount(a, minlength=n)
    return Model(idx, att, dfn, float(mu), float(gamma), counts)
