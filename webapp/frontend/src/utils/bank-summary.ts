import type { BankIndicators, IndicatorDirection, IndicatorSeries } from "@/types/api";
import { formatNumber, formatQuarter } from "./format";
import { formatIndicator } from "./indicator";

/**
 * Tóm tắt mô tả một ngân hàng từ chỉ tiêu theo quý: câu tóm tắt và điểm mạnh/điểm yếu theo thứ hạng từng chỉ tiêu.
 * Chỉ là mô tả số liệu (như thẻ chỉ tiêu), không phải điểm tổng hợp — xếp hạng tổng hợp do mô hình đảm nhận.
 */

/** Tên ngắn dùng trong câu văn. */
const SHORT_NAME: Record<string, string> = {
  car: "CAR",
  npl: "nợ xấu",
  loans_g2: "nợ cần chú ý",
  npl_coverage: "bao phủ nợ xấu",
  cir: "CIR",
  nim: "NIM",
  roa: "ROA",
  roe: "ROE",
  cof: "chi phí vốn",
  asset_yield: "lợi suất tài sản",
  casa: "CASA",
  ldr: "LDR",
  loans_growth_yoy: "tăng trưởng dư nợ",
  total_assets: "tổng tài sản",
  deposits: "tiền gửi khách hàng",
};

/** Chỉ tiêu đưa vào câu "so với cùng kỳ", theo thứ tự người gửi tiền quan tâm. */
const SUMMARY_CODES = ["npl", "car", "nim", "roe", "casa"];

/** Điểm mạnh/yếu: nằm trong 3 hạng đầu/cuối của các ngân hàng có số. */
const EXTREME_RANKS = 3;
/** Số của ngân hàng cũ hơn quý mới nhất quá 3 quý thì không đưa vào tóm tắt. */
const MAX_STALE_QUARTERS = 3;

export interface Highlight {
  code: string;
  /** "Nợ xấu thấp", "CAR cao"... */
  label: string;
  rank: number;
  bankCount: number;
  period: string;
}

export interface BankSummary {
  sentences: string[];
  strengths: Highlight[];
  weaknesses: Highlight[];
}

export function summarizeBank(data: BankIndicators): BankSummary {
  const fresh = data.indicators.filter(
    (s) => s.latest && (!data.latestPeriod || quartersBetween(s.latest.period, data.latestPeriod) <= MAX_STALE_QUARTERS),
  );
  const byCode = new Map(fresh.map((s) => [s.indicator.code, s]));

  const sentences: string[] = [];
  const size = byCode.get("total_assets");
  if (data.latestPeriod) {
    sentences.push(
      size?.latest
        ? `Số liệu tài chính mới nhất ${formatQuarter(data.latestPeriod)}: tổng tài sản ${formatIndicator(size.latest.value, "VND")}, lớn thứ ${size.latest.rank}/${size.latest.bankCount} ngân hàng.`
        : `Số liệu tài chính mới nhất ${formatQuarter(data.latestPeriod)}.`,
    );
  }
  const changes = SUMMARY_CODES.flatMap((code) => {
    const series = byCode.get(code);
    const change = series ? yoyChange(series) : null;
    if (!series?.latest || !change) return [];
    const direction = change.delta > 0 ? "tăng" : change.delta < 0 ? "giảm" : "không đổi";
    const amount = change.delta === 0 ? "" : ` ${formatNumber(Math.abs(change.delta), 2)} điểm %`;
    const stale = series.latest.period !== data.latestPeriod ? `, ${formatQuarter(series.latest.period)}` : "";
    return [`${SHORT_NAME[code]} ${formatIndicator(series.latest.value, series.indicator.unit)} (${direction}${amount}${stale})`];
  });
  if (changes.length > 0) {
    sentences.push(`So với cùng kỳ năm trước: ${changes.join("; ")}.`);
  }

  const ranked = fresh.filter((s) => s.indicator.direction !== "NEUTRAL" && s.latest!.bankCount >= 2 * EXTREME_RANKS);
  const strengths = ranked
    .filter((s) => s.latest!.rank <= EXTREME_RANKS)
    .sort((a, b) => a.latest!.rank - b.latest!.rank)
    .map((s) => toHighlight(s, true));
  const weaknesses = ranked
    .filter((s) => s.latest!.rank > s.latest!.bankCount - EXTREME_RANKS)
    .sort((a, b) => b.latest!.rank / b.latest!.bankCount - a.latest!.rank / a.latest!.bankCount)
    .map((s) => toHighlight(s, false));

  return { sentences, strengths, weaknesses };
}

/** Thay đổi (điểm %) so với cùng quý năm trước; null nếu thiếu một trong hai số. */
export function yoyChange(series: IndicatorSeries): { delta: number; previousPeriod: string } | null {
  const latest = series.latest;
  if (!latest || series.indicator.unit !== "PERCENT") return null;
  const match = /^(\d{4})-Q([1-4])$/.exec(latest.period);
  if (!match) return null;
  const previousPeriod = `${Number(match[1]) - 1}-Q${match[2]}`;
  const previous = series.points.find((p) => p.period === previousPeriod)?.value;
  if (previous === null || previous === undefined) return null;
  return { delta: Math.round((latest.value - previous) * 100) / 100, previousPeriod };
}

function toHighlight(series: IndicatorSeries, strong: boolean): Highlight {
  const latest = series.latest!;
  const name = SHORT_NAME[series.indicator.code] ?? series.indicator.name;
  return {
    code: series.indicator.code,
    label: `${capitalize(name)} ${adjective(series.indicator.direction, strong)}`,
    rank: latest.rank,
    bankCount: latest.bankCount,
    period: latest.period,
  };
}

/** Chỉ tiêu "thấp hơn là tốt" mà là điểm mạnh thì "thấp", ngược lại "cao". */
function adjective(direction: IndicatorDirection, strong: boolean): string {
  const lowIsGood = direction === "LOWER_BETTER";
  return strong === lowIsGood ? "thấp" : "cao";
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Số quý từ {@code from} tới {@code to} ("2025-Q4" → "2026-Q2" = 2). */
export function quartersBetween(from: string, to: string): number {
  const parse = (p: string) => {
    const m = /^(\d{4})-Q([1-4])$/.exec(p);
    return m ? Number(m[1]) * 4 + Number(m[2]) - 1 : NaN;
  };
  return parse(to) - parse(from);
}
