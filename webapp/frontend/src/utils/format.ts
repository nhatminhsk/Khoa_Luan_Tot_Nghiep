/** Định dạng số, tiền, ngày theo thói quen đọc của người Việt (dấu phẩy thập phân, dấu chấm hàng nghìn). */

const LOCALE = "vi-VN";

const numberCache = new Map<string, Intl.NumberFormat>();
function numberFormat(min: number, max: number): Intl.NumberFormat {
  const key = `${min}-${max}`;
  let format = numberCache.get(key);
  if (!format) {
    format = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: min, maximumFractionDigits: max });
    numberCache.set(key, format);
  }
  return format;
}

export const EMPTY = "—";

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return numberFormat(0, digits).format(value);
}

/** 6.55 → "6,55%". Luôn 2 chữ số thập phân cho lãi suất để các cột thẳng hàng. */
export function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${numberFormat(digits, digits).format(value)}%`;
}

/** Thay đổi điểm %: +0,20 / −0,15 / 0,00. Dùng dấu trừ thật (U+2212) cho dễ đọc. */
export function formatDelta(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  const abs = numberFormat(digits, digits).format(Math.abs(value));
  if (value > 0) return `+${abs}`;
  if (value < 0) return `−${abs}`;
  return abs;
}

/** 100000000 → "100.000.000 ₫". */
export function formatVnd(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${numberFormat(0, 0).format(Math.round(value))} ₫`;
}

/** Số tiền lớn gọn: 1,2 tỷ / 350 triệu / 2.345 nghìn tỷ. */
export function formatVndCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${numberFormat(0, 1).format(value / 1e12)} nghìn tỷ`;
  if (abs >= 1e9) return `${numberFormat(0, 2).format(value / 1e9)} tỷ`;
  if (abs >= 1e6) return `${numberFormat(0, 1).format(value / 1e6)} triệu`;
  return formatVnd(value);
}

/** "2026-09-27" → "27/09/2026". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return EMPTY;
  const [y, m, d] = iso.slice(0, 10).split("-");
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

const DATE_TIME = new Intl.DateTimeFormat(LOCALE, {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "Asia/Ho_Chi_Minh",
});

/** ISO datetime → "27/09/2026 16:05" theo giờ Việt Nam. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return EMPTY;
  const parts = Object.fromEntries(DATE_TIME.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}`;
}

/** "2026-Q2" → "Q2/2026". */
export function formatQuarter(period: string | null | undefined): string {
  if (!period) return EMPTY;
  const match = /^(\d{4})-Q([1-4])$/.exec(period);
  return match ? `Q${match[2]}/${match[1]}` : period;
}

/** "2026-07" → "07/2026". */
export function formatMonth(month: string | null | undefined): string {
  if (!month) return EMPTY;
  const [y, m] = month.split("-");
  return m && y ? `${m}/${y}` : month;
}

/** 240 → "20 năm", 18 → "1 năm 6 tháng", 6 → "6 tháng". */
export function formatTerm(months: number): string {
  const years = Math.floor(months / 12);
  const rest = months % 12;
  if (years === 0) return `${months} tháng`;
  return rest === 0 ? `${years} năm` : `${years} năm ${rest} tháng`;
}

/** Số ngày giữa hai ngày ISO (b − a). */
export function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(b.slice(0, 10)) - Date.parse(a.slice(0, 10))) / 86_400_000);
}
