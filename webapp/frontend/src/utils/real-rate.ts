import type { InflationPoint } from "@/types/api";

/**
 * Lãi suất thực xấp xỉ (điểm %/năm) = lãi niêm yết − lạm phát so cùng kỳ (xấp xỉ Fisher, đủ chính xác khi cả hai
 * dưới 10%). Dương: tiền gửi tăng được sức mua; âm: tiền lãi không bù được mức tăng giá.
 */
export function realRate(nominal: number | null | undefined, inflation: number | null | undefined): number | null {
  if (nominal === null || nominal === undefined || inflation === null || inflation === undefined) return null;
  return Math.round((nominal - inflation) * 100) / 100;
}

/**
 * Lạm phát áp cho từng ngày: lấy tháng của ngày đó; tháng chưa công bố (thường là tháng hiện tại) thì để trống
 * chứ không kéo số tháng trước sang, để biểu đồ không vẽ số chưa có.
 */
export function inflationByDate(dates: string[], series: InflationPoint[]): (number | null)[] {
  const byMonth = new Map(series.map((p) => [p.month, p.yoyPercent]));
  return dates.map((d) => byMonth.get(d.slice(0, 7)) ?? null);
}
