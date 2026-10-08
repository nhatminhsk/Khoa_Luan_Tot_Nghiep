"""Runs all daily data crawlers, one failure isolated from the next.

Intended to be invoked once a day by Windows Task Scheduler (see README.md for
the exact `schtasks /create` command) so real historical time series accumulate
over the >2 months available before the thesis deadline. Safe to also run by
hand any time -- every crawler here is idempotent for the same day.

Schedule it AFTER the 15:00 close (README uses 15:30). The price crawler stores
whatever the session shows at the time it runs, so a morning run would file an
unfinished session -- that is exactly how the 2026-08-20 rows came to hold
mid-session figures. Running late also means deposit rates are captured after
the banks' own daytime updates. A run before the close is not wasted, though:
crawlers.price refreshes a trailing window, so the next run corrects it.

The last step (serving_export) rewrites data/serving/ for the web app from the
files the crawlers just updated; webapp/backend picks it up at 16:00.

market_index (VN-Index, VN30) joined the daily run on 2026-10-01: run by hand
only, it had left a 10-session gap (10/09 -> 23/09/2026).

price_index_nso (USD / gold price index, core inflation -- same NSO post) joined on
2026-10-07 for the same reason.

cpi_nso (CPI from the NSO press release) joined on 2026-10-06: run by hand only,
the web app kept showing August inflation after September's figure was out
(published 03/10). NSO posts last month's CPI around the 3rd-6th; on other days
the step reads the latest posts and adds nothing.

Does NOT run crawlers.macro here: that module has no daily crawl step (the SBV
policy rate is a manually-logged event series, see crawl_macro.ipynb).

The two deposit cross-check crawlers run right after deposit_rates so all three
readings of the same day land together. They exist because three sources that
claim to publish the same cell disagree by up to 2.1 points -- see the
"Ba nguon, cung mot o" section in README.md. Neither is a replacement for
deposit_rates; they are the independent check the project previously lacked.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawlers import (cpi_nso, deposit_24hmoney, deposit_crosscheck, deposit_rates,
                      loan_rates, market_index, price, price_index_nso)
from serving import export as serving_export

CRAWLERS = {
    "deposit_rates": deposit_rates.run,
    "deposit_24hmoney": deposit_24hmoney.run,      # doi chung #1, bang HTML, 22/22 ticker
    "deposit_crosscheck": deposit_crosscheck.run,  # doi chung #2, van xuoi CafeF, chi o 12th/online
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
