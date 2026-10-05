"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import type { Bank } from "@/types/api";

/** Danh sách 22 ngân hàng (ít đổi, cache lâu) và bảng tra theo mã. */
export function useBanks() {
  const query = useQuery({ queryKey: queryKeys.banks, queryFn: bankRepository.list, staleTime: 60 * 60 * 1000 });
  const byTicker = useMemo(
    () => new Map<string, Bank>((query.data ?? []).map((bank) => [bank.ticker, bank])),
    [query.data],
  );
  return { ...query, banks: query.data ?? [], byTicker };
}
