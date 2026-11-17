"""Tek maç analizi: geçmiş maçlara bakıp gelecekteki maç için tahmin ve açıklamalı yorum.

Kullanım: python -m iddia analiz Galatasaray Fenerbahçe   (lig kodu isteğe bağlı: --lig T1)
"""
from __future__ import annotations

import difflib
import re
from datetime import date

import numpy as np
import pandas as pd

from . import benzer, config, data, markets, model

_TR = str.maketrans("çğıöşüâîûÇĞİÖŞÜÂÎÛ", "cgiosuaiuCGIOSUAIU")
FORM_N = 6       # form için son kaç maç
H2H_N = 8        # aralarındaki son kaç maç
RECENT_DAYS = 400  # takım adı ararken sadece bu kadar gün içinde oynamış takımlar


def norm(s: str) -> str:
    """'Fenerbahçe SK' -> 'fenerbahcesk' (Türkçe harf, boşluk, nokta fark etmez)."""
    return re.sub(r"[^a-z0-9]", "", s.translate(_TR).lower())


def _candidates(divs) -> list[tuple[str, str]]:
    """(lig, takım) listesi: yakın zamanda oynamış takımlar."""
    out = []
    for div in divs:
        try:
            df = data.load_results(div)
        except FileNotFoundError:
            continue
        recent = df[df["date"] >= df["date"].max() - pd.Timedelta(days=RECENT_DAYS)]
        for t in sorted(set(recent["home"]) | set(recent["away"])):
            out.append((div, t))
    return out


def find_team(query: str, div: str | None = None) -> tuple[str, str]:
    """Yazılan adı veri kaynağındaki takım adına eşler. Bulamazsa öneri listesiyle durur."""
    cands = _candidates([div] if div else list(config.LEAGUES))
    if not cands:
        raise SystemExit("Veri yok. Önce: python -m iddia indir")
    q = norm(query)
    exact = [c for c in cands if norm(c[1]) == q]
    if exact:
        return exact[0]
    part = [c for c in cands if q and (q in norm(c[1]) or norm(c[1]) in q)]
    if len(part) == 1:
        return part[0]
    keys = {norm(t): (d, t) for d, t in cands}
    close = difflib.get_close_matches(q, list(keys), n=5, cutoff=0.6)
    if len(part) == 0 and len(close) >= 1 and (
        len(close) == 1 or difflib.SequenceMatcher(None, q, close[0]).ratio() >= 0.85
    ):
        return keys[close[0]]
    options = part or [keys[k] for k in close]
    if options:
        names = ", ".join(f"{t} ({config.LEAGUES[d]})" for d, t in options[:8])
        raise SystemExit(f"'{query}' birden fazla takıma uyuyor ya da tam bulunamadı: {names}")
    raise SystemExit(f"'{query}' adında takım bulunamadı. Lig kodu verip tekrar dene (örnek: --lig T1).")


def _result(hg, ag) -> str:
    return "1" if hg > ag else ("X" if hg == ag else "2")


def _form(df: pd.DataFrame, team: str, venue: str | None = None, n: int = FORM_N) -> dict:
    """Takımın son n maçı (venue: 'ev', 'dep' ya da hepsi)."""
    if venue == "ev":
        g = df[df["home"] == team]
    elif venue == "dep":
        g = df[df["away"] == team]
    else:
        g = df[(df["home"] == team) | (df["away"] == team)]
    g = g.tail(n)
    letters, gf, ga, pts = [], 0, 0, 0
    for r in g.itertuples():
        f, a = (r.hg, r.ag) if r.home == team else (r.ag, r.hg)
        gf += f
        ga += a
        if f > a:
            letters.append("G")
            pts += 3
        elif f == a:
            letters.append("B")
            pts += 1
        else:
            letters.append("M")
    k = max(len(g), 1)
    return {
        "n": len(g), "seri": " ".join(letters) or "-",
        "atilan": gf / k, "yenilen": ga / k, "puan": pts / k,
        "kg": float(((g["hg"] > 0) & (g["ag"] > 0)).mean()) if len(g) else float("nan"),
        "ust": float(((g["hg"] + g["ag"]) >= 3).mean()) if len(g) else float("nan"),
    }


def _h2h(df: pd.DataFrame, home: str, away: str, n: int = H2H_N) -> pd.DataFrame:
    g = df[((df["home"] == home) & (df["away"] == away)) | ((df["home"] == away) & (df["away"] == home))]
    return g.tail(n)


def _fixture_odds(div: str, home: str, away: str):
    """Fikstürde bu maç varsa (tarih, 1, X, 2 oranları)."""
    fx = data.load_fixtures()
    if fx.empty:
        return None
    m = fx[(fx["div"] == div) & (fx["home"] == home) & (fx["away"] == away)]
    if m.empty:
        return None
    r = m.iloc[0]
    o = tuple(float(r.get(k, np.nan)) for k in ("o_1", "o_x", "o_2"))
    return r["date"], o


def _pct(p: float) -> str:
    return "-" if p != p else f"%{p * 100:.0f}"


def _top_scores(m: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
    flat = [(f"{i}-{j}", float(m[i, j])) for i in range(m.shape[0]) for j in range(m.shape[1])]
    return sorted(flat, key=lambda x: -x[1])[:k]


def _yorum(home, away, p, lh, la, fh, fa, h2h_df) -> list[str]:
    """Sayıları sade Türkçe cümlelere çevirir. Kural tabanlı, ücretsiz."""
    out = []
    fav = max(("1", home), ("x", None), ("2", away), key=lambda t: p[t[0]])
    if fav[0] == "x":
        out.append(f"Model beraberliği en olası sonuç görüyor (%{p['x'] * 100:.0f}); iki takım birbirine yakın.")
    else:
        pr = p[fav[0]]
        guc = "açık favori" if pr >= 0.60 else ("hafif favori" if pr >= 0.45 else "çok az önde")
        out.append(f"**{fav[1]}** {guc}: kazanma olasılığı %{pr * 100:.0f}.")

    toplam = lh + la
    if toplam >= 3.0:
        out.append(f"Gol beklentisi yüksek ({toplam:.1f}); bol gollü maç ihtimali güçlü.")
    elif toplam <= 2.2:
        out.append(f"Gol beklentisi düşük ({toplam:.1f}); az gollü, kontrollü maç beklenir.")
    else:
        out.append(f"Gol beklentisi orta ({toplam:.1f}).")

    if fh["n"] and fa["n"]:
        d = fh["puan"] - fa["puan"]
        if abs(d) >= 0.8:
            iyi = home if d > 0 else away
            out.append(f"Son {FORM_N} maçta formu belirgin şekilde daha iyi olan taraf {iyi}.")
        else:
            out.append("Son maçlardaki formları birbirine yakın.")

    if len(h2h_df) >= 3:
        res = [_result(r.hg, r.ag) if r.home == home else _result(r.ag, r.hg) for r in h2h_df.itertuples()]
        w, dr, l = res.count("1"), res.count("X"), res.count("2")
        out.append(f"Aralarındaki son {len(res)} maçta {home} {w} galibiyet, {dr} beraberlik, {l} mağlubiyet aldı.")
    else:
        out.append("Aralarında yeterli geçmiş maç yok; bu bölüm az şey söyler.")

    sinyal = []
    for key in ("1x", "x2", "kg_var", "kg_yok", "ust", "alt", "1", "2"):
        if p[key] >= 0.70:
            sinyal.append(f"{markets.LABELS[key]} (%{p[key] * 100:.0f})")
    if sinyal:
        out.append("Modelin en emin olduğu seçenekler: " + ", ".join(sinyal[:3]) + ".")
    else:
        out.append("Model hiçbir seçenekte %70'in üstünde emin değil; belirsiz bir maç.")
    return out


def analyze(home_q: str, away_q: str, div: str | None = None, today: date | None = None) -> str:
    hdiv, home = find_team(home_q, div)
    adiv, away = find_team(away_q, div or hdiv)
    if hdiv != adiv:
        raise SystemExit(f"{home} ({config.LEAGUES[hdiv]}) ve {away} ({config.LEAGUES[adiv]}) farklı liglerde.")
    div = hdiv
    df = data.load_results(div)
    mdl = model.fit(df)
    m = mdl.score_matrix(home, away)
    p = markets.probabilities(m)
    lh, la = mdl.rates(home, away)
    fh, fa = _form(df, home), _form(df, away)
    fh_ev, fa_dep = _form(df, home, "ev"), _form(df, away, "dep")
    h2h_df = _h2h(df, home, away)
    today = today or date.today()

    L = [
        f"# Maç Analizi: {home} – {away}",
        "",
        f"{config.LEAGUES[div]} · {today:%d.%m.%Y} · son veri: {df['date'].max():%d.%m.%Y}",
        "",
        "## Kısa yorum",
        "",
    ]
    L += [f"- {s}" for s in _yorum(home, away, p, lh, la, fh, fa, h2h_df)]

    az = min(mdl.matches_of(home), mdl.matches_of(away))
    if az < config.MIN_TEAM_MATCHES:
        L += ["", f"⚠️ Takımlardan birinin veride sadece {az} maçı var; tahmin güvenilirliği düşük."]

    L += [
        "",
        "## Model tahmini",
        "",
        f"Gol beklentisi: {home} **{lh:.2f}** – **{la:.2f}** {away}",
        "",
        "| Seçenek | Olasılık | Değerli olması için en az oran |",
        "|---|---|---|",
    ]
    for key, label in markets.LABELS.items():
        L.append(f"| {label} | {_pct(p[key])} | {markets.min_odds(p[key]):.2f} |")
    L += ["", "En olası skorlar: " + ", ".join(f"{s} ({_pct(q)})" for s, q in _top_scores(m)), ""]

    L += [
        "## Son form",
        "",
        "G = galibiyet, B = beraberlik, M = mağlubiyet (eskiden yeniye)",
        "",
        "| | Son maçlar | Attığı ort. | Yediği ort. | Maç başı puan | KG Var | 2.5 Üst |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, f in ((f"{home} (tüm)", fh), (f"{home} (evinde)", fh_ev), (f"{away} (tüm)", fa), (f"{away} (deplasmanda)", fa_dep)):
        L.append(
            f"| {name} | {f['seri']} | {f['atilan']:.1f} | {f['yenilen']:.1f} | {f['puan']:.1f} | {_pct(f['kg'])} | {_pct(f['ust'])} |"
        )

    L += ["", f"## Aralarındaki son maçlar", ""]
    if h2h_df.empty:
        L.append("Veride aralarında oynanmış maç yok.")
    else:
        L += ["| Tarih | Maç | Skor |", "|---|---|---|"]
        for r in h2h_df.iloc[::-1].itertuples():
            L.append(f"| {r.date:%d.%m.%Y} | {r.home} – {r.away} | {int(r.hg)}-{int(r.ag)} |")
        kg = ((h2h_df["hg"] > 0) & (h2h_df["ag"] > 0)).mean()
        ust = ((h2h_df["hg"] + h2h_df["ag"]) >= 3).mean()
        L += ["", f"Bu maçlarda KG Var {_pct(kg)}, 2.5 Üst {_pct(ust)}."]

    fx = _fixture_odds(div, home, away)
    L += ["", "## Benzer oranlarla oynanmış geçmiş maçlar", ""]
    if fx and all(np.isfinite(fx[1])):
        when, (o1, ox, o2) = fx
        L.append(f"Maç tarihi {when:%d.%m.%Y}, piyasa oranları: 1 = {o1:.2f}, X = {ox:.2f}, 2 = {o2:.2f}")
        L.append("")
        L += benzer.block(benzer.load_pool(), o1, ox, o2, before=when)
    else:
        L.append(
            "Bu maçın oranı henüz fikstür verisinde yok. Oranları biliyorsan "
            "'Oran sorgula' çalışmasıyla benzer maçlara bakabilirsin."
        )

    L += [
        "",
        "---",
        "Bu analiz yalnızca geçmiş skorlara dayanır; sakatlık, ceza, rotasyon ve motivasyonu bilmez. "
        "Olasılıklar garanti değildir ve bahis sitelerinin oranları genelde bu modelden daha isabetlidir.",
    ]
    return "\n".join(L) + "\n"
