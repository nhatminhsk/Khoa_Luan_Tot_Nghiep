import { apiClient } from "@/lib/http/api-client";
import type { LoanAdvice, LoanAdviceRequest, SavingsAdvice, SavingsAdviceRequest } from "@/types/api";

/** Công cụ chọn ngân hàng. Không lưu gì phía máy chủ; muốn lưu nhu cầu thì dùng meRepository.createNeed. */
export const advisorRepository = {
  savings: (request: SavingsAdviceRequest) => apiClient.post<SavingsAdvice>("/advisor/savings", request),
  loans: (request: LoanAdviceRequest) => apiClient.post<LoanAdvice>("/advisor/loans", request),
};
