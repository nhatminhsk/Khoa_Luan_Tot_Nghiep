from __future__ import annotations

import csv
import http.cookiejar
import json
import random
import ssl
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RA = Path(__file__).resolve().parent / "ket_qua"
CTX = ssl._create_unverified_context()  # chứng chỉ tự ký của môi trường thử (Docker HTTPS)


class Phien:
    def __init__(self, goc: str):
        self.goc = goc.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                              urllib.request.HTTPSHandler(context=CTX))

    def csrf(self) -> str:
        for c in self.jar:
            if c.name == "XSRF-TOKEN":
                return c.value
        self.goi("GET", "/api/v1/auth/session")
        return next((c.value for c in self.jar if c.name == "XSRF-TOKEN"), "")

    def goi(self, method: str, path: str, body=None, raw: bytes | None = None) -> tuple[int, dict | str, float]:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.goc + path, data=data, method=method)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if method != "GET":
            req.add_header("X-XSRF-TOKEN", self.csrf())
        t0 = time.perf_counter()
        try:
            with self.op.open(req, timeout=30) as r:
                txt, st = r.read().decode("utf-8", "replace"), r.status
        except urllib.error.HTTPError as e:
            txt, st = e.read().decode("utf-8", "replace"), e.code
        except Exception as e:  # mất kết nối, hết thời gian
            return -1, f"{type(e).__name__}: {e}", time.perf_counter() - t0
        dt = time.perf_counter() - t0
        try:
            return st, json.loads(txt), dt
        except ValueError:
            return st, txt[:200], dt


def _thong_bao(b) -> str:
    if isinstance(b, dict):
        if not b.get("success", True):
            fe = b.get("fieldErrors")
            return f"{b.get('errorCode', '')}: {b.get('message', '')}" + (
                f" ({'; '.join(f'{k}: {v}' for k, v in fe.items())})" if fe else "")
        data = b.get("data")
        if isinstance(data, dict) and isinstance(data.get("offers"), list):
            rk = data.get("ranking") or {}
            return (f"{len(data['offers'])} ngân hàng có sản phẩm; xếp hạng {rk.get('status')}"
                    + (f" ({rk.get('reason')})" if rk.get("reason") else ""))
        return "thành công"
    return str(b)[:240]


GUI = dict(amount=500_000_000, termMonths=12, channel="ONLINE")
VAY = dict(purpose="HOME_PURCHASE", amount=1_000_000_000, termMonths=240, repayment="DECLINING_BALANCE")
CA = [
    ("Gửi: hợp lệ (đối chứng)", "POST", "/api/v1/advisor/savings", GUI, None),
    ("Gửi: số tiền 0", "POST", "/api/v1/advisor/savings", {**GUI, "amount": 0}, None),
    ("Gửi: số tiền âm", "POST", "/api/v1/advisor/savings", {**GUI, "amount": -5_000_000}, None),
    ("Gửi: số tiền 200 tỷ (vượt trần)", "POST", "/api/v1/advisor/savings", {**GUI, "amount": 200_000_000_000}, None),
    ("Gửi: số tiền là chữ", "POST", "/api/v1/advisor/savings", {**GUI, "amount": "năm trăm triệu"}, None),
    ("Gửi: thiếu kỳ hạn", "POST", "/api/v1/advisor/savings", {k: v for k, v in GUI.items() if k != "termMonths"}, None),
    ("Gửi: kỳ hạn 0 tháng", "POST", "/api/v1/advisor/savings", {**GUI, "termMonths": 0}, None),
    ("Gửi: kênh không tồn tại", "POST", "/api/v1/advisor/savings", {**GUI, "channel": "ATM"}, None),
    ("Gửi: kỳ hạn 9 tháng (không ngân hàng nào có số liệu)", "POST", "/api/v1/advisor/savings",
     {**GUI, "termMonths": 9}, None),
    ("Gửi: kỳ hạn 60 tháng (không có số liệu)", "POST", "/api/v1/advisor/savings", {**GUI, "termMonths": 60}, None),
    ("Gửi: thân yêu cầu không phải JSON", "POST", "/api/v1/advisor/savings", None, b"amount=500000000"),
    ("Vay: hợp lệ (đối chứng)", "POST", "/api/v1/advisor/loans", VAY, None),
    ("Vay: số tiền 5 triệu (dưới mức tối thiểu)", "POST", "/api/v1/advisor/loans", {**VAY, "amount": 5_000_000}, None),
    ("Vay: thời hạn 50 năm", "POST", "/api/v1/advisor/loans", {**VAY, "termMonths": 600}, None),
    ("Vay: mục đích không tồn tại", "POST", "/api/v1/advisor/loans", {**VAY, "purpose": "CASINO"}, None),
    ("Vay: thiếu cách trả nợ", "POST", "/api/v1/advisor/loans", {k: v for k, v in VAY.items() if k != "repayment"}, None),
    ("Hồ sơ ngân hàng không tồn tại", "GET", "/api/v1/banks/XYZ", None, None),
    ("Xếp hạng với mục đích sai", "GET", "/api/v1/rankings?purpose=ABC", None, None),
    ("Chỉ tiêu không tồn tại", "GET", "/api/v1/indicators/khong_co/comparison", None, None),
    ("Trang cá nhân khi chưa đăng nhập", "GET", "/api/v1/me/needs", None, None),
    ("Đã đăng nhập, lưu nhu cầu nhưng thiếu mã CSRF", "POST_NO_CSRF", "/api/v1/me/needs",
     {"name": "thu", "purpose": "SAVINGS", "amount": 500_000_000, "termMonths": 12, "channel": "ONLINE"}, None),
    ("Đường dẫn quản trị khi chưa đăng nhập", "GET", "/api/v1/admin/imports", None, None),
]


def khong_hop_le(goc: str) -> list[dict]:
    rows = []
    for ten, method, path, body, raw in CA:
        s = Phien(goc)
        if method == "POST_NO_CSRF":
            email = f"kiemthu{random.randrange(10**9)}@example.com"
            s.goi("POST", "/api/v1/auth/register", {"email": email, "password": "MatKhauThu#2026", "displayName": "Kiểm thử"})
            data = json.dumps(body).encode()
            req = urllib.request.Request(s.goc + path, data=data, method="POST",
                                         headers={"Content-Type": "application/json"})
            try:
                with s.op.open(req, timeout=30) as r:
                    st, b = r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                st, b = e.code, e.read().decode("utf-8", "replace")
                try:
                    b = json.loads(b)
                except ValueError:
                    pass
        else:
            st, b, _ = s.goi(method, path, body, raw)
        rows.append(dict(truong_hop=ten, phuong_thuc=method.replace("_NO_CSRF", ""), duong_dan=path, ma_http=st,
                         phan_hoi=_thong_bao(b)))
        print(f"  {st}  {ten}: {rows[-1]['phan_hoi']}", flush=True)
    return rows


def _phien_nguoi_dung(goc: str, lap: int, rng: random.Random, ket: list, khoa: threading.Lock, cho: threading.Barrier):
    s = Phien(goc)
    s.csrf()
    cho.wait()
    for _ in range(lap):
        for method, path, body in (
                ("GET", "/api/v1/overview", None),
                ("GET", "/api/v1/rankings?purpose=SAVINGS", None),
                ("POST", "/api/v1/advisor/savings", {**GUI, "amount": rng.choice([1e8, 3e8, 5e8, 1e9, 5e9]).__int__(),
                                                     "termMonths": rng.choice([6, 12, 24])}),
                ("GET", "/api/v1/banks", None),
                ("POST", "/api/v1/advisor/loans", VAY)):
            st, _, dt = s.goi(method, path, body)
            with khoa:
                ket.append((method + " " + path.split("?")[0], st, dt))


def dong_thoi(goc: str, muc: list[int], lap: int = 5) -> list[dict]:
    rows = []
    for n in muc:
        ket, khoa = [], threading.Lock()
        cho = threading.Barrier(n)
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n) as ex:
            for k in range(n):
                ex.submit(_phien_nguoi_dung, goc, lap, random.Random(k), ket, khoa, cho)
        tong = time.perf_counter() - t0
        dts = sorted(d for _, st, d in ket)
        loi = sum(1 for _, st, _ in ket if st != 200)
        q = statistics.quantiles(dts, n=100)
        rows.append(dict(nguoi_dung=n, yeu_cau=len(ket), loi=loi, ty_le_loi=loi / len(ket), thoi_gian_s=round(tong, 2),
                         yeu_cau_moi_giay=round(len(ket) / tong, 1), trung_vi_s=round(statistics.median(dts), 3),
                         p95_s=round(q[94], 3), p99_s=round(q[98], 3), lon_nhat_s=round(dts[-1], 3)))
        print(f"  {n} người dùng: {rows[-1]}", flush=True)
        time.sleep(2)
    return rows


def _ghi(rows: list[dict], ten: str):
    RA.mkdir(parents=True, exist_ok=True)
    with open(RA / ten, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("ghi", RA / ten)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    goc = sys.argv[1]
    nhan = sys.argv[sys.argv.index("--nhan") + 1] if "--nhan" in sys.argv else "may_ca_nhan"
    muc = [int(x) for x in (sys.argv[sys.argv.index("--dong-thoi") + 1] if "--dong-thoi" in sys.argv
                            else "10,50,100,200").split(",")]
    if "--chi-dong-thoi" not in sys.argv:
        _ghi(khong_hop_le(goc), f"{nhan}_khong_hop_le.csv")
    if "--chi-khong-hop-le" not in sys.argv:
        _ghi(dong_thoi(goc, muc), f"{nhan}_dong_thoi.csv")


if __name__ == "__main__":
    main()
