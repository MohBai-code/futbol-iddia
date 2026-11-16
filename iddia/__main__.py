"""Kullanım: python -m iddia {indir|rapor|backtest|mac}"""
import argparse
import sys

from . import backtest, benzer, config, data, markets, model, report


def main() -> None:
    ap = argparse.ArgumentParser(prog="iddia", description="Futbol tahmin ve değerli oran aracı")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("indir", help="Güncel sonuç, oran ve fikstür verisini indir")
    sub.add_parser("rapor", help="Önümüzdeki haftanın raporunu reports/ altına yaz")
    sub.add_parser("backtest", help="Modeli ve kuralları geçmiş maçlarda sına")
    m = sub.add_parser("mac", help="Tek maç için olasılıklar")
    m.add_argument("lig", choices=list(config.LEAGUES))
    m.add_argument("ev")
    m.add_argument("deplasman")
    b = sub.add_parser("benzer", help="Verilen MS oranlarıyla açılmış geçmiş maçların sonuçları")
    b.add_argument("ms1")
    b.add_argument("msx")
    b.add_argument("ms2")
    sub.add_parser("benzer-rapor", help="Haftanın her maçı için benzer oranlı maç tablosu")
    args = ap.parse_args()
    try:  # Windows konsolunda Türkçe karakterler bozulmasın
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if args.cmd == "indir":
        data.download()
    elif args.cmd == "rapor":
        path = report.write()
        print(f"Rapor yazıldı: {path}")
    elif args.cmd == "benzer":
        try:
            odds = [float(v.replace(",", ".")) for v in (args.ms1, args.msx, args.ms2)]
        except ValueError:
            raise SystemExit("Oranları sayı olarak yaz, örnek: python -m iddia benzer 1.85 3.50 4.20")
        if min(odds) <= 1:
            raise SystemExit("Oranlar 1'den büyük olmalı.")
        print(benzer.query(*odds))
    elif args.cmd == "benzer-rapor":
        print(f"Rapor yazıldı: {benzer.write()}")
    elif args.cmd == "backtest":
        print(backtest.run_all())
    elif args.cmd == "mac":
        mdl = model.fit(data.load_results(args.lig))
        for t in (args.ev, args.deplasman):
            if t not in mdl.teams:
                raise SystemExit(f"Takım bulunamadı: {t}\nSeçenekler: {', '.join(mdl.teams)}")
        p = markets.probabilities(mdl.score_matrix(args.ev, args.deplasman))
        lh, la = mdl.rates(args.ev, args.deplasman)
        print(f"{args.ev} – {args.deplasman}  (gol beklentisi {lh:.2f} – {la:.2f})")
        for key, label in markets.LABELS.items():
            print(f"  {label:<8} %{p[key] * 100:4.0f}   en az oran {markets.min_odds(p[key]):.2f}")


if __name__ == "__main__":
    main()
