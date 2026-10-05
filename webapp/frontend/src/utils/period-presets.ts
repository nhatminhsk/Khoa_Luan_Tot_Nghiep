/**
 * Khoảng thời gian dựng sẵn cho biểu đồ. Mốc tính từ ngày/quý CÓ SỐ LIỆU mới nhất (không phải hôm nay),
 * để "1 tháng" luôn có số kể cả khi dữ liệu cập nhật trễ.
 */

export type DailyPreset = "1M" | "3M" | "6M" | "YTD" | "1Y" | "ALL";
export type QuarterPreset = "3Y" | "5Y" | "ALL";

export const DAILY_PRESETS: { value: DailyPreset; label: string; title: string }[] = [
  { value: "1M", label: "1T", title: "1 tháng" },
  { value: "3M", label: "3T", title: "3 tháng" },
  { value: "6M", label: "6T", title: "6 tháng" },
  { value: "YTD", label: "Từ đầu năm", title: "Từ đầu năm" },
  { value: "1Y", label: "1N", title: "1 năm" },
  { value: "ALL", label: "Tất cả", title: "Toàn bộ số liệu" },
];

export const QUARTER_PRESETS: { value: QuarterPreset; label: string; title: string }[] = [
  { value: "3Y", label: "3 năm", title: "12 quý gần nhất" },
  { value: "5Y", label: "5 năm", title: "20 quý gần nhất" },
  { value: "ALL", label: "Tất cả", title: "Từ 2019" },
];

/** Ngày bắt đầu (ISO "YYYY-MM-DD") của khoảng, tính lùi từ {@code latestIso}; null = không cắt. */
export function dailyPresetStart(preset: DailyPreset, latestIso: string): string | null {
  if (preset === "ALL") return null;
  const [y, m, d] = latestIso.slice(0, 10).split("-").map(Number);
  if (preset === "YTD") return `${y}-01-01`;
  const months = { "1M": 1, "3M": 3, "6M": 6, "1Y": 12 }[preset];
  // Lùi theo tháng dương lịch; ngày 31 lùi vào tháng ngắn thì Date tự tràn sang đầu tháng sau — chấp nhận được cho biểu đồ.
  const start = new Date(Date.UTC(y, m - 1 - months, d));
  return start.toISOString().slice(0, 10);
}

/** Chỉ số các phần tử nằm trong khoảng; {@code dates} là chuỗi ISO tăng dần. */
export function indexesInDailyPreset(dates: string[], preset: DailyPreset): number[] {
  if (dates.length === 0) return [];
  const start = dailyPresetStart(preset, dates[dates.length - 1]);
  return dates.flatMap((d, i) => (start === null || d.slice(0, 10) >= start ? [i] : []));
}

/** Số quý giữ lại (tính cả quý mới nhất); null = giữ hết. */
export function quarterPresetCount(preset: QuarterPreset): number | null {
  return preset === "3Y" ? 12 : preset === "5Y" ? 20 : null;
}

export function pick<T>(values: T[], indexes: number[]): T[] {
  return indexes.map((i) => values[i]);
}
