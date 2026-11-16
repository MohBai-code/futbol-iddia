"""Geçmişe dönük test: model her hafta yalnızca o güne kadarki maçları görür."""
from __future__ import annotations

from math import log

import numpy as np
import pandas as pd

from . import config, data, markets, model


def run(div: str, last_n: int = 380) -> dict:
    df = data.load_results(div)
    test = df.tail(last_n)
    week = test["date"].dt.to_period("W").dt.start_time
    bets, ll_model, ll_market = [], [], []

    for start, games in test.groupby(week):
        try:
            mdl = model.fit(df, as_of=start)
        except ValueError:
            continue
        for g in games.itertuples():
            if min(mdl.matches_of(g.home), mdl.matches_of(g.away)) < config.MIN_TEAM_MATCHES:
                continue
            p = markets.probabilities(mdl.score_matrix(g.home, g.away))
            result = "1" if g.hg > g.ag else "x" if g.hg == g.ag else "2"
            won = {"1": result == "1", "x": result == "x", "2": result == "2",
                   "ust": g.hg + g.ag >= 3, "alt": g.hg + g.ag < 3}
            if np.isfinite([g.o_1, g.o_x, g.o_2]).all():
                imp = dict(zip(("1", "x", "2"), markets.implied(g.o_1, g.o_x, g.o_2)))
                ll_model.append(-log(max(p[result], 1e-9)))
                ll_market.append(-log(imp[result]))
            odds = {"1": g.o_1, "x": g.o_x, "2": g.o_2, "ust": g.o_ust, "alt": g.o_alt}
            for v in markets.value_bets(p, odds):
                bets.append(v["odds"] - 1 if won[v["market"]] else -1.0)

    n = len(bets)
    return {
        "lig": config.LEAGUES[div],
        "maç": len(ll_model),
        "bahis": n,
        "isabet": float(np.mean([b > 0 for b in bets])) if n else float("nan"),
        "getiri": float(np.mean(bets)) if n else float("nan"),
        "model_ll": float(np.mean(ll_model)) if ll_model else float("nan"),
        "piyasa_ll": float(np.mean(ll_market)) if ll_market else float("nan"),
    }


def run_all() -> str:
    rows = []
    for div in config.LEAGUES:
        try:
            rows.append(run(div))
        except (FileNotFoundError, ValueError) as e:
            print(f"{config.LEAGUES[div]}: {e}")
    if not rows:
        return "Veri yok."
    t = pd.DataFrame(rows)
    out = ["Lig              Maç  Bahis  İsabet  Getiri   Model LL  Piyasa LL"]
    for r in t.itertuples():
        out.append(
            f"{r.lig[:15]:<15} {r.maç:>4}  {r.bahis:>5}  {r.isabet:>6.0%}  {r.getiri:>+6.1%}"
            f"   {r.model_ll:>7.3f}   {r.piyasa_ll:>7.3f}"
        )
    out += [
        "",
        "Getiri: bahis başına sabit 1 birimle ortalama kâr/zarar.",
        "LL (log kayıp): düşük olan daha isabetli. Model LL > Piyasa LL ise",
        "bahis sitesi modelden iyi tahmin ediyor demektir; bu olağan durumdur.",
        "100'den az bahisle çıkan getiri rakamı şans olabilir.",
    ]
    return "\n".join(out)
