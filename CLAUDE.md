# futbol-iddia — Claude Code için proje notları

Kullanıcı Türkçe konuşur; yanıtları ve rapor metinlerini Türkçe yaz. Adım adım, pratik anlat.
Bahis terimleri Türkçe: MS, KG Var/Yok, ÇŞ (çifte şans), 2.5 Alt/Üst.

## Amaç
`config.LEAGUES` içindeki ligler için maç olasılığı üretmek, piyasa oranıyla kıyaslayıp
değerli seçimleri bulmak ve haftalık Markdown raporu yazmak. Seçim tarzı temkinli:
yüksek olasılık, küçük kasa payı.

## Komutlar
- `python -m iddia indir` — veriyi güncelle (data/raw/, git'e girmez)
- `python -m iddia rapor` — reports/YYYY-AA-GG.md
- `python -m iddia backtest` — model + kural sınaması
- `python -m iddia mac <lig> <ev> <deplasman>`
- `python -m iddia benzer <ms1> <msx> <ms2>` — bu oranlarla açılmış geçmiş maçlar
- `python -m iddia benzer-rapor` — reports/benzer-YYYY-AA-GG.md
- `python -m pytest` — testler

## Otomasyon
`.github/workflows/rapor.yml` salı ve cuma akşamı veriyi indirir, backtest + raporu
`reports/` altına yazıp commit eder. Kullanıcı raporları GitHub'dan okur; bilgisayarında
kurulum yok. `.github/workflows/sorgu.yml` elle çalışır: üç MS oranı alır, benzer
maç tablosunu çalışma özetine yazar.

## Kurallar
- Ücretsiz veri ve araçlarla kal; ücretli API önerme (kullanıcı sormadıkça).
- `config.py` içindeki bir eşiği ya da modeli değiştirince önce/sonra `backtest`
  çalıştır ve farkı göster. Backtest'i iyileştirmek için eşikleri geçmişe uydurma
  (overfit); değişikliğin bir gerekçesi olsun.
- `model.fit(df, as_of=...)` yalnızca `as_of` öncesi maçları kullanır. Bu geleceğe
  bakmama kuralını bozma; `tests/test_model.py` bunu sınar.
- Kesin kazanç vaat eden ifade yazma. Raporlarda olasılık ve belirsizlik açık olsun.
- Veri: football-data.co.uk. Sütunlar `data.py` içindeki `ODDS_COLS` ile eşlenir;
  KG ve çifte şans oranı bu kaynakta yok, o yüzden "en az oran" gösteriliyor.

## Bilinen durum (16.11.2026 ilk gerçek backtest)
Değerli oran kuralları 16 ligin 15'inde zarar etti (lig başına -%0,4 ile -%27 arası),
model log kaybı her ligde piyasadan kötü. Yani "Değerli oranlar" bölümü şu haliyle
para yatırmaya uygun değil; öncelik modeli iyileştirmek.

## Sıradaki fikirler
- `kupon` komutu: oynanan bahisleri CSV'ye kaydet, kâr/zarar ve isabet takibi
- Takım adlarında Türkçe yazımı kabul eden eşleme (Fenerbahçe -> Fenerbahce)
- Şut/isabetli şut verisiyle (HS, HST sütunları) gol beklentisini güçlendirme
- Raporu her pazartesi otomatik üretme (Windows Görev Zamanlayıcı)
