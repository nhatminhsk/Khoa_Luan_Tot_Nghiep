"use client";

import { Box, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import { IconArrowRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { BankAvatar } from "@/components/common/BankLabel";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { LendingRate } from "@/types/api";
import { formatMonth, formatPercent } from "@/utils/format";
import { STALE_MONTHS, isComparableLending, latestMonthOf, lendingBasisText } from "@/utils/lending";

/** Mặc định chỉ hiện chừng này dòng, có nút xem thêm tại chỗ. */
const COLLAPSED = 3;

/**
 * Lãi cho vay bình quân thấp nhất trong các số so được với nhau (`isComparableLending`: khách hàng cá nhân, ngân hàng tự công bố,
 * không cũ) — cùng tập với thẻ Vay của Tổng quan và thẻ số trang Vay. Không đánh số thứ tự: cơ sở tính (khoản vay mới / dư nợ /
 * không ghi) vẫn có thể khác nhau, nên mỗi dòng ghi cơ sở tính thường trực thay vì xếp hạng chung.
 */
export function LendingRatesCard() {
  const [expanded, setExpanded] = useState(false);
  const lending = useQuery({ queryKey: queryKeys.lendingRates, queryFn: marketRepository.lendingRates });

  const all = lending.data ?? [];
  const latestMonth = latestMonthOf(all);
  const pool = all.filter((r) => isComparableLending(r, latestMonth)).sort((a, b) => a.lendingAvgPercent - b.lendingAvgPercent);
  const rows = expanded ? pool : pool.slice(0, COLLAPSED);

  return (
    <SectionCard
      title="Lãi vay bình quân thấp nhất"
      subtitle={`KH cá nhân, NH tự công bố, số trong ${STALE_MONTHS} tháng · ${pool.length}/${all.length || 22} NH`}
      info={`Lãi cho vay bình quân là mức bình quân trên danh mục cho vay khách hàng cá nhân mà ngân hàng công bố, không phải lãi suất bạn được duyệt. Chỉ gồm ngân hàng công bố riêng số khách hàng cá nhân, số không cũ hơn ${STALE_MONTHS} tháng so với tháng mới nhất; mỗi ngân hàng lấy tháng mới nhất có số. Trang Vay có đủ 22 ngân hàng kèm nhãn loại số.`}
      action={
        <Button component={Link} href="/loans" size="small" endIcon={<IconArrowRight size={16} />} sx={{ minHeight: 32 }}>
          Tất cả
        </Button>
      }
    >
      {lending.isError ? (
        <ErrorState error={lending.error} onRetry={() => lending.refetch()} />
      ) : !lending.data ? (
        <LoadingBlock height={180} />
      ) : pool.length === 0 ? (
        <EmptyState title="Chưa có số lãi cho vay khách hàng cá nhân" />
      ) : (
        <>
          <Stack component="ul" spacing={1.5} aria-label="Lãi cho vay bình quân khách hàng cá nhân, thấp đến cao" sx={{ listStyle: "none", m: 0, p: 0 }}>
            {rows.map((row) => (
              <LendingRow key={row.ticker} row={row} />
            ))}
          </Stack>
          {pool.length > COLLAPSED && (
            <Button size="small" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded} sx={{ mt: 1, ml: -1 }}>
              {expanded ? "Thu gọn" : `Xem cả ${pool.length} ngân hàng`}
            </Button>
          )}
          <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1 }}>
            Khác tháng và cơ sở tính; không phải lãi suất được duyệt.
          </Typography>
        </>
      )}
    </SectionCard>
  );
}

function LendingRow({ row }: { row: LendingRate }) {
  return (
    <Stack component="li" direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
      <BankAvatar ticker={row.ticker} size={30} />
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <MuiLink
          component={Link}
          href={`/banks/${row.ticker}?tab=rates`}
          underline="hover"
          color="text.primary"
          variant="body2"
          sx={{ display: "block", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
        >
          {row.shortName}
        </MuiLink>
        <Typography variant="caption" color="text.secondary">
          {formatMonth(row.month)} · {lendingBasisText(row.basis)}
        </Typography>
      </Box>
      <Typography sx={{ fontWeight: 700, fontSize: "1rem", fontVariantNumeric: "tabular-nums" }}>{formatPercent(row.lendingAvgPercent)}</Typography>
    </Stack>
  );
}
