"use client";

import { useColorScheme } from "@mui/material/styles";

/**
 * Màu biểu đồ. Bốn màu định danh lấy theo thứ tự cố định của bảng màu tham chiếu (skill dataviz),
 * đã chạy validate_palette.js trên chính nền thẻ của ứng dụng:
 *  - Sáng (#ffffff): đạt mọi ngưỡng; màu 3–4 tương phản < 3:1 nên biểu đồ nhiều ngân hàng luôn kèm bảng số.
 *  - Tối (#111827): đạt mọi ngưỡng.
 * Màu gắn theo ngân hàng (thứ tự người dùng chọn), không theo hạng — lọc bớt không đổi màu ngân hàng còn lại.
 */
const SERIES = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500"],
} as const;

/** Đường tham chiếu (trung vị 22 ngân hàng): xám trung tính, không phải một "danh mục". */
const REFERENCE = { light: "#8a94a6", dark: "#7b8494" } as const;

/**
 * Thang tuần tự một sắc xanh (thấp → cao), 7 bậc 100→700 lấy từ bảng màu tham chiếu của skill dataviz.
 * Nền sáng: bậc nhạt là "thấp" (lẫn dần vào nền); nền tối đảo đầu thang: bậc tối là "thấp", bậc sáng là "cao".
 * Chỉ dùng cho độ lớn (bản đồ nhiệt); số luôn in trong ô nên không dựa vào màu đơn độc.
 */
const SEQUENTIAL = {
  light: ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
  dark: ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"],
} as const;

/** Vùng khoảng (thấp nhất–cao nhất): màu định danh 1 rất nhạt. */
const BAND = { light: "rgba(42, 120, 214, 0.14)", dark: "rgba(57, 135, 229, 0.24)" } as const;

export interface ChartPalette {
  series: readonly string[];
  reference: string;
  band: string;
  sequential: readonly string[];
}

export function useChartPalette(): ChartPalette {
  const { mode, systemMode } = useColorScheme();
  const resolved = (mode === "system" ? systemMode : mode) === "dark" ? "dark" : "light";
  return { series: SERIES[resolved], reference: REFERENCE[resolved], band: BAND[resolved], sequential: SEQUENTIAL[resolved] };
}
