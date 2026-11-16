"""Haftalık Markdown raporu: reports/YYYY-AA-GG.md"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import config, data, markets, model


def _pct(p: float) -> str:
    return f"%{round(p * 100)}"


def build(today: date | None = None) -> str:
    today = pd.Timestamp(today or date.today())
    end = today + pd.Timedelta(days=config.REPORT_DAYS)
    fx = data.load_fixtures()
    fx = fx[(fx["date"] >= today) & (fx["date"] <= end)]

    lines = [
        f"# Haftalık Futbol Analizi — {today:%d.%m.%Y}",
        "",
        f"Kapsam: {today:%d.%m} – {end:%d.%m}. Olasılıklar modelin tahminidir, garanti değildir.",
        "",
    ]
    values, safe = [], []

    for div, name in config.LEAGUES.items():
        games = fx[fx["div"] == div]
        lines += [f"## {name}", ""]
        if games.empty:
            lines += ["Bu aralıkta fikstür verisi yok.", ""]
            continue
        try:
            mdl = model.fit(data.load_results(div), as_of=today)
        except (FileNotFoundError, ValueError) as e:
            lines += [f"Model kurulamadı: {e}", ""]
            continue
        lines += [
            "| Tarih | Maç | 1 | X | 2 | KG Var | 2.5 Üst | Gol bekl. |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for g in games.itertuples():
            lh, la = mdl.rates(g.home, g.away)
            p = markets.probabilities(mdl.score_matrix(g.home, g.away))
            thin = min(mdl.matches_of(g.home), mdl.matches_of(g.away)) < config.MIN_TEAM_MATCHES
            match = f"{g.home} – {g.away}" + (" ⚠" if thin else "")
            lines.append(
                f"| {g.date:%d.%m} | {match} | {_pct(p['1'])} | {_pct(p['x'])} | {_pct(p['2'])} "
                f"| {_pct(p['kg_var'])} | {_pct(p['ust'])} | {lh:.1f} – {la:.1f} |"
            )
            if thin:
                continue
            odds = {"1": g.o_1, "x": g.o_x, "2": g.o_2, "ust": g.o_ust, "alt": g.o_alt}
            for v in markets.value_bets(p, odds):
                values.append((name, g, v))
            # oranı veride olmayan pazarlar: en olası seçim + gereken en düşük oran
            # (pazar grubu başına maçın en olası tek seçimi; oranı 1.10 altı olacaklar anlamsız)
            for group in (("1x", "x2", "12"), ("kg_var", "kg_yok")):
                key = max(group, key=lambda k: p[k])
                if p[key] >= 0.70 and markets.min_odds(p[key]) >= 1.10:
                    safe.append((p[key], name, g, key))
        lines.append("")

    lines += [
        "## Değerli oranlar",
        "",
        "Dikkat: bu kuralların geçmiş maçlardaki kâr/zarar sonucu `reports/backtest.txt` "
        "dosyasında. Getiri sütunu eksideyse bu bölümdeki seçimlere para yatırma.",
        "",
    ]
    if values:
        lines += [
            "Model olasılığı piyasa oranının ima ettiğinden yüksek olan seçimler.",
            "",
            "| Lig | Maç | Seçim | Olasılık | Oran | Avantaj | Kasa payı |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, g, v in sorted(values, key=lambda t: -t[2]["edge"]):
            lines.append(
                f"| {name} | {g.home} – {g.away} | {markets.LABELS[v['market']]} | {_pct(v['p'])} "
                f"| {v['odds']:.2f} | +%{v['edge'] * 100:.0f} | %{v['stake'] * 100:.1f} |"
            )
    else:
        lines.append("Bu hafta kuralları geçen seçim yok. Zorlamamak da bir karardır.")
    lines += ["", "## Temkinli seçimler (oranı kendin kontrol et)", ""]
    if safe:
        lines += [
            "Çifte şans ve KG oranları veri kaynağında yok. Bahis sitendeki oran "
            "\"En az oran\" sütunundan yüksekse seçim değerlidir.",
            "",
            "| Lig | Maç | Seçim | Olasılık | En az oran |",
            "|---|---|---|---|---|",
        ]
        for p, name, g, key in sorted(safe, key=lambda t: -t[0])[:15]:
            lines.append(
                f"| {name} | {g.home} – {g.away} | {markets.LABELS[key]} | {_pct(p)} "
                f"| {markets.min_odds(p):.2f} |"
            )
    else:
        lines.append("Olasılığı %70 üstü seçim yok.")
    lines += ["", "⚠ = takımlardan birinin verisi az, öneri yapılmadı.", ""]
    return "\n".join(lines)


def write(today: date | None = None):
    today = today or date.today()
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.REPORT_DIR / f"{today:%Y-%m-%d}.md"
    path.write_text(build(today), encoding="utf-8")
    return path
