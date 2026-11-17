import type {
  CamelsGroup,
  Channel,
  DatasetFrequency,
  LoanPurpose,
  ProgramCategory,
  RepaymentMethod,
} from "@/types/api";

/** Nhãn tiếng Việt cho các mã enum của backend. */

export const CHANNEL_LABEL: Record<Channel, string> = {
  ONLINE: "Trực tuyến",
  COUNTER: "Tại quầy",
};

export const LOAN_PURPOSE_LABEL: Record<LoanPurpose, string> = {
  HOME_PURCHASE: "Mua nhà ở thương mại",
  SOCIAL_HOUSING: "Mua nhà ở xã hội",
  CONSUMER: "Tiêu dùng cá nhân",
  CAR: "Mua ô tô",
  HOUSEHOLD_BUSINESS: "Kinh doanh hộ gia đình",
  AGRICULTURE: "Sản xuất nông, lâm, thủy sản",
};

export const REPAYMENT_LABEL: Record<RepaymentMethod, string> = {
  DECLINING_BALANCE: "Gốc đều, lãi giảm dần",
  ANNUITY: "Trả góp đều hằng tháng",
};

export const REPAYMENT_HINT: Record<RepaymentMethod, string> = {
  DECLINING_BALANCE: "Cách phổ biến ở Việt Nam: tháng đầu trả nhiều nhất, giảm dần về sau.",
  ANNUITY: "Mỗi tháng trả một số tiền bằng nhau; tổng lãi cao hơn một chút.",
};

export const CAMELS_LABEL: Record<CamelsGroup, string> = {
  C: "Vốn (C)",
  A: "Chất lượng tài sản (A)",
  M: "Quản trị (M)",
  E: "Thu nhập (E)",
  L: "Thanh khoản (L)",
  G: "Quy mô và tăng trưởng",
};

export const CAMELS_ORDER: CamelsGroup[] = ["C", "A", "M", "E", "L", "G"];

export const FREQUENCY_LABEL: Record<DatasetFrequency, string> = {
  DAILY: "Hằng ngày",
  MONTHLY: "Hằng tháng",
  QUARTERLY: "Hằng quý",
  SNAPSHOT: "Ảnh chụp",
  IRREGULAR: "Khi có văn bản mới",
};

export const PROGRAM_CATEGORY_LABEL: Record<ProgramCategory, string> = {
  HOUSING: "Nhà ở",
  AGRICULTURE: "Nông nghiệp",
  BUSINESS: "Doanh nghiệp",
  INFRASTRUCTURE: "Hạ tầng",
  OTHER: "Khác",
};

export const DATASET_LABEL: Record<string, string> = {
  rankings: "Xếp hạng ngân hàng",
};

/** Các kỳ hạn gửi tiết kiệm phổ biến hiển thị trên giao diện. */
export const SAVINGS_TERMS = [1, 3, 6, 9, 12, 13, 18, 24, 36] as const;
