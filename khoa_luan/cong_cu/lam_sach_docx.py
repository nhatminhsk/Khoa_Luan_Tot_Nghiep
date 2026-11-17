import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
WM = os.environ.get("WATERMARKS_SERVICE_URL", "http://127.0.0.1:8765")
KEY = os.environ.get("WATERMARKS_SERVER_API_KEY")
VAO = Path(__file__).resolve().parents[1] / "dau_ra" / "khoa_luan.docx"
RA = VAO.with_name("khoa_luan.cleaned.docx")


def goi(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(WM + path, data=data, headers={"Content-Type": "application/json"})
    if KEY:
        req.add_header("Authorization", f"Bearer {KEY}")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


try:
    goi("/health")
except Exception as e:  # noqa: BLE001
    raise SystemExit(f"Dịch vụ remove-ai-marks không chạy ở {WM}: {e}")

cap = goi("/capabilities").get("tools", {})
viec = [(VAO, RA, {"also_layer_a_text": True})]
PDF = VAO.with_suffix(".pdf")
if PDF.exists():
    if cap.get("exiftool") and cap.get("qpdf"):
        viec.append((PDF, PDF.with_name("khoa_luan.cleaned.pdf"), {}))
    else:
        print("Bỏ qua PDF: dịch vụ chưa có exiftool/qpdf (khởi động bằng C:\\Users\\ADMIN\\watermarks-tools\\chay-dich-vu.ps1)")

for vao, ra, opt in viec:
    r = goi("/clean", {"file": base64.b64encode(vao.read_bytes()).decode(), "name": vao.name, "options": opt})
    rep = r.get("report", {})
    ra.write_bytes(base64.b64decode(r["cleaned"]))
    print(f"Đã ghi {ra}")
    for a in rep.get("actions", []):
        print("  -", a)
    print(f"  Còn C2PA: {rep.get('still_has_c2pa')}; còn siêu dữ liệu AI: {rep.get('still_has_ai_metadata')}")
