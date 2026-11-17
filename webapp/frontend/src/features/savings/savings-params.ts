import { z } from "zod";
import type { Channel, SavingsAdviceRequest, SavingsWeights } from "@/types/api";
import { SAVINGS_TERMS } from "@/utils/labels";

/**
 * Tiêu chí gửi tiết kiệm nằm trên URL (?amount=&term=&channel=&w=) để chép link là mở lại đúng kết quả.
 * URL là nguồn sự thật của lần tìm gần nhất; form chỉ là bản nháp cho tới khi bấm "Xem kết quả".
 */
// Hai tiêu chí: lãi suất và độ an toàn. Trường `app` vẫn có trong API/nhu cầu đã lưu nhưng luôn 0 (đã bỏ tiêu chí ứng dụng).
export const DEFAULT_WEIGHTS: SavingsWeights = { rate: 60, safety: 40, app: 0 };

export const savingsSchema = z
  .object({
    amount: z
      .number({ message: "Nhập số tiền gửi" })
      .min(1_000_000, "Số tiền tối thiểu 1 triệu đồng")
      .max(100_000_000_000, "Số tiền tối đa 100 tỷ đồng"),
    termMonths: z.number().refine((v) => (SAVINGS_TERMS as readonly number[]).includes(v), "Chọn kỳ hạn"),
    channel: z.enum(["ONLINE", "COUNTER"]),
    weights: z.object({
      rate: z.number().min(0).max(100),
      safety: z.number().min(0).max(100),
      app: z.number().min(0).max(100),
    }),
  })
  .refine((v) => v.weights.rate + v.weights.safety > 0, {
    path: ["weights"],
    message: "Chọn ít nhất một tiêu chí quan trọng",
  });

export type SavingsFormValues = z.infer<typeof savingsSchema>;

export function parseSavingsParams(params: URLSearchParams): SavingsAdviceRequest {
  const amount = Number(params.get("amount"));
  const term = Number(params.get("term"));
  const channel = params.get("channel") === "COUNTER" ? "COUNTER" : ("ONLINE" as Channel);
  // Link cũ có ba số (lãi suất, an toàn, ứng dụng): bỏ số thứ ba.
  const [rate, safety] = (params.get("w") ?? "").split(",").map(Number);
  const weightsValid = [rate, safety].every((w) => Number.isFinite(w) && w >= 0 && w <= 100);
  const weightsUsable = weightsValid && rate + safety > 0;
  return {
    amount: Number.isFinite(amount) && amount >= 1_000_000 && amount <= 100_000_000_000 ? amount : 100_000_000,
    termMonths: (SAVINGS_TERMS as readonly number[]).includes(term) ? term : 12,
    channel,
    // Link cũ hoặc nhu cầu đã lưu có thể mang trọng số không cộng đủ 100: quy về tổng 100 để hai thanh trượt khớp.
    weights: weightsUsable ? normalizedWeights({ rate, safety, app: 0 }) : DEFAULT_WEIGHTS,
  };
}

export function toSavingsQuery(values: SavingsAdviceRequest): string {
  const params = new URLSearchParams({
    amount: String(values.amount),
    term: String(values.termMonths),
    channel: values.channel,
  });
  // Không ghi trọng số lên URL: xếp hạng lấy trọng số an toàn theo số tiền gửi (link cũ có "w" vẫn đọc được ở trên).
  return params.toString();
}

/** Tỉ trọng % của hai tiêu chí (lãi suất, an toàn) sau khi chuẩn hóa về tổng 100; trọng số ứng dụng luôn 0. */
export function normalizedWeights(w: SavingsWeights): SavingsWeights {
  const total = w.rate + w.safety || 1;
  const rate = Math.round((w.rate / total) * 100);
  return { rate, safety: 100 - rate, app: 0 };
}

type WeightKey = "rate" | "safety";

/** Đặt một tiêu chí thành {@code value} (0–100), tiêu chí kia nhận phần còn lại để tổng luôn là 100. */
export function rebalanceWeights(current: SavingsWeights, key: WeightKey, value: number): SavingsWeights {
  const target = Math.min(100, Math.max(0, Math.round(value)));
  const other: WeightKey = key === "rate" ? "safety" : "rate";
  return { ...current, [key]: target, [other]: 100 - target, app: 0 };
}
