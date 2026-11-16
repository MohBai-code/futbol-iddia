"""Benzer oranlı geçmiş maçlar: aynı MS 1/X/2 oranlarıyla açılmış maçlar nasıl bitti?

Not: veri kaynağındaki oranlar maçtan birkaç gün önce toplanan (kapanış olmayan)
piyasa ortalamasıdır; gerçek "ilk açılış" oranı ücretsiz veride yok. Fikstür
oranları da aynı türden olduğu için kıyas tutarlıdır.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import config, data


def load_pool() -> pd.DataFrame:
    """Tüm liglerin oranı bilinen oynanmış maçları."""
    parts = []
    for div, name in config.LEAGUES.items():
        try:
            df = data.load_results(div)
        except FileNotFoundError:
            continue
        df["lig"] = name
        parts.append(df)
    if not parts:
        raise FileNotFoundError("Veri yok. Önce: python -m iddia indir")
    pool = pd.concat(parts, ignore_index=True)
    return pool.dropna(subset=["o_1", "o_x", "o_2"])


def similar(pool: pd.DataFrame, o1: float, ox: float, o2: float, before=None) -> pd.DataFrame:
    """Üç oranı da hedefin ±SIMILAR_TOL yakınında olan maçlar, yeniden eskiye."""
    t = config.SIMILAR_TOL
    m = (
        ((pool["o_1"] / o1 - 1).abs() <= t)
        & ((pool["o_x"] / ox - 1).abs() <= t)
        & ((pool["o_2"] / o2 - 1).abs() <= t)
    )
    if before is not None:
        m &= pool["date"] < pd.Timestamp(before)
    return pool[m].sort_values("date", ascending=False)


def summarize(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {"n": 0}
    total = df["hg"] + df["ag"]
    scores = (df["hg"].astype(int).astype(str) + "-" + df["ag"].astype(int).astype(str)).value_counts()
    return {
        "n": n,
        "1": float((df["hg"] > df["ag"]).mean()),
        "x": float((df["hg"] == df["ag"]).mean()),
        "2": float((df["hg"] < df["ag"]).mean()),
        "kg": float(((df["hg"] > 0) & (df["ag"] > 0)).mean()),
        "ust": float((total >= 3).mean()),
        "gol": float(total.mean()),
        "skor": ", ".join(f"{s} (%{c / n * 100:.0f})" for s, c in scores.head(3).items()),
    }


def _pct(p: float) -> str:
    return f"%{p * 100:.0f}"


def block(pool: pd.DataFrame, o1: float, ox: float, o2: float, before=None) -> list[str]:
    """Bir oran üçlüsü için Markdown: özet tablo + en yeni benzer maçlar."""
    sim = similar(pool, o1, ox, o2, before)
    s = summarize(sim)
    if s["n"] == 0:
        return [f"Bu oranlara ±%{config.SIMILAR_TOL * 100:.0f} yakınlıkta geçmiş maç bulunamadı.", ""]
    imp = [1 / o1, 1 / ox, 1 / o2]
    imp = [v / sum(imp) for v in imp]
    lines = [
        "| | Maç sayısı | MS 1 | MS X | MS 2 | KG Var | 2.5 Üst | Ort. gol |",
        "|---|---|---|---|---|---|---|---|",
        f"| Benzer maçlar | {s['n']} | {_pct(s['1'])} | {_pct(s['x'])} | {_pct(s['2'])} "
        f"| {_pct(s['kg'])} | {_pct(s['ust'])} | {s['gol']:.2f} |",
        f"| Oranın ima ettiği | | {_pct(imp[0])} | {_pct(imp[1])} | {_pct(imp[2])} | | | |",
        "",
        f"En sık skorlar: {s['skor']}",
    ]
    if s["n"] < config.SIMILAR_MIN_N:
        lines.append(f"Örnek az ({s['n']} maç): yüzdeler şansa çok açık, tek başına güvenme.")
    lines += [
        "",
        "| Tarih | Lig | Maç | 1 | X | 2 | Skor | Sonuç |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for g in sim.head(config.SIMILAR_SHOW).itertuples():
        res = "1" if g.hg > g.ag else "X" if g.hg == g.ag else "2"
        lines.append(
            f"| {g.date:%d.%m.%Y} | {g.lig} | {g.home} – {g.away} | {g.o_1:.2f} | {g.o_x:.2f} "
            f"| {g.o_2:.2f} | {int(g.hg)}-{int(g.ag)} | {res} |"
        )
    if s["n"] > config.SIMILAR_SHOW:
        lines.append(f"\n(En yeni {config.SIMILAR_SHOW} maç gösterildi, toplam {s['n']}.)")
    lines.append("")
    return lines


def query(o1: float, ox: float, o2: float) -> str:
    head = [f"## Oranlar {o1:.2f} / {ox:.2f} / {o2:.2f} ile açılmış geçmiş maçlar", ""]
    return "\n".join(head + block(load_pool(), o1, ox, o2))


def build(today: date | None = None) -> str:
    today = pd.Timestamp(today or date.today())
    end = today + pd.Timedelta(days=config.REPORT_DAYS)
    fx = data.load_fixtures()
    fx = fx[(fx["date"] >= today) & (fx["date"] <= end)]
    pool = load_pool()
    lines = [
        f"# Benzer Oranlı Maçlar — {today:%d.%m.%Y}",
        "",
        f"Her maç için, MS 1/X/2 oranlarının üçü de ±%{config.SIMILAR_TOL * 100:.0f} yakınlıkta "
        f"olan geçmiş maçların sonuçları ({pool['date'].min():%Y}–{pool['date'].max():%Y}, "
        f"{len(pool)} maçlık havuz, tüm ligler).",
        "",
        "Geçmiş yüzdeler garanti değildir; \"Oranın ima ettiği\" satırıyla arasındaki küçük "
        "farklar çoğunlukla şanstır.",
        "",
    ]
    any_game = False
    for div, name in config.LEAGUES.items():
        games = fx[fx["div"] == div]
        if games.empty:
            continue
        any_game = True
        lines += [f"## {name}", ""]
        for g in games.itertuples():
            lines.append(f"### {g.date:%d.%m} {g.home} – {g.away}")
            if pd.isna(g.o_1) or pd.isna(g.o_x) or pd.isna(g.o_2):
                lines += ["", "Bu maçın oranı henüz veride yok.", ""]
                continue
            lines += [f"Oranlar: {g.o_1:.2f} / {g.o_x:.2f} / {g.o_2:.2f}", ""]
            lines += block(pool, g.o_1, g.o_x, g.o_2, before=today)
    if not any_game:
        lines.append("Bu aralıkta fikstür verisi yok.")
    return "\n".join(lines) + "\n"


def write(today: date | None = None):
    today = today or date.today()
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.REPORT_DIR / f"benzer-{today:%Y-%m-%d}.md"
    path.write_text(build(today), encoding="utf-8")
    return path
