import csv
import json
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RA = Path(__file__).resolve().parent / "ket_qua"
CTX = ssl._create_unverified_context()


def goi(url: str) -> tuple[int, float, str]:
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                    timeout=60, context=CTX) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, time.perf_counter() - t0, body[:120]
    except urllib.error.HTTPError as e:
        return e.code, time.perf_counter() - t0, e.read().decode("utf-8", "replace")[:160]
    except Exception as e:
        return -1, time.perf_counter() - t0, f"{type(e).__name__}: {e}"[:160]


def docker(*args) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True).stdout.strip()


def suc_khoe(c: str) -> tuple[str, str]:
    s = json.loads(docker("inspect", c))[0]["State"]
    return s.get("Health", {}).get("Status", "?"), str(json.loads(docker("inspect", c))[0]["RestartCount"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    goc, du_an = sys.argv[1].rstrip("/"), sys.argv[2]
    db, api = f"{du_an}-db-1", f"{du_an}-api-1"
    url = goc + "/api/v1/banks"
    rows = []

    def ghi(pha):
        st, dt, body = goi(url)
        h, rc = suc_khoe(api)
        rows.append(dict(thoi_diem_s=round(time.perf_counter() - T0, 1), pha=pha, ma_http=st, thoi_gian_s=round(dt, 3),
                         suc_khoe_api=h, so_lan_khoi_dong_lai=rc, phan_hoi=body.replace("\n", " ")))
        print(rows[-1], flush=True)
        return st

    T0 = time.perf_counter()
    for _ in range(3):
        ghi("binh_thuong")
    docker("stop", db)
    t_stop = time.perf_counter()
    while time.perf_counter() - t_stop < 75:
        ghi("csdl_dung")
        time.sleep(2)
    docker("start", db)
    t_start = time.perf_counter()
    phuc_hoi = None
    while time.perf_counter() - t_start < 120:
        if ghi("csdl_chay_lai") == 200 and phuc_hoi is None:
            phuc_hoi = time.perf_counter() - t_start
            break
        time.sleep(1)
    for _ in range(3):
        ghi("sau_phuc_hoi")
    RA.mkdir(parents=True, exist_ok=True)
    with open(RA / "docker_mat_csdl.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"phục hồi sau {phuc_hoi:.1f}s kể từ lúc chạy lại CSDL" if phuc_hoi else "KHÔNG phục hồi trong 120 giây")


if __name__ == "__main__":
    main()
