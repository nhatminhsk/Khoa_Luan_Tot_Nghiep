import { apiClient } from "@/lib/http/api-client";
import type {
  Bank,
  BankIndicators,
  BankProgram,
  BankRates,
  LendingRate,
} from "@/types/api";

/** Dữ liệu theo từng ngân hàng — tương ứng các endpoint /api/v1/banks/**. */
export const bankRepository = {
  list: () => apiClient.get<Bank[]>("/banks"),
  get: (ticker: string) => apiClient.get<Bank>(`/banks/${encodeURIComponent(ticker)}`),
  indicators: (ticker: string) => apiClient.get<BankIndicators>(`/banks/${encodeURIComponent(ticker)}/indicators`),
  rates: (ticker: string) => apiClient.get<BankRates>(`/banks/${encodeURIComponent(ticker)}/rates`),
  lendingRates: (ticker: string) => apiClient.get<LendingRate[]>(`/banks/${encodeURIComponent(ticker)}/lending-rates`),
  programs: (ticker: string) => apiClient.get<BankProgram[]>(`/banks/${encodeURIComponent(ticker)}/programs`),
};
