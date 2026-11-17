from __future__ import annotations

import pandas as pd

from crawlers import macro

HISTORY: list[tuple[str, str, float, float, float, str, str]] = [
    (
        "2011-10-10", "2210/QĐ-NHNN", 15.0, 13.0, 16.0,
        "https://caselaw.vn/van-ban-phap-luat/188097-quyet-dinh-so-2210-qd-nhnn-ngay-06-10-2011-cua-thong-doc-ngan-hang-nha-nuoc-viet-nam-ve-lai-suat-tai-cap-von-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 06/10/2011, hieu luc 10/10/2011; chi sua tai cap von (15,0) va qua dem (16,0). Tai chiet khau 13,0 giu theo QD 929/QD-NHNN ngay 29/4/2011 (caselaw.vn/van-ban-phap-luat/191002). Them 13/10/2026 de lui mau ve 2012.",
    ),
    (
        "2012-03-13", "407/QĐ-NHNN", 14.0, 12.0, 15.0,
        "https://caselaw.vn/van-ban-phap-luat/184946-quyet-dinh-so-407-qd-nhnn-ngay-12-03-2012-ve-lai-suat-tai-cap-von-tai-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-do-ngan-hang-nha-nuoc-viet-nam-ban-hanh-van-ban-het-hieu-luc",
        "Ky 12/03/2012, hieu luc 13/03/2012. Thay the QD 2210 va QD 929. Doc toan van Dieu 1.",
    ),
    (
        "2012-04-11", "693/QĐ-NHNN", 13.0, 11.0, 14.0,
        "https://caselaw.vn/van-ban-phap-luat/184372-quyet-dinh-so-693-qd-nhnn-ngay-10-04-2012-ve-lai-suat-tai-cap-von-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-nganh-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-ngan-hang-van-ban-het-hieu-luc",
        "Ky 10/04/2012, hieu luc 11/04/2012. Doc toan van Dieu 1.",
    ),
    (
        "2012-05-28", "1081/QĐ-NHNN", 12.0, 10.0, 13.0,
        "https://caselaw.vn/van-ban-phap-luat/183498-quyet-dinh-so-1081-qd-nhnn-ngay-25-05-2012-ve-lai-suat-tai-cap-von-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-ngan-hang-van-ban-het-hieu-luc",
        "Ky 25/05/2012, hieu luc 28/05/2012. Thay the QD 693. Doc toan van Dieu 1.",
    ),
    (
        "2012-06-11", "1196/QĐ-NHNN", 11.0, 9.0, 12.0,
        "https://caselaw.vn/van-ban-phap-luat/183175-quyet-dinh-so-1196-qd-nhnn-ngay-08-06-2012-ve-lai-suat-tai-cap-von-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thiet-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 08/06/2012, hieu luc 11/06/2012. Thay the QD 1081. Doc toan van Dieu 1.",
    ),
    (
        "2012-07-01", "1289/QĐ-NHNN", 10.0, 8.0, 11.0,
        "https://caselaw.vn/van-ban-phap-luat/182692-quyet-dinh-so-1289-qd-nhnn-ngay-29-06-2012-ve-lai-suat-tai-cap-von-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 29/06/2012, hieu luc 01/07/2012. Thay the QD 1196. Doc toan van Dieu 1.",
    ),
    (
        "2012-12-24", "2646/QĐ-NHNN", 9.0, 7.0, 10.0,
        "https://caselaw.vn/van-ban-phap-luat/178652-quyet-dinh-so-2646-qd-nhnn-ngay-21-12-2012-ve-lai-suat-tai-cap-von-lai-suat-tai-chiet-khau-lai-suat-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 21/12/2012, hieu luc 24/12/2012. Thay the QD 1289. Doc toan van Dieu 1.",
    ),
    (
        "2013-03-26", "643/QĐ-NHNN", 8.0, 6.0, 9.0,
        "https://caselaw.vn/van-ban-phap-luat/176604-quyet-dinh-so-643-qd-nhnn-ngay-25-03-2013-ve-lai-suat-tai-cap-von-tai-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 25/03/2013, hieu luc 26/03/2013. Thay the QD 2646. Doc toan van Dieu 1.",
    ),
    (
        "2013-05-13", "1073/QĐ-NHNN", 7.0, 5.0, 8.0,
        "https://caselaw.vn/van-ban-phap-luat/175518-quyet-dinh-so-1073-qd-nhnn-ngay-10-05-2013-ve-lai-suat-cap-von-lai-suat-tai-chiet-khau-lai-suat-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 10/05/2013, hieu luc 13/05/2013. Thay the QD 643. Doc toan van Dieu 1.",
    ),
    (
        "2014-03-18", "496/QĐ-NHNN", 6.5, 4.5, 7.5,
        "https://caselaw.vn/van-ban-phap-luat/166651-quyet-dinh-so-496-qd-nhnn-ngay-17-03-2014-ve-lai-suat-tai-cap-von-lai-suat-tai-chiet-khau-lai-suat-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-va-cho-vay-bu-dap-thieu-hut-von-trong-thanh-toan-bu-tru-cua-ngan-hang-nha-nuoc-viet-nam-doi-voi-cac-ngan-hang-van-ban-het-hieu-luc",
        "Ky 17/03/2014, hieu luc 18/03/2014. Thay the QD 1073; giu nguyen den QD 1424 (10/07/2017).",
    ),
    (
        "2017-07-10", "1424/QĐ-NHNN", 6.25, 4.25, 7.25,
        "https://cafebiz.vn/3-phut-de-hieu-tai-sao-nhnn-cat-giam-lai-suat-la-tin-hieu-tot-"
        "cho-nen-kinh-te-20170714170833637.chn",
        "Muc nen truoc 16/09/2019. Nguon nay neu TRUC TIEP ca ba muc cua QD 1424: 'giam lai "
        "suat tai cap von tu 6,5% xuong 6,25%/nam; lai suat tai chiet khau tu 4,5% xuong "
        "4,25%/nam; lai suat cho vay qua dem ... tu 7,5% xuong 7,25%/nam'. Truoc day o day "
        "tro vao QD 1870 va ghi la 'xac nhan gian tiep' - kiem lai thi toan van QD 1870 CHI "
        "neu muc moi (6,0/4,0/7,0) va cau 'thay the QD 1424', KHONG he chua 6,25 hay 4,25, "
        "nen su xac nhan gian tiep do khong ton tai. Ngay hieu luc suy ra tu QD 1425/QD-NHNN "
        "ban hanh cung ngay 07/07/2017; van nen doi chieu toan van QD 1424 khi trich luan van.",
    ),
    (
        "2019-09-16", "1870/QĐ-NHNN", 6.0, 4.0, 7.0,
        "https://thuviennhadat.vn/vbpl/quyet-dinh-1870-qd-nhnn-2019-lai-suat-tai-cap-von-"
        "chiet-khau-cua-ngan-hang-nha-nuoc-doi-voi-cac-ngan-437242.html",
        "Ky 12/09/2019, hieu luc 16/09/2019. Thay the QD 1424/QD-NHNN.",
    ),
    (
        "2020-03-17", "418/QĐ-NHNN", 5.0, 3.5, 6.0,
        "https://thuviennhadat.vn/vbpl/quyet-dinh-418-qd-nhnn-2020-lai-suat-tai-cap-von-"
        "tai-chiet-khau-thanh-toan-dien-tu-lien-ngan-hang-437234.html",
        "Ky 16/03/2020, hieu luc 17/03/2020. Dot giam thu nhat ung pho Covid-19.",
    ),
    (
        "2020-05-13", "918/QĐ-NHNN", 4.5, 3.0, 5.5,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-918-qd-nhnn-2020-ve-lai-suat-tai-cap-von-"
        "lai-suat-tai-chiet-khau-183413-d1.html",
        "Ky 12/05/2020, hieu luc 13/05/2020. Dot giam thu hai nam 2020.",
    ),
    (
        "2020-10-01", "1728/QĐ-NHNN", 4.0, 2.5, 5.0,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-1728-lai-suat-trong-thanh-toan-dien-tu-"
        "lien-ngan-hang-192035-d1.html",
        "Ky 30/09/2020, hieu luc 01/10/2020. Dot giam thu ba nam 2020; day muc tai cap von "
        "xuong day lich su 4,0%.",
    ),
    (
        "2022-09-23", "1606/QĐ-NHNN", 5.0, 3.5, 6.0,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-1606-qd-nhnn-230061-d1.html",
        "Ky 22/09/2022, hieu luc 23/09/2022. Dot TANG thu nhat (+1,0 diem) sau chu ky noi long.",
    ),
    (
        "2022-10-25", "1809/QĐ-NHNN", 6.0, 4.5, 7.0,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-1809-qd-nhnn-2022-lai-suat-tai-cap-von-"
        "tai-chiet-khau-cho-vay-qua-dem-trong-thanh-toan-dien-tu-lien-ngan-hang-232587-d1.html",
        "Ky 24/10/2022, hieu luc 25/10/2022. Dot TANG thu hai (+1,0 diem); dinh cua chu ky. "
        "Nguon cu (hieuluat.vn) bi Cloudflare chan, tra 403 voi moi request tu dong nen khong "
        "kiem chung duoc; ban tren luatvietnam co toan van. Doi chieu them: "
        "https://baochinhphu.vn/ngan-hang-nha-nuoc-viet-nam-dieu-chinh-cac-muc-lai-suat-dieu-hanh-"
        "102221024210117723.htm",
    ),
    (
        "2023-03-15", "313/QĐ-NHNN", 6.0, 3.5, 6.0,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-313-qd-nhnn-245991-d1.html",
        "Ky 14/03/2023, hieu luc 15/03/2023. Chi giam tai chiet khau (4,5->3,5) va qua dem "
        "(7,0->6,0); tai cap von giu 6,0.",
    ),
    (
        "2023-04-03", "574/QĐ-NHNN", 5.5, 3.5, 6.0,
        "https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/"
        "47507/tu-ngay-03-4-2023-muc-lai-suat-tai-cap-von-la-5-5-nam",
        "Ky 31/03/2023, hieu luc 03/04/2023. Giam tai cap von 6,0->5,5; tai chiet khau giu 3,5.",
    ),
    (
        "2023-05-25", "950/QĐ-NHNN", 5.0, 3.5, 5.5,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-950-qd-nhnn-2023-giam-lai-suat-tai-cap-von-"
        "vay-qua-dem-tu-25-5-253281-d1.html",
        "Ky 23/05/2023, hieu luc 25/05/2023. Giam tai cap von 5,5->5,0; tai chiet khau giu 3,5. "
        "Nguon cu tro vao thuvienphapluat/47487 - trang do da bi bien tap lai tai cho va gio "
        "noi ve QD 1123 (19/06/2023), chi nhac QD 950 gian tiep; URL cu con song nhung khong "
        "con la trich dan cua su kien nay.",
    ),
    (
        "2023-06-19", "1123/QĐ-NHNN", 4.5, 3.0, 5.0,
        "https://luatvietnam.vn/tai-chinh/quyet-dinh-1123-qd-nhnn-2023-lai-suat-cho-vay-qua-dem-"
        "va-cho-vay-bu-dap-thieu-hut-von-255980-d1.html",
        "Ky 16/06/2023, hieu luc 19/06/2023. VAN CON HIEU LUC tinh den 08/2026 - SBV giu nguyen "
        "lai suat dieu hanh suot 2024-2026.",
    ),
]

RATE_TYPES = ("tai_cap_von", "tai_chiet_khau", "cho_vay_qua_dem")


def build_frame() -> pd.DataFrame:
    rows = []
    for effective, decision, *rates, source_url, note in HISTORY:
        for rate_type, rate in zip(RATE_TYPES, rates):
            rows.append({
                "date_effective": effective,
                "rate_type": rate_type,
                "rate_percent": rate,
                "source_url": source_url,
                "note": f"QD {decision}. {note}",
            })
    return pd.DataFrame(rows, columns=macro.POLICY_RATE_COLUMNS)


def as_daily_series(start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    events = build_frame()
    wide = events.pivot(index="date_effective", columns="rate_type", values="rate_percent")
    wide.index = pd.to_datetime(wide.index)

    end = end or pd.Timestamp.today().normalize().strftime("%Y-%m-%d")
    days = pd.date_range(min(wide.index.min(), pd.Timestamp(start)), end, freq="D")
    daily = wide.reindex(wide.index.union(days)).ffill().reindex(days)
    return daily.loc[start:].rename_axis("date").reset_index()


def backfill(write: bool = True) -> pd.DataFrame:
    macro.ensure_files()
    df = build_frame()
    if not write:
        return df

    existing = pd.read_csv(macro.policy_rate_path(), encoding="utf-8-sig")
    merged = pd.concat([existing, df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["date_effective", "rate_type"], keep="last")
    merged = merged.sort_values(["date_effective", "rate_type"])
    merged.to_csv(macro.policy_rate_path(), index=False, encoding="utf-8-sig")
    return merged


if __name__ == "__main__":
    result = backfill()
    events = result["date_effective"].nunique()
    print(f"policy_rate.csv now holds {len(result)} rows across {events} rate-change events: "
          f"{result['date_effective'].min()} -> {result['date_effective'].max()}")
