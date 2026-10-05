import type { Channel, Purpose } from "@/types/api";

/**
 * Khóa cache của TanStack Query, gom một chỗ để invalidate đúng phạm vi.
 * Dữ liệu từ server (danh sách, trạng thái tải, lỗi) do cache quản lý, không cần state toàn cục viết tay.
 */
export const queryKeys = {
  overview: ["overview"] as const,
  datasets: ["datasets"] as const,
  banks: ["banks"] as const,
  bank: (ticker: string) => ["banks", ticker] as const,
  bankIndicators: (ticker: string) => ["banks", ticker, "indicators"] as const,
  bankRates: (ticker: string) => ["banks", ticker, "rates"] as const,
  bankLending: (ticker: string) => ["banks", ticker, "lending"] as const,
  bankApp: (ticker: string) => ["banks", ticker, "app"] as const,
  bankPrograms: (ticker: string) => ["banks", ticker, "programs"] as const,
  bankForecasts: (ticker: string) => ["banks", ticker, "forecasts"] as const,
  indicators: ["indicators"] as const,
  indicatorSnapshot: ["indicators", "snapshot"] as const,
  indicatorComparison: (code: string, tickers: string[]) => ["indicators", code, "comparison", ...tickers] as const,
  depositTable: (channel: Channel) => ["rates", "deposit", channel] as const,
  rateTrend: (term: number, channel: Channel) => ["rates", "trend", term, channel] as const,
  rateChanges: (days: number) => ["rates", "changes", days] as const,
  lendingRates: ["rates", "lending"] as const,
  appScores: ["app-scores"] as const,
  programs: ["programs"] as const,
  ranking: (purpose: Purpose) => ["rankings", purpose] as const,
  inflation: ["macro", "inflation"] as const,

  me: ["auth", "me"] as const,
  needs: ["me", "needs"] as const,
  watchlist: ["me", "watchlist"] as const,
  notifications: ["me", "notifications"] as const,
  unreadCount: ["me", "notifications", "unread"] as const,
  notificationSettings: ["me", "notification-settings"] as const,
  emailVerification: ["me", "email-verification"] as const,
  importRuns: ["admin", "imports"] as const,
  emailQueue: ["admin", "email-queue"] as const,
};
