import { formatDate } from "@/utils/format";

/** Ngày hôm nay theo giờ Việt Nam, dạng "YYYY-MM-DD" (máy người xem ở múi giờ khác vẫn so đúng với ngày dữ liệu). */
export function vnToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh" }).format(new Date());
}

/** Số ngày từ `isoDate` tới hôm nay (giờ Việt Nam). */
export function daysSince(isoDate: string): number {
  return Math.round((Date.parse(vnToday()) - Date.parse(isoDate.slice(0, 10))) / 86_400_000);
}

/** "hôm nay" khi lãi suất là của hôm nay, không thì "ngày dd/mm/yyyy" — tránh ghi "hôm nay" cho số của ngày cũ. */
export function rateDayText(rateDate: string | null | undefined): string {
  if (!rateDate) return "hôm nay";
  return rateDate.slice(0, 10) === vnToday() ? "hôm nay" : `ngày ${formatDate(rateDate)}`;
}
