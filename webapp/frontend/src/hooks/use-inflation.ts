"use client";

import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";

/** Lạm phát theo tháng; số công bố mỗi tháng một lần nên cache lâu. */
export function useInflation() {
  return useQuery({ queryKey: queryKeys.inflation, queryFn: marketRepository.inflation, staleTime: 60 * 60 * 1000 });
}
