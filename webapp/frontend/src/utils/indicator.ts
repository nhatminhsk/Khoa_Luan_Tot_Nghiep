import type { Indicator, IndicatorDirection, IndicatorUnit } from "@/types/api";
import { formatPercent, formatVndCompact } from "./format";

export function formatIndicator(value: number | null | undefined, unit: IndicatorUnit): string {
  return unit === "VND" ? formatVndCompact(value) : formatPercent(value);
}

/** So sánh hai giá trị theo chiều "tốt hơn"; NEUTRAL thì không có tốt/xấu. */
export function isBetter(a: number, b: number, direction: IndicatorDirection): boolean {
  if (direction === "HIGHER_BETTER") return a > b;
  if (direction === "LOWER_BETTER") return a < b;
  return false;
}

export function directionHint(indicator: Pick<Indicator, "direction">): string {
  switch (indicator.direction) {
    case "HIGHER_BETTER":
      return "Cao hơn là tốt hơn";
    case "LOWER_BETTER":
      return "Thấp hơn là tốt hơn";
    default:
      return "Không có chiều tốt/xấu tuyệt đối";
  }
}

/** "Hạng 3/22" cho chỉ tiêu có chiều tốt; "Lớn thứ 3/22" cho chỉ tiêu trung tính. */
export function rankLabel(rank: number, count: number, direction: IndicatorDirection): string {
  return direction === "NEUTRAL" ? `Lớn thứ ${rank}/${count}` : `Hạng ${rank}/${count}`;
}
