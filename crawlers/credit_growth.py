from __future__ import annotations

import pandas as pd

from crawlers import macro

HISTORY: list[tuple[int, float, str, str, str, str]] = [
    (
        2018, 13.89, "2018-12-31", "NHNN",
        "https://www.tinnhanhchungkhoan.vn/tang-truong-tin-dung-va-gdp-qua-cac-con-so-"
        "giai-doan-2016-2019-so-sanh-cho-nam-2020-post252898.html",
        "Bao chi thoi diem do giat tit lam tron '14%' (vd Nhan Dan); con so NHNN la 13,89. "
        "Nguon la bai tong hop dan so lieu NHNN, KHONG phai cong bo goc - nen bo sung "
        "trich dan bao cao thuong nien NHNN 2018 truoc khi dua vao luan van.",
    ),
    (
        2019, 13.65, "2019-12-31", "NHNN",
        "https://www.tinnhanhchungkhoan.vn/tang-truong-tin-dung-va-gdp-qua-cac-con-so-"
        "giai-doan-2016-2019-so-sanh-cho-nam-2020-post252898.html",
        "Cung nguon voi 2018. Luu y 13,89 la so cua NAM 2018 - nhieu bang tong hop tren "
        "mang dat nham no vao dong 2019.",
    ),
    (
        2020, 12.13, "2020-12-31", "NHNN",
        "https://vnexpress.net/tin-dung-tang-manh-nhung-ngay-cuoi-nam-2020-4217812.html",
        "Pho Thong doc Dao Minh Tu cong bo tai hop bao chieu 07/01/2021; du no toan nen kinh "
        "te tinh den 31/12/2020 gan 9,2 trieu ty dong. Den 21/12/2020 moi tang 10,14% va NHNN "
        "khi do uoc ca nam ~11% - hon 163 nghin ty duoc giai ngan trong 10 ngay cuoi nam. "
        "Nguon cu (hochiminhcity.gov.vn) da bi go: URL van tra 200 nhung redirect ve trang chu "
        "cong thong tin, khong con con so nao.",
    ),
    (
        2021, 13.53, "2021-12-31", "NHNN",
        "https://dttc.sggp.org.vn/tang-truong-tin-dung-nam-2021-dat-1353-gia-tri-no-co-cau-"
        "luy-ke-khoang-616000-ty-dong-post91184.html",
        "Cong bo tai hop bao NHNN. GSO thoi diem 01/2022 uoc 'co the dat 14%' - la uoc "
        "tinh truoc quyet toan, khong phai so chinh thuc.",
    ),
    (
        2022, 14.50, "2022-12-31", "NHNN",
        "https://thoibaotaichinhvietnam.vn/tin-dung-nam-2022-dat-tang-truong-145-119827.html",
        "So cong bo 04/01/2023. Ban so lieu ve sau con luu hanh muc 14,18 - chenh do "
        "quyet toan lai; neu dung 14,18 phai noi ro lay tu ban nao. Den 21/12/2022 moi "
        "tang 12,87%, hon 170 nghin ty duoc giai ngan trong 10 ngay cuoi nam.",
    ),
    (
        2023, 13.71, "2023-12-31", "NHNN",
        "https://tapchikinhtetaichinh.vn/tang-truong-tin-dung-nam-2023-chinh-thuc-dat-"
        "1371-43543.html",
        "Pho Thong doc Dao Minh Tu cong bo tai hop bao Chinh phu 05/01/2024. Du no toan "
        "nen kinh te ~13,56 trieu ty dong. Da doi sang URL dich: tapchitaichinh.vn "
        "redirect sang tapchikinhtetaichinh.vn (tap chi doi ten).",
    ),
    (
        2024, 15.08, "2024-12-31", "NHNN",
        "https://baodauthau.vn/nam-2024-tang-truong-tin-dung-dat-1508-post172436.html",
        "Pho Thong doc Dao Minh Tu cong bo tai hop bao 07/01/2025. Du no toan he thong "
        "15,3 trieu ty dong. NHNN da noi room 2 lan trong nam (28/08 va 28/11/2024).",
    ),
    (
        2025, 19.01, "2025-12-31", "NHNN",
        "https://tuoitre.vn/tang-truong-tin-dung-nam-2025-hon-19-nhung-nam-2026-se-thap-"
        "hon-20260110193917581.htm",
        "Pho Thong doc Pham Thanh Ha cong bo 09/01/2026; du no 18,58 trieu ty dong. "
        "Cao hon muc 17,87% tung cong bo so bo truoc do. So chi tiet la 19,01; chinh "
        "Tuoi Tre da sua tit tu 'den 19,1%' thanh 'hon 19%' va doi luon slug - day la "
        "URL dich.",
    ),
]


def build() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "year": year,
                "credit_growth_percent": growth,
                "as_of_date": as_of,
                "announced_by": who,
                "source_url": url,
                "note": note,
            }
            for year, growth, as_of, who, url, note in HISTORY
        ],
        columns=macro.CREDIT_GROWTH_COLUMNS,
    ).sort_values("year").reset_index(drop=True)


def write() -> pd.DataFrame:
    macro.ensure_files()
    df = build()
    df.to_csv(macro.credit_growth_path(), index=False, encoding="utf-8-sig")
    print(f"ghi {macro.credit_growth_path()}: {len(df)} nam "
          f"({df['year'].min()} -> {df['year'].max()})")
    return df


def as_monthly_series(df: pd.DataFrame | None = None) -> pd.Series:
    if df is None:
        df = pd.read_csv(macro.credit_growth_path(), encoding="utf-8-sig")
    rows = {
        f"{int(row.year):04d}-{month:02d}": row.credit_growth_percent
        for row in df.itertuples()
        for month in range(1, 13)
    }
    return pd.Series(rows, name="credit_growth_percent").sort_index()


def check_sources(pause: float = 0.4) -> bool:
    import time

    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    })

    ok = True
    for year, growth, _, _, url, _ in HISTORY:
        wanted = f"{growth:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        try:
            r = session.get(url, timeout=45)
        except Exception as exc:
            print(f"!! {year}  KHONG TAI DUOC: {exc}")
            ok = False
            continue
        redirected = r.url.rstrip("/") != url.rstrip("/")
        has_figure = wanted in r.text
        good = r.status_code == 200 and not redirected and has_figure
        ok &= good
        print(f"{'OK ' if good else '!! '}{year}  {r.status_code}  "
              f"redirect={str(redirected):5s}  co \"{wanted}\"={str(has_figure):5s}")
        if redirected:
            print(f"      -> {r.url}")
        time.sleep(pause)

    print("\ntat ca trich dan con song" if ok else "\nCO TRICH DAN HONG - sua HISTORY")
    return ok


def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(macro.credit_growth_path(), encoding="utf-8-sig")

    print(df[["year", "credit_growth_percent", "as_of_date", "announced_by"]].to_string(index=False))

    years = df["year"].tolist()
    missing = [y for y in range(min(years), max(years) + 1) if y not in years]
    print(f"\nnam thieu: {missing or 'khong'}")
    print(f"moi dong co source_url: {df['source_url'].notna().all() and (df['source_url'] != '').all()}")
    print(f"as_of_date deu la 31/12: {(df['as_of_date'].str[5:] == '12-31').all()}")

    growth = df["credit_growth_percent"]
    print(f"khoang: {growth.min():.2f}% - {growth.max():.2f}%, trung binh {growth.mean():.2f}%")
    odd = df[(growth < 5) | (growth > 40)]
    print(f"ngoai khoang 5-40%: {len(odd)} dong")

    try:
        bank = pd.read_csv("data/credit/bank_credit_quarterly.csv", encoding="utf-8-sig")
    except FileNotFoundError:
        print("\n(chua co bank_credit_quarterly.csv de doi chieu)")
        return

    q4 = bank[bank["period"].str.endswith("Q4")].copy()
    q4["year"] = q4["period"].str[:4].astype(int)
    listed = q4.groupby("year")["loans_vnd"].sum()
    listed_growth = (listed.pct_change() * 100).dropna()

    both = pd.concat([listed_growth.rename("niem_yet"),
                      df.set_index("year")["credit_growth_percent"].rename("he_thong")],
                     axis=1).dropna()
    if len(both) >= 3:
        print(f"\ndoi chieu voi tong du no 22 NH niem yet ({len(both)} nam):")
        print(both.round(2).to_string())
        print(f"  tuong quan r = {both['niem_yet'].corr(both['he_thong']):.4f}")
        print(f"  chenh lech trung vi {(both['niem_yet'] - both['he_thong']).median():+.2f} diem")


if __name__ == "__main__":
    import sys

    if "--validate" in sys.argv:
        validate()
    elif "--check-sources" in sys.argv:
        raise SystemExit(0 if check_sources() else 1)
    else:
        validate(write())
