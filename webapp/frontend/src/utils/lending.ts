import type { LendingRateOrigin } from "@/types/api";

/** Số cũ hơn tháng mới nhất chừng này tháng thì coi là cũ (gắn cảnh báo, không đặt cạnh số mới để so). */
export const STALE_MONTHS = 3;

/** Số tháng từ `from` tới `to` (chuỗi "YYYY-MM"). */
export function monthsBetween(from: string, to: string): number {
  const [fy, fm] = from.split("-").map(Number);
  const [ty, tm] = to.split("-").map(Number);
  return (ty - fy) * 12 + (tm - fm);
}

/** Tháng mới nhất trong danh sách (chuỗi "YYYY-MM"). */
export function latestMonthOf(rows: { month: string }[]): string | null {
  return rows.reduce<string | null>((m, r) => (m === null || r.month > m ? r.month : m), null);
}

/**
 * Lãi cho vay bình quân đặt cạnh nhau để so được: số khách hàng cá nhân do chính ngân hàng công bố và không cũ hơn
 * STALE_MONTHS tháng so với tháng mới nhất. Dùng chung cho thẻ Vay ở Tổng quan, danh sách lãi vay và thẻ số trang Vay để ba chỗ
 * luôn chọn cùng một tập. (Cơ sở tính — khoản vay mới hay dư nợ — vẫn có thể khác: ghi ở từng dòng.)
 */
export function isComparableLending(row: LendingRateOrigin & { month: string }, latestMonth: string | null): boolean {
  if (row.source !== "BANK" || row.segment !== "INDIVIDUAL") return false;
  return latestMonth === null || monthsBetween(row.month, latestMonth) < STALE_MONTHS;
}

/** Chữ ngắn cho cơ sở tính. */
export function lendingBasisText(basis: LendingRateOrigin["basis"]): string {
  if (basis === "NEW_LOANS") return "khoản vay mới";
  if (basis === "OUTSTANDING") return "toàn bộ dư nợ";
  return "không ghi cơ sở tính";
}
