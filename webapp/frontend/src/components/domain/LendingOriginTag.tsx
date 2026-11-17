"use client";

import { Chip, Tooltip } from "@mui/material";
import type { LendingRateOrigin } from "@/types/api";

/** Chữ ngắn trên nhãn: con số thuộc nhóm khách hàng nào, lấy từ đâu. */
export function lendingOriginLabel(origin: LendingRateOrigin): string {
  if (origin.source === "VIETNAMNET") return "Báo tổng hợp";
  if (origin.segment === "INDIVIDUAL") return "Cá nhân";
  if (origin.segment === "ALL") return "Số chung";
  // Hai nhãn nhóm hẹp giữ ≤ độ rộng "Báo tổng hợp" (87px) để bảng trang Vay không cuộn ngang ở 1280px;
  // tooltip ghi đủ "cá nhân", "ngắn hạn".
  if (origin.segment === "INDIV_MID_LONG") return "Trung dài hạn";
  if (origin.segment === "CONSUMER_SHORT") return "Vay tiêu dùng";
  return "Chưa rõ";
}

/** Giải thích đầy đủ cho tooltip. */
export function describeLendingOrigin(origin: LendingRateOrigin): string {
  const parts: string[] = [];
  if (origin.source === "VIETNAMNET") {
    parts.push(
      "Số do báo VietnamNet tổng hợp, không ghi rõ nhóm khách hàng (thường là số chung). Hệ thống chưa lấy được số trên web ngân hàng cho tháng này.",
    );
  } else if (origin.segment === "INDIVIDUAL") {
    parts.push("Lãi cho vay bình quân khách hàng cá nhân, ngân hàng công bố trên web theo Chỉ thị 01/CT-NHNN.");
  } else if (origin.segment === "ALL") {
    parts.push(
      "Lãi cho vay bình quân chung (cá nhân và doanh nghiệp), ngân hàng công bố trên web; ngân hàng không công bố riêng số khách hàng cá nhân.",
    );
  } else if (origin.segment === "INDIV_MID_LONG") {
    parts.push(
      "Lãi cho vay bình quân khách hàng cá nhân, chỉ các khoản trung và dài hạn. Ngân hàng công bố tách ngắn hạn và trung dài hạn, không có số chung; hệ thống lấy số trung dài hạn vì gần với khoản vay nhiều năm hơn. Không so ngang được với số cá nhân hay số chung của ngân hàng khác.",
    );
  } else if (origin.segment === "CONSUMER_SHORT") {
    parts.push(
      "Lãi cho vay bình quân ngắn hạn phục vụ đời sống, tiêu dùng — nhóm duy nhất ngân hàng công bố. Không phản ánh vay trung dài hạn (như vay mua nhà) và không so ngang được với số cá nhân hay số chung của ngân hàng khác.",
    );
  }
  if (origin.basis === "NEW_LOANS") parts.push("Tính trên các khoản vay mới giải ngân trong kỳ.");
  else if (origin.basis === "OUTSTANDING") parts.push("Tính trên toàn bộ dư nợ.");
  else if (origin.source === "BANK") parts.push("Ngân hàng không ghi tính trên khoản vay mới hay toàn bộ dư nợ.");
  if (origin.sourceUrl) parts.push("Bấm để mở nguồn.");
  return parts.join(" ");
}

/**
 * Nhãn nhỏ cạnh con số lãi cho vay bình quân. Mỗi ngân hàng công bố một con số khác nhau (cá nhân, chung) nên
 * phải ghi rõ đang so số nào. Backend cũ chưa có các trường này thì không hiện gì.
 */
export function LendingOriginTag({ origin }: { origin: LendingRateOrigin }) {
  if (!origin.segment && !origin.source) return null;
  const link = origin.sourceUrl
    ? { component: "a" as const, href: origin.sourceUrl, target: "_blank", rel: "noopener noreferrer", clickable: true }
    : {};
  return (
    <Tooltip title={describeLendingOrigin(origin)}>
      <Chip
        size="small"
        variant="outlined"
        color={origin.source === "BANK" && origin.segment === "INDIVIDUAL" ? "primary" : "default"}
        label={lendingOriginLabel(origin)}
        // Nhỏ hơn Chip small mặc định để cột lãi suất trang Vay không làm bảng cuộn ngang ở màn 1280px.
        sx={{ height: 20, fontSize: "0.6875rem", "& .MuiChip-label": { px: 0.75 } }}
        {...link}
      />
    </Tooltip>
  );
}
