import { z } from "zod";
import type { LoanAdviceRequest, LoanPurpose, RepaymentMethod } from "@/types/api";
import { LOAN_PURPOSE_LABEL, REPAYMENT_LABEL } from "@/utils/labels";

export const LOAN_TERMS = [6, 12, 24, 36, 60, 84, 120, 180, 240, 300, 360] as const;
const PURPOSES = Object.keys(LOAN_PURPOSE_LABEL) as LoanPurpose[];
const REPAYMENTS = Object.keys(REPAYMENT_LABEL) as RepaymentMethod[];

export const loanSchema = z.object({
  purpose: z.enum(PURPOSES as [LoanPurpose, ...LoanPurpose[]]),
  amount: z
    .number({ message: "Nhập số tiền vay" })
    .min(10_000_000, "Số tiền vay tối thiểu 10 triệu đồng")
    .max(50_000_000_000, "Số tiền vay tối đa 50 tỷ đồng"),
  termMonths: z.number().refine((v) => (LOAN_TERMS as readonly number[]).includes(v), "Chọn thời hạn"),
  repayment: z.enum(REPAYMENTS as [RepaymentMethod, ...RepaymentMethod[]]),
});

export function parseLoanParams(params: URLSearchParams): LoanAdviceRequest {
  const purpose = params.get("purpose") as LoanPurpose | null;
  const repayment = params.get("repayment") as RepaymentMethod | null;
  const amount = Number(params.get("amount"));
  const term = Number(params.get("term"));
  return {
    purpose: purpose && PURPOSES.includes(purpose) ? purpose : "HOME_PURCHASE",
    amount: Number.isFinite(amount) && amount >= 10_000_000 && amount <= 50_000_000_000 ? amount : 1_000_000_000,
    termMonths: (LOAN_TERMS as readonly number[]).includes(term) ? term : 240,
    repayment: repayment && REPAYMENTS.includes(repayment) ? repayment : "DECLINING_BALANCE",
  };
}

export function toLoanQuery(values: LoanAdviceRequest): string {
  return new URLSearchParams({
    purpose: values.purpose,
    amount: String(values.amount),
    term: String(values.termMonths),
    repayment: values.repayment,
  }).toString();
}
