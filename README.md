# futbol-iddia

16 Avrupa ligi (Süper Lig, Premier League, La Liga, Serie A, Bundesliga, Ligue 1 ve diğerleri) için maç tahmin modeli, değerli oran
taraması ve haftalık analiz raporu. Tamamen ücretsiz veriyle çalışır
(football-data.co.uk, API anahtarı gerekmez).

## Kurulum (Windows)

1. Python 3.10+ kurulu olsun (`python --version`).
2. Bu klasörde bir terminal aç:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Git deposu yap (bir kere):
   ```
   git init
   git add .
   git commit -m "İlk kurulum"
   ```

## Haftalık kullanım

```
python -m iddia indir       # güncel sonuç, oran ve fikstürleri indir
python -m iddia backtest    # model ve kurallar geçmişte nasıl sonuç verdi?
python -m iddia rapor       # reports/2026-11-16.md gibi bir rapor yazar
python -m iddia mac T1 Galatasaray Fenerbahce    # tek maç
```

Lig kodları ve tam liste `iddia/config.py` içinde (`T1` Süper Lig, `E0` Premier League,
`SP1` La Liga, `I1` Serie A, `D1` Bundesliga, `F1` Ligue 1 ...). İstemediğin ligi oradan sil.

## Bilgisayarsız kullanım (GitHub Actions)

Depo GitHub'dayken `.github/workflows/rapor.yml` her salı ve cuma akşamı veriyi
indirir, raporu `reports/` klasörüne yazar ve depoya kaydeder. Raporu telefondan
GitHub'da açıp okuyabilirsin. Elle çalıştırmak için: Actions > Haftalık rapor > Run workflow.
Takım adları veri kaynağındaki gibi yazılır (yanlış yazarsan liste gösterilir).

## Maç analizi (ajan)

İstediğin maçı yaz, geçmişe bakıp tahmin ve açıklamalı yorum versin.

- **Telefondan:** GitHub'da Actions > **Maç analiz et** > Run workflow. Ev sahibi ve deplasman
  takımını yaz (Türkçe harfle yazabilirsin: Fenerbahçe, Beşiktaş). Sonuç çalışmanın özet
  sayfasında görünür ve `reports/analiz/` klasörüne kaydedilir.
- **Komutla:** `python -m iddia analiz Galatasaray Fenerbahçe` (lig kodu isteğe bağlı: `--lig T1`)

Analizde: kısa yorum, model olasılıkları (MS, ÇŞ, KG, 2.5 Alt/Üst), en olası skorlar,
iki takımın son 6 maçlık formu (ev/deplasman ayrı), aralarındaki son 8 maç ve fikstürde
oranı varsa aynı oranlarla açılmış geçmiş maçların sonuçları.

## Benzer oranlı maçlar

"Bu maçla aynı oranlarla açılmış geçmiş maçlar nasıl bitti?" sorusunun cevabı.

- **Otomatik:** her çalışmada `reports/benzer-YYYY-AA-GG.md` yazılır. Haftanın her maçı
  için özet (MS 1/X/2, KG Var, 2.5 Üst yüzdeleri, en sık skorlar) ve benzer maçların listesi.
- **Elle sorgu (telefondan):** GitHub'da Actions > Oran sorgula > Run workflow, üç oranı yaz.
  Sonuç tablosu çalışmanın özet sayfasında görünür.
- **Komutla:** `python -m iddia benzer 1.85 3.50 4.20`

Benzerlik: üç oranın her biri ±%4 yakınında (`config.SIMILAR_TOL`). Oranlar maçtan birkaç
gün önceki piyasa ortalamasıdır; gerçek ilk açılış oranı ücretsiz veride yok.

## Raporu okumak

- **Lig tabloları:** her maç için 1/X/2, KG Var, 2.5 Üst olasılığı ve gol beklentisi.
- **Değerli oranlar:** MS ve 2.5 alt/üst için model olasılığı x piyasa oranı
  en az +%5 getiri vadeden seçimler. "Kasa payı" çeyrek Kelly'dir, en fazla %2.
- **Temkinli seçimler:** çifte şans ve KG için olasılığı %70 üstü seçimler.
  Bu pazarların oranı veride yok; bahis sitendeki oran "En az oran"dan yüksekse oyna.

## Nasıl çalışıyor

| Dosya | İş |
|---|---|
| `iddia/config.py` | Ligler ve tüm eşikler |
| `iddia/data.py` | Veri indirme ve okuma |
| `iddia/model.py` | Zaman ağırlıklı Poisson + Dixon-Coles modeli |
| `iddia/markets.py` | Pazar olasılıkları, değerli oran kuralları, bahis miktarı |
| `iddia/report.py` | Haftalık rapor |
| `iddia/analiz.py` | Tek maç analizi ve Türkçe takım adı eşleme |
| `iddia/backtest.py` | Geçmişe dönük test |

## Dürüst uyarı

Model yalnızca gol geçmişine bakar; sakatlık, ceza, rotasyon, hava, motivasyon bilmez.
Bahis sitelerinin oranları genelde bu tür basit modellerden daha isabetlidir
(backtest çıktısındaki "Model LL / Piyasa LL" bunu gösterir). Raporu karar yerine
ön eleme olarak kullan ve kaybetmeyi göze alamayacağın parayla oynama.
