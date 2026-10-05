import { apiClient } from "@/lib/http/api-client";
import type {
  AppScoreSummary,
  BestRateItem,
  Channel,
  Datasets,
  DepositRateTable,
  Indicator,
  IndicatorComparison,
  IndicatorSnapshot,
  Inflation,
  LendingRate,
  Overview,
  Program,
  Purpose,
  RankingBlock,
  RateChanges,
  RateTrendPoint,
} from "@/types/api";

/** Dữ liệu dùng chung cho cả thị trường (không gắn với một ngân hàng). */
export const marketRepository = {
  overview: () => apiClient.get<Overview>("/overview"),

  depositTable: (channel: Channel) => apiClient.get<DepositRateTable>("/rates/deposit", { channel }),
  bestRates: () => apiClient.get<{ rateDate: string | null; items: BestRateItem[] }>("/rates/deposit/best"),
  rateTrend: (term: number, channel: Channel) =>
    apiClient.get<RateTrendPoint[]>("/rates/deposit/trend", { term, channel }),
  /** Các lần ngân hàng đổi lãi suất trong {@code days} ngày gần nhất (mới nhất trước). */
  rateChanges: (days: number) => apiClient.get<RateChanges>("/rates/deposit/changes", { days }),
  lendingRates: () => apiClient.get<LendingRate[]>("/rates/lending"),

  indicators: () => apiClient.get<Indicator[]>("/indicators"),
  indicatorSnapshot: () => apiClient.get<IndicatorSnapshot>("/indicators/snapshot"),
  indicatorComparison: (code: string, tickers: string[]) =>
    apiClient.get<IndicatorComparison>(`/indicators/${encodeURIComponent(code)}/comparison`, { tickers }),

  appScores: () => apiClient.get<AppScoreSummary[]>("/app-scores"),
  programs: () => apiClient.get<Program[]>("/programs"),
  ranking: (purpose: Purpose, limit = 0) => apiClient.get<RankingBlock>("/rankings", { purpose, limit }),
  datasets: () => apiClient.get<Datasets>("/datasets"),
  /** Lạm phát theo tháng (CPI so cùng kỳ), để tính lãi suất thực. */
  inflation: () => apiClient.get<Inflation>("/macro/inflation"),
};
