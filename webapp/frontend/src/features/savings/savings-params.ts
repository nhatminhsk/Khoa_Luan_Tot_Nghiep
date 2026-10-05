import { z } from "zod";
import type { Channel, SavingsAdviceRequest, SavingsWeights } from "@/types/api";
import { SAVINGS_TERMS } from "@/utils/labels";

/**
 * Tiêu chí gửi tiết kiệm nằm trên URL (?amount=&term=&channel=&w=) để chép link là mở lại đúng kết quả.
 * URL là nguồn sự thật của lần tìm gần nhất; form chỉ là bản nháp cho tới khi bấm "Xem kết quả".
 */
export const DEFAULT_WEIGHTS: SavingsWeights = { rate: 50, safety: 30, app: 20 };

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
  .refine((v) => v.weights.rate + v.weights.safety + v.weights.app > 0, {
    path: ["weights"],
    message: "Chọn ít nhất một tiêu chí quan trọng",
  });

export type SavingsFormValues = z.infer<typeof savingsSchema>;

export function parseSavingsParams(params: URLSearchParams): SavingsAdviceRequest {
  const amount = Number(params.get("amount"));
  const term = Number(params.get("term"));
  const channel = params.get("channel") === "COUNTER" ? "COUNTER" : ("ONLINE" as Channel);
  const [rate, safety, app] = (params.get("w") ?? "").split(",").map(Number);
  const weightsValid = [rate, safety, app].every((w) => Number.isFinite(w) && w >= 0 && w <= 100);
  const weightsUsable = weightsValid && rate + safety + app > 0;
  return {
    amount: Number.isFinite(amount) && amount >= 1_000_000 && amount <= 100_000_000_000 ? amount : 100_000_000,
    termMonths: (SAVINGS_TERMS as readonly number[]).includes(term) ? term : 12,
    channel,
    // Link cũ hoặc nhu cầu đã lưu có thể mang trọng số không cộng đủ 100: quy về tổng 100 để ba thanh trượt khớp.
    weights: weightsUsable ? normalizedWeights({ rate, safety, app }) : DEFAULT_WEIGHTS,
  };
}

export function toSavingsQuery(values: SavingsAdviceRequest): string {
  const params = new URLSearchParams({
    amount: String(values.amount),
    term: String(values.termMonths),
    channel: values.channel,
  });
  if (values.weights) params.set("w", [values.weights.rate, values.weights.safety, values.weights.app].join(","));
  return params.toString();
}

/** Tỉ trọng % của ba tiêu chí sau khi chuẩn hóa về tổng 100. */
export function normalizedWeights(w: SavingsWeights): SavingsWeights {
  const total = w.rate + w.safety + w.app || 1;
  const rate = Math.round((w.rate / total) * 100);
  const safety = Math.round((w.safety / total) * 100);
  return { rate, safety, app: 100 - rate - safety };
}

type WeightKey = keyof SavingsWeights;
const WEIGHT_KEYS: WeightKey[] = ["rate", "safety", "app"];

/**
 * Đặt một tiêu chí thành {@code value} (0–100) và chia phần còn lại cho hai tiêu chí kia theo tỉ lệ đang có giữa
 * chúng, để tổng luôn là 100. Hai tiêu chí kia đều bằng 0 thì chia đều.
 * Ví dụ {50, 30, 20}, kéo "lãi suất" lên 70 → {70, 18, 12}.
 */
export function rebalanceWeights(current: SavingsWeights, key: WeightKey, value: number): SavingsWeights {
  const target = Math.min(100, Math.max(0, Math.round(value)));
  const [first, second] = WEIGHT_KEYS.filter((k) => k !== key);
  const remaining = 100 - target;
  const othersTotal = current[first] + current[second];
  const firstShare = othersTotal > 0 ? Math.round((remaining * current[first]) / othersTotal) : Math.round(remaining / 2);
  return { ...current, [key]: target, [first]: firstShare, [second]: remaining - firstShare };
}
