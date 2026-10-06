/**
 * Kiểu dữ liệu trao đổi với backend. Mỗi kiểu khớp 1–1 với một record DTO bên Java
 * (vn.kltn.bankadvisor.module.<module>.dto). Đổi DTO bên Java thì đổi ở đây.
 */

// ===== Vỏ phản hồi chung =====

export interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  errorCode?: string;
  message?: string;
  fieldErrors?: Record<string, string>;
}

export interface PageResponse<T> {
  items: T[];
  page: number;
  size: number;
  totalItems: number;
  totalPages: number;
}

/** Kết quả thuật toán: NOT_AVAILABLE là "chưa có kết quả", không phải lỗi. */
export type ResultStatus = "AVAILABLE" | "NOT_AVAILABLE";

// ===== Ngân hàng, chỉ tiêu =====

export interface Bank {
  ticker: string;
  shortName: string;
  fullName: string;
  appName: string | null;
  /** Cơ cấu sở hữu (ảnh chụp mới nhất); null khi chưa có dữ liệu. */
  ownership: BankOwnership | null;
}

export interface BankOwnership {
  asOfDate: string;
  /** Tỷ lệ sở hữu nhà nước (%). */
  statePercent: number | null;
  foreignPercent: number | null;
  /** Trần sở hữu nước ngoài (%). */
  foreignRoomPercent: number | null;
  source: string | null;
}

// ===== Vĩ mô =====

export interface InflationPoint {
  /** "2026-08" */
  month: string;
  /** CPI so với cùng tháng năm trước (%). */
  yoyPercent: number;
  momPercent: number | null;
}

export interface Inflation {
  latest: InflationPoint | null;
  /** Thông cáo của Tổng cục Thống kê cho tháng mới nhất. */
  sourceUrl: string | null;
  series: InflationPoint[];
}

export type CamelsGroup = "C" | "A" | "M" | "E" | "L" | "G";
export type IndicatorUnit = "PERCENT" | "VND";
export type IndicatorDirection = "HIGHER_BETTER" | "LOWER_BETTER" | "NEUTRAL";

export interface Indicator {
  code: string;
  name: string;
  camelsGroup: CamelsGroup;
  unit: IndicatorUnit;
  direction: IndicatorDirection;
  description: string | null;
}

export interface IndicatorPoint {
  period: string;
  value: number | null;
  median: number | null;
}

export interface IndicatorLatest {
  period: string;
  value: number;
  median: number | null;
  rank: number;
  bankCount: number;
}

export interface IndicatorSeries {
  indicator: Indicator;
  points: IndicatorPoint[];
  latest: IndicatorLatest | null;
}

export interface BankIndicators {
  ticker: string;
  latestPeriod: string | null;
  indicators: IndicatorSeries[];
}

export interface SnapshotCell {
  value: number;
  period: string;
}

export interface IndicatorSnapshot {
  latestPeriod: string | null;
  indicators: Indicator[];
  rows: { ticker: string; shortName: string; values: Record<string, SnapshotCell> }[];
}

export interface IndicatorComparison {
  indicator: Indicator;
  periods: string[];
  banks: { ticker: string; shortName: string; values: (number | null)[] }[];
  median: (number | null)[];
}

// ===== Lãi suất =====

export type Channel = "ONLINE" | "COUNTER";

export interface RateCell {
  rate: number;
  change: number | null;
}

export interface DepositRateTable {
  rateDate: string | null;
  previousDate: string | null;
  channel: Channel;
  terms: number[];
  rows: { ticker: string; shortName: string; cells: Record<string, RateCell> }[];
}

export interface BestRate {
  ticker: string;
  shortName: string;
  rate: number;
  tiedCount: number;
}

export interface BestRateItem {
  termMonths: number;
  online: BestRate | null;
  counter: BestRate | null;
  medianOnline: number | null;
  medianCounter: number | null;
}

export interface RateTrendPoint {
  date: string;
  min: number;
  median: number;
  max: number;
  bankCount: number;
}

/** Một lần ngân hàng đổi lãi suất, so với lần quan sát liền trước (cùng kỳ hạn, cùng kênh). */
export interface RateChange {
  date: string;
  previousDate: string;
  ticker: string;
  shortName: string;
  termMonths: number;
  channel: Channel;
  previousRate: number;
  rate: number;
  change: number;
}

export interface RateChanges {
  latestDate: string | null;
  fromDate: string | null;
  days: number;
  changes: RateChange[];
}

export interface BankRates {
  rateDate: string | null;
  current: {
    termMonths: number;
    online: number | null;
    counter: number | null;
    onlineChange: number | null;
    counterChange: number | null;
  }[];
  history: { date: string; termMonths: number; channel: Channel; rate: number }[];
}

export interface LendingRate {
  ticker: string;
  shortName: string;
  month: string;
  lendingAvgPercent: number;
  depositAvgPercent: number | null;
  sourceUrl: string | null;
}

// ===== Xếp hạng, dự báo (kết quả thuật toán) =====

export type Purpose = "SAVINGS" | "LOAN";

export interface RankingItem {
  rank: number;
  rankLow: number | null;
  rankHigh: number | null;
  ticker: string;
  shortName: string;
  score: number | null;
  groupLabel: string | null;
  topPositive: string | null;
  topNegative: string | null;
}

export interface RankingBlock {
  status: ResultStatus;
  purpose: Purpose;
  asOfPeriod: string | null;
  methodVersion: string | null;
  personalized: boolean;
  items: RankingItem[];
}

export interface ForecastBlock {
  status: ResultStatus;
  originPeriod: string | null;
  indicators: {
    indicatorCode: string;
    method: string | null;
    points: {
      targetPeriod: string;
      horizon: number;
      value: number;
      lower: number | null;
      upper: number | null;
      naiveValue: number | null;
    }[];
  }[];
}

// ===== Ứng dụng ngân hàng =====

export type AppStore = "GOOGLE_PLAY" | "APP_STORE";

export interface AppExperience {
  ticker: string;
  stores: { store: AppStore; appName: string | null; score: number | null; ratings: number | null; snapshotDate: string }[];
  monthly: {
    month: string;
    reviewCount: number;
    meanScore: number | null;
    oneStarShare: number | null;
    fiveStarShare: number | null;
    usable: boolean;
  }[];
  aspects: { status: ResultStatus; items: { period: string; aspect: string; score: number; reviewCount: number }[] };
}

export interface AppScoreSummary {
  ticker: string;
  googlePlayScore: number | null;
  googlePlayRatings: number | null;
  appStoreScore: number | null;
  appStoreRatings: number | null;
}

// ===== Chương trình tín dụng chính sách =====

export type ProgramCategory = "HOUSING" | "AGRICULTURE" | "BUSINESS" | "INFRASTRUCTURE" | "OTHER";

export interface ProgramRateTerm {
  borrowerGroup: string;
  validFrom: string | null;
  validTo: string | null;
  ratePercent: number | null;
  spreadMin: number | null;
  spreadMax: number | null;
  current: boolean;
}

export interface Program {
  code: string;
  name: string;
  category: ProgramCategory;
  participatingTickers: string[];
  listAsOf: string | null;
  rates: ProgramRateTerm[];
}

export interface BankProgram {
  code: string;
  name: string;
  category: ProgramCategory;
  participates: boolean;
  listAsOf: string | null;
  sourceUrl: string | null;
}

// ===== Công cụ chọn ngân hàng =====

export interface SavingsWeights {
  rate: number;
  safety: number;
  app: number;
}

export interface SavingsAdviceRequest {
  amount: number;
  termMonths: number;
  channel: Channel;
  weights?: SavingsWeights;
}

export interface SavingsOffer {
  rateOrder: number;
  ticker: string;
  shortName: string;
  ratePercent: number;
  changeFromPrevious: number | null;
  interest: number;
  maturityAmount: number;
  appScore: number | null;
  /** Bậc số tiền đã áp (ví dụ "Từ 500 triệu"); null khi ngân hàng không chia bậc hoặc dưới mọi bậc. */
  tierLabel: string | null;
}

export interface SavingsAdvice {
  rateDate: string | null;
  amount: number;
  termMonths: number;
  channel: Channel;
  offers: SavingsOffer[];
  ranking: RankingBlock;
}

export type LoanPurpose =
  | "HOME_PURCHASE"
  | "SOCIAL_HOUSING"
  | "CONSUMER"
  | "CAR"
  | "HOUSEHOLD_BUSINESS"
  | "AGRICULTURE";

export type RepaymentMethod = "DECLINING_BALANCE" | "ANNUITY";

export interface LoanAdviceRequest {
  purpose: LoanPurpose;
  amount: number;
  termMonths: number;
  repayment: RepaymentMethod;
}

export interface LoanOffer {
  ticker: string;
  shortName: string;
  month: string;
  monthsBehind: number;
  lendingAvgPercent: number;
  firstPayment: number;
  lastPayment: number;
  totalInterest: number;
  totalPayment: number;
  programCodes: string[];
}

export interface LoanAdvice {
  latestMonth: string | null;
  purpose: LoanPurpose;
  amount: number;
  termMonths: number;
  repayment: RepaymentMethod;
  offers: LoanOffer[];
  programs: Program[];
  ranking: RankingBlock;
}

// ===== Tổng quan, dữ liệu =====

export type DatasetFrequency = "DAILY" | "MONTHLY" | "QUARTERLY" | "SNAPSHOT" | "IRREGULAR";

export interface DatasetSource {
  dataset: string;
  name: string;
  source: string | null;
  frequency: DatasetFrequency;
  lastUpdated: string | null;
  rowCount: number | null;
  coverageNote: string | null;
}

export interface Datasets {
  sources: DatasetSource[];
  algorithmOutputs: {
    dataset: string;
    fileName: string;
    status: ResultStatus;
    rowCount: number;
    lastImportedAt: string | null;
  }[];
}

/** Tóm tắt lãi suất kỳ hạn tham chiếu của một kênh hôm nay so với ngày liền trước. */
export interface MarketSummary {
  referenceTermMonths: number;
  median: number | null;
  highest: BestRate | null;
  lowest: number | null;
  banksQuoted: number;
  banksRaised: number;
  banksLowered: number;
  banksUnchanged: number;
}

export interface Overview {
  rateDate: string | null;
  previousRateDate: string | null;
  /** Kênh trực tuyến. */
  market: MarketSummary;
  /** Kênh tại quầy; null khi backend bản cũ chưa trả trường này. */
  counterMarket: MarketSummary | null;
  bestRates: BestRateItem[];
  savingsRanking: RankingBlock;
  loanRanking: RankingBlock;
  latestQuarter: string | null;
  datasets: DatasetSource[];
}

export type ImportStatus = "RUNNING" | "SUCCESS" | "FAILED";

export interface ImportRun {
  id: number;
  dataset: string;
  fileName: string;
  status: ImportStatus;
  rowCount: number | null;
  message: string | null;
  startedAt: string;
  finishedAt: string | null;
}

export interface ImportSummary {
  outcomes: {
    dataset: string;
    fileName: string;
    status: "IMPORTED" | "UNCHANGED" | "MISSING" | "FAILED";
    loaded: number;
    skipped: number;
    message: string | null;
  }[];
}

// ===== Người dùng =====

export type Role = "USER" | "ADMIN";

export interface User {
  id: number;
  email: string;
  displayName: string;
  role: Role;
  emailVerified: boolean;
}

export interface EmailVerificationStatus {
  email: string;
  verified: boolean;
  /** Lần gửi link gần nhất. */
  sentAt: string | null;
  /** Thời điểm được gửi lại link; null = gửi được ngay (hoặc đã xác minh). */
  resendAvailableAt: string | null;
  /** Hạn của mã 6 số trong email; null = không có mã còn hiệu lực. */
  codeExpiresAt: string | null;
}

export interface SavedNeed {
  id: number;
  purpose: Purpose;
  label: string;
  amount: number;
  termMonths: number;
  channel: Channel | null;
  loanPurpose: LoanPurpose | null;
  repayment: RepaymentMethod | null;
  weightRate: number | null;
  weightSafety: number | null;
  weightApp: number | null;
  updatedAt: string;
}

export type SavedNeedRequest = Omit<SavedNeed, "id" | "updatedAt">;

export interface WatchItem {
  ticker: string;
  shortName: string;
  rateThreshold: number;
  rate12mOnline: number | null;
  change12mOnline: number | null;
  createdAt: string;
}

/** IN_APP: chỉ trong ứng dụng; EMAIL: trong ứng dụng và email. */
export type NotifyChannel = "IN_APP" | "EMAIL";

export interface NotificationSettingsUpdate {
  notifyRateChange: boolean;
  notifyNewRanking: boolean;
  channel: NotifyChannel;
}

export interface NotificationSettings extends NotificationSettingsUpdate {
  email: string;
  /** Hệ thống có bật gửi email không. */
  emailEnabled: boolean;
  emailVerified: boolean;
}

export interface AppNotification {
  id: number;
  type: "RATE_CHANGE" | "NEW_RANKING";
  ticker: string | null;
  title: string;
  body: string;
  createdAt: string;
  read: boolean;
  /** Đã gửi bản sao qua email lúc nào (null nếu chỉ trong ứng dụng). */
  emailedAt: string | null;
}

export type MailMode = "OFF" | "LOG" | "SMTP";

export interface EmailQueueSummary {
  mode: MailMode;
  pending: number;
  sent: number;
  failed: number;
  skipped: number;
  recentFailures: {
    notificationId: number;
    recipient: string;
    title: string;
    attempts: number;
    lastError: string | null;
    createdAt: string;
  }[];
}

export interface EmailDispatchResult {
  emailsSent: number;
  emailsFailed: number;
  notificationsSkipped: number;
}
