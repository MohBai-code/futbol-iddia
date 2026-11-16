"""Tüm ayarlar tek yerde. Bir eşiği değiştirmeden önce `python -m iddia backtest` çalıştır."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("IDDIA_ROOT", Path(__file__).resolve().parent.parent))
RAW_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "reports"

# football-data.co.uk lig kodları
# İstemediğin ligin satırını silmen ya da başına # koyman yeterli.
LEAGUES = {
    "T1": "Süper Lig",
    "E0": "Premier League",
    "E1": "Championship",
    "SP1": "La Liga",
    "SP2": "La Liga 2",
    "I1": "Serie A",
    "I2": "Serie B",
    "D1": "Bundesliga",
    "D2": "2. Bundesliga",
    "F1": "Ligue 1",
    "F2": "Ligue 2",
    "N1": "Eredivisie",
    "B1": "Belçika Pro Lig",
    "P1": "Portekiz Ligi",
    "SC0": "İskoçya Premiership",
    "G1": "Yunanistan Süper Lig",
}

N_SEASONS = 3            # indirilecek sezon sayısı (içinde bulunulan dahil)

# --- Model ---
HALF_LIFE_DAYS = 240     # bir maçın ağırlığı bu kadar günde yarıya iner
PRIOR_GOALS = 3.0        # az maçı olan takımı lig ortalamasına çeken ağırlık
RHO = -0.06              # Dixon-Coles düşük skor düzeltmesi (0 = saf Poisson)
MAX_GOALS = 10
MIN_TEAM_MATCHES = 8     # bundan az maçı olan takımın maçına öneri yapılmaz

# --- Değerli oran / temkinli seçim kuralları ---
MIN_PROB = 0.55          # model olasılığı en az
MIN_EDGE = 0.05          # beklenen getiri (olasılık x oran - 1) en az
MAX_EDGE = 0.25          # bundan büyük "avantaj" genelde model hatasıdır, ele
MIN_ODDS = 1.30
KELLY_FRACTION = 0.25    # çeyrek Kelly
MAX_STAKE = 0.02         # tek bahiste kasanın en fazla %2'si

REPORT_DAYS = 7          # rapor kaç gün ilerisini kapsasın
