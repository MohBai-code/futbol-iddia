"""football-data.co.uk'tan sonuç + oran CSV'lerini indirir ve okur (ücretsiz, anahtar gerekmez)."""
from __future__ import annotations

import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd

from . import config

BASE = "https://www.football-data.co.uk"

# Oran sütunları: önce piyasa ortalaması, yoksa Bet365, yoksa Pinnacle
ODDS_COLS = {
    "o_1": ["AvgH", "B365H", "PSH"],
    "o_x": ["AvgD", "B365D", "PSD"],
    "o_2": ["AvgA", "B365A", "PSA"],
    "o_ust": ["Avg>2.5", "B365>2.5", "P>2.5"],
    "o_alt": ["Avg<2.5", "B365<2.5", "P<2.5"],
}


def season_codes(today: date | None = None, n: int = config.N_SEASONS) -> list[str]:
    """2026-11 -> ['2627', '2526', '2425'] (sezon temmuzda başlar)."""
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return [f"{(start - i) % 100:02d}{(start - i + 1) % 100:02d}" for i in range(n)]


def _get(url: str, dest) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
    except Exception as e:  # ağ hatası / 404: diğer dosyalara devam et
        print(f"  ! alınamadı: {url} ({e})")
        return False
    dest.write_bytes(body)
    print(f"  ok  {dest.name} ({len(body) // 1024} KB)")
    return True


def download(leagues=None) -> None:
    """Dosyaları paralel indirir. Biten sezonların dosyası zaten varsa tekrar indirmez
    (GitHub Actions önbelleği sayesinde her çalışmada sadece bu sezon ve fikstür iner)."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    leagues = list(leagues or config.LEAGUES)
    codes = season_codes()
    jobs = []
    for i, code in enumerate(codes):
        for div in leagues:
            dest = config.RAW_DIR / f"{div}_{code}.csv"
            if i > 0 and dest.exists() and dest.stat().st_size > 0:
                continue  # biten sezon değişmez
            jobs.append((f"{BASE}/mmz4281/{code}/{div}.csv", dest))
    jobs.append((f"{BASE}/fixtures.csv", config.RAW_DIR / "fixtures.csv"))
    print(f"{len(jobs)} dosya indirilecek")
    with ThreadPoolExecutor(max_workers=8) as ex:
        ok = sum(ex.map(lambda j: _get(*j), jobs))
    have = any(config.RAW_DIR.glob("*_*.csv"))
    if not ok and not have:
        raise SystemExit("Hiçbir dosya indirilemedi. İnternet bağlantısını kontrol et.")


def _read(path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines="skip")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")
    df = df.dropna(subset=["HomeTeam", "AwayTeam", "Date"])
    out = pd.DataFrame(
        {
            "div": df["Div"].astype(str).str.strip(),
            "date": pd.to_datetime(df["Date"], dayfirst=True, errors="coerce"),
            "home": df["HomeTeam"].astype(str).str.strip(),
            "away": df["AwayTeam"].astype(str).str.strip(),
            "hg": pd.to_numeric(df.get("FTHG"), errors="coerce"),
            "ag": pd.to_numeric(df.get("FTAG"), errors="coerce"),
        }
    )
    for name, candidates in ODDS_COLS.items():
        col = pd.Series(float("nan"), index=df.index)
        for c in candidates:
            if c in df.columns:
                col = col.fillna(pd.to_numeric(df[c], errors="coerce"))
        out[name] = col
    return out.dropna(subset=["date"])


def load_results(div: str) -> pd.DataFrame:
    """Bir ligin oynanmış tüm maçları, tarihe göre sıralı."""
    files = sorted(config.RAW_DIR.glob(f"{div}_*.csv"))
    if not files:
        raise FileNotFoundError(f"{div} için veri yok. Önce: python -m iddia indir")
    df = pd.concat([_read(f) for f in files], ignore_index=True)
    df = df.dropna(subset=["hg", "ag"]).drop_duplicates(["date", "home", "away"])
    return df.sort_values("date").reset_index(drop=True)


def load_fixtures() -> pd.DataFrame:
    """Önümüzdeki maçlar (oranlarıyla). Dosya yoksa boş tablo."""
    path = config.RAW_DIR / "fixtures.csv"
    if not path.exists():
        return pd.DataFrame(columns=["div", "date", "home", "away"])
    df = _read(path)
    return df[df["div"].isin(config.LEAGUES)].sort_values("date").reset_index(drop=True)
