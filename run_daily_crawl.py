from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawlers import (cpi_nso, deposit_24hmoney, deposit_crosscheck, deposit_official, deposit_rates,
                      deposit_techcombank, lending_rates_official, loan_rates, market_index, price, price_index_nso,
                      ranking_panels, select_features, select_features_hf)
from serving import export as serving_export

CRAWLERS = {
    "deposit_rates": deposit_rates.run,
    "deposit_24hmoney": deposit_24hmoney.run,      # doi chung #1, bang HTML, 22/22 ticker
    "deposit_crosscheck": deposit_crosscheck.run,  # doi chung #2, van xuoi CafeF, chi o 12th/online
    # Doi chung #3 (them 03/11/2026, khi 24hmoney dung o 29/10): trang khong co lich su nen ngay nao lo la mat.
    "deposit_techcombank": deposit_techcombank.run,
    # NGUON CHINH tu 07/11/2026: bieu lai suat doc thang tu web / PDF cua tung NH (20/22, thieu MBB, SSB).
    # 24hmoney dung o 29/10; deposit_tiers.read() dung bang nay tu ngay chup dau tien, bu o thieu bang anh chup
    # doc tay roi blog Techcombank. Can Edge headless (BID, PGB, VIB, BVB, HDB, SHB, NVB, TPB, EIB). ~3-4 phut.
    "deposit_official": deposit_official.run,
    "loan_rates": loan_rates.run,
    "price": price.run,
    # VN-Index, VN30: truoc 01/10/2026 chi chay tay nen tung hong 10/09 -> 23/09.
    "market_index": market_index.build,
    # CPI thang (Cuc Thong ke): truoc 06/10/2026 chi chay tay nen web dung o lam phat thang 8 khi thang 9
    # da cong bo. Chi doc vai bai moi nhat; ngay khong co bai moi thi khong them gi.
    "cpi_nso": cpi_nso.run,
    # Chi so gia USD/vang/lam phat co ban, cung bai NSO voi CPI: truoc 07/10/2026 chi chay tay nen file
    # dung o thang 8 khi thang 9 da cong bo. Chi them thang moi / bu o trong, khong ghi de.
    "price_index_nso": price_index_nso.run,
    # Lai cho vay binh quan tu web cua tung ngan hang (Chi thi 01/CT-NHNN), them tu 08/10/2026. So thang,
    # nen ngan hang da co so thang truoc thi bo qua; chi ton thoi gian vao dau thang khi ngan hang dang so moi.
    # Can Microsoft Edge (dung trang JavaScript bang --headless --dump-dom).
    "lending_rates_official": lending_rates_official.run,
    # Ban ngay / thang cua features_selected (them 14/10/2026): doc lai cac file vua crawl, khong goi mang.
    "features_hf": select_features_hf.build,
    # File dau vao xep hang (them 14/10/2026): BCTC quy gan nhat + lai gui ngay moi nhat, lai vay thang moi nhat,
    # diem app 3 thang gan nhat. Truoc do lai suat trong file la trung binh quy, khong khop so web hien.
    "ranking_latest": select_features.write_ranking,
    # Lich su tieu chi xep hang o tan suat goc (them 15/10/2026): lai gui theo ngay, lai vay theo thang, BCTC theo quy.
    "ranking_panels": ranking_panels.build,
    # Chay SAU cac crawler: xuat lai data/serving/ cho web app (webapp/backend tu nap luc 16:00).
    # Khong goi mang; loi o day khong anh huong so lieu da crawl.
    "serving_export": serving_export.main,
}


def main() -> int:
    started_at = datetime.now(timezone.utc).isoformat()
    print(f"=== daily crawl run started {started_at} ===")
    failures = []

    for name, run_func in CRAWLERS.items():
        print(f"\n--- {name} ---")
        try:
            result = run_func()
            print(f"{name}: ok -> {result}")
        except Exception:
            failures.append(name)
            print(f"{name}: FAILED")
            traceback.print_exc()
            with open("crawl_log.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now(timezone.utc).isoformat()}] {name}: FAILED -- "
                        f"{traceback.format_exc(limit=3)}\n")

    print(f"\n=== daily crawl run finished; failures: {failures or 'none'} ===")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
