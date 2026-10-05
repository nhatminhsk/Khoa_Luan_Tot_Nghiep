
from __future__ import annotations

from pathlib import Path

import pandas as pd

TARGETS = {"nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "npl_percent": "NPL", "casa_percent": "CASA",
           "ldr_computed_percent": "LDR", "roe_ttm_percent": "ROE"}

# Ghi chú điều tra viết tay cho các biến then chốt; số liệu lấy từ eda_ml.py.
MANUAL = {
    "npl_percent": "NVB (đang tái cơ cấu) lên 35% kéo lệch cả phân phối. NPL giảm ở quý 4 rồi tăng lại quý 1.",
    "casa_percent": "So giữa các NH: CASA cao thì vốn rẻ (ρ = −0,95 với COF). Trong từng NH gần như không liên quan. Giảm ở quý 1.",
    "cof_ttm_percent": "Đi theo lãi điều hành, trễ 1–2 quý (số riêng quý). 60% thay đổi là chung cả ngành.",
    "nim_ttm_percent": "Bị ép khi chi phí vốn tăng (trễ khoảng 2 quý).",
    "ldr_computed_percent": "Có xu hướng (drift), không có mùa vụ.",
    "roe_ttm_percent": "Gần như toàn bộ thay đổi là nhiễu riêng từng NH–quý.",
    "roa_ttm_percent": "Trùng thông tin với ROE (VIF ≈ 12): chỉ nên giữ một.",
    "loans_qoq_percent": "Tín dụng dồn vào quý 4 (mùa vụ).",
    "refinancing_rate_pct": "Chỉ đổi 7 lần từ 2019, nên ít điểm để ước lượng độ trễ.",
    "car_asof_percent": "Nhiều NH chỉ công bố CAR theo năm hoặc nửa năm; NVB không có số sau 2024-Q1.",
    "ind_share_C_asof_pct": "Dư nợ theo ngành chép tay từ BCTC năm, còn 33 NH–năm chưa nhập.",
    "ind_share_F_asof_pct": "Dư nợ theo ngành chép tay từ BCTC năm, còn 33 NH–năm chưa nhập.",
    "log_total_assets": "Giả thuyết: NH càng lớn trả lãi tiền gửi càng thấp (ρ = −0,27 với lãi 12 tháng online, chưa có ý nghĩa với 22 NH).",
    "state_own_percent": "Phân ba nhóm rõ: 4 NH trên 40% (BID, VCB, CTG, MBB), 7 NH vài phần trăm, 11 NH bằng 0.",
    "gold_index_yoy_q_pct": "Chỉ số giá vàng (NSO) thiếu 9 quý nằm giữa 2021-Q2 và 2024-Q1.",
}

KIND = {"chung mọi NH": "Chung cho mọi NH (vĩ mô): chỉ giải thích phần biến động chung theo quý.",
        "tĩnh theo NH": "Không đổi theo thời gian: chỉ dùng để so sánh giữa các NH."}


def _vi(x, d=2):
    """Số có dấu kiểu Việt: +0,43 / −0,21."""
    s = f"{abs(x):.{d}f}".replace(".", ",")
    return ("−" if x < 0 else "+") + s


def _num(x, d=1):
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def build(root: Path) -> pd.DataFrame:
    cat = pd.read_csv(root / "data/model/feature_catalog.csv", encoding="utf-8-sig")
    cat = cat[cat.decision == "Giữ"].set_index("feature")
    uni = pd.read_csv(root / "data/model/eda_ml/univariate.csv", encoding="utf-8-sig").set_index("feature")
    ft = pd.read_csv(root / "data/model/eda_ml/feature_target.csv", encoding="utf-8-sig")
    stab = ft[(ft.h == 1) & ft.stable].sort_values("rho", key=abs, ascending=False).groupby("feature").first()
    rows = []
    for f, r in cat.iterrows():
        marks, notes = [], []
        u = uni.loc[f] if f in uni.index else None
        if f in TARGETS:
            marks.append("🎯")
            notes.append(f"Mục tiêu dự báo ({TARGETS[f]}).")
        if f in stab.index:
            s = stab.loc[f]
            marks.append("★")
            notes.append(f"Đi cùng thay đổi {s.label} quý sau (ρ = {_vi(s.rho)}, cùng dấu ở hai nửa giai đoạn).")
        if r["kind"] in KIND:
            notes.append(KIND[r["kind"]])
        flags = str(r["flags"]) if isinstance(r["flags"], str) else ""
        leaks = [TARGETS.get(x.split(":")[1], x.split(":")[1]) for x in flags.split(", ") if x.startswith("leak:")]
        if leaks:
            marks.append("⚠️")
            notes.append(f"Cùng định nghĩa với {', '.join(leaks)} trong cùng quý: chỉ dùng số quý trước.")
        if "as-of" in flags:
            notes.append("Số năm gán cho các quý sau (as-of): đổi theo bậc mỗi năm.")
        if u is not None:
            if u.missing_pct > 10:
                marks.append("⚠️")
                notes.append(f"Thiếu {u.missing_pct:.0f}% ô.")
            if u.outlier_pct > 2:
                if "⚠️" not in marks:
                    marks.append("⚠️")
                who = f", {u.top_outlier_bank_share:.0%} là của {u.top_outlier_bank}" if isinstance(u.top_outlier_bank, str) and u.top_outlier_bank else ""
                notes.append(f"Ngoại lai {_num(u.outlier_pct)}% ô{who}.")
            if abs(u["skew"]) > 2 and u.n_unique > 2:
                marks.append("🔍")
                notes.append(f"Lệch mạnh (skew {_num(u['skew'])}): cần biến đổi nếu dùng mô hình tuyến tính.")
        if f in MANUAL:
            notes.append(MANUAL[f])
        rows.append({"nhóm": r["group"], "cột": f, "ý nghĩa": r["formula"], "đơn vị": r["unit"],
                     "vai trò": r["use"], "ký hiệu": " ".join(dict.fromkeys(marks)), "ghi chú điều tra": " ".join(notes) or "—"})
    return pd.DataFrame(rows)


def to_markdown(d: pd.DataFrame) -> dict:
    """Mỗi nhóm một bảng markdown: Cột | Ý nghĩa | Ghi chú điều tra."""
    out = {}
    for g, sub in d.groupby("nhóm", sort=True):
        lines = ["| Cột | Ý nghĩa | Ghi chú điều tra |", "|---|---|---|"]
        esc = lambda s: str(s).replace("|", "\\|")  # noqa: E731  (công thức |a|+|b| làm vỡ bảng)
        for _, r in sub.iterrows():
            name = f"**{r['cột']}** {r['ký hiệu']}".strip()
            lines.append(f"| {name} | {esc(r['ý nghĩa'])} ({r['đơn vị']}) | {esc(r['ghi chú điều tra'])} |")
        out[g] = "\n".join(lines)
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    d = build(root)
    d.to_csv(Path(__file__).with_name("tu_dien_dac_trung.csv"), index=False, encoding="utf-8-sig")
    print(d.groupby("nhóm").size().to_string())
