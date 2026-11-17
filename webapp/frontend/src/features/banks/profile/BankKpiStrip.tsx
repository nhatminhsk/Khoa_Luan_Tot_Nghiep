"use client";

import { Box, Card, Skeleton, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { PillarTone } from "@/components/common/PillarCard";
import { lendingOriginLabel } from "@/components/domain/LendingOriginTag";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import type { IndicatorSeries } from "@/types/api";
import { formatDelta, formatMonth, formatPercent, formatQuarter } from "@/utils/format";
import { rankLabel } from "@/utils/indicator";
import { rateDayText } from "@/utils/today";

/** Chỉ tiêu sức khỏe đưa lên dải đầu trang: người gửi/vay xem nợ xấu, vốn, khả năng sinh lời và nguồn vốn rẻ. */
const HEALTH = ["npl", "car", "roe", "casa"] as const;

/**
 * Dải số đầu trang hồ sơ: lãi gửi 12 tháng trực tuyến, lãi cho vay bình quân, và bốn chỉ tiêu sức khỏe kèm hạng trong ngành.
 * Dùng chung cache với các tab bên dưới (không gọi thêm API khi đã mở tab).
 */
export function BankKpiStrip({ ticker }: { ticker: string }) {
  const rates = useQuery({ queryKey: queryKeys.bankRates(ticker), queryFn: () => bankRepository.rates(ticker) });
  const lending = useQuery({ queryKey: queryKeys.bankLending(ticker), queryFn: () => bankRepository.lendingRates(ticker) });
  const indicators = useQuery({ queryKey: queryKeys.bankIndicators(ticker), queryFn: () => bankRepository.indicators(ticker) });

  const r12 = rates.data?.current.find((c) => c.termMonths === 12);
  const loan = [...(lending.data ?? [])].sort((a, b) => b.month.localeCompare(a.month))[0];
  const byCode = new Map((indicators.data?.indicators ?? []).map((s) => [s.indicator.code, s]));

  return (
    <Card sx={{ mb: 2.5 }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2, 1fr)", sm: "repeat(3, 1fr)", lg: "repeat(6, 1fr)" },
          // Đường kẻ giữa các ô: viền trái/trên của từng ô, cắt bỏ ở mép ngoài bằng margin âm của lưới.
          "& > *": { borderLeft: 1, borderTop: 1, borderColor: "divider" },
          m: "-1px 0 0 -1px",
        }}
      >
        <Cell
          tone="deposit"
          label="Lãi gửi 12T trực tuyến"
          loading={rates.isLoading}
          value={formatPercent(r12?.online)}
          note={
            r12?.onlineChange
              ? `${formatDelta(r12.onlineChange)} điểm · ${rateDayText(rates.data?.rateDate)}`
              : rateDayText(rates.data?.rateDate)
          }
        />
        <Cell
          tone="loan"
          label="Lãi vay bình quân"
          loading={lending.isLoading}
          value={formatPercent(loan?.lendingAvgPercent)}
          note={loan ? `${lendingOriginLabel(loan)} · ${formatMonth(loan.month)}` : "Chưa có số"}
        />
        {HEALTH.map((code) => (
          <HealthCell key={code} series={byCode.get(code)} loading={indicators.isLoading} />
        ))}
      </Box>
    </Card>
  );
}

function HealthCell({ series, loading }: { series: IndicatorSeries | undefined; loading: boolean }) {
  const latest = series?.latest ?? null;
  return (
    <Cell
      tone="health"
      label={series ? shortName(series.indicator.code, series.indicator.name) : ""}
      loading={loading}
      value={formatPercent(latest?.value)}
      // "Vị trí" (không gọi "hạng"): vị trí trong ngành của riêng chỉ tiêu này, không phải xếp hạng tổng hợp.
      note={
        latest && series
          ? `${series.indicator.direction === "NEUTRAL" ? rankLabel(latest.rank, latest.bankCount, "NEUTRAL") : `Vị trí ${latest.rank}/${latest.bankCount}`} · ${formatQuarter(latest.period)}`
          : "Chưa có số"
      }
    />
  );
}

function Cell({ tone, label, value, note, loading }: { tone: PillarTone; label: string; value: ReactNode; note: ReactNode; loading: boolean }) {
  return (
    <Box sx={{ px: { xs: 1.75, sm: 2 }, py: 1.5, minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" component="div" sx={{ display: "flex", alignItems: "center", gap: 0.75 }} noWrap>
        <Box component="span" aria-hidden sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: `${tone}.main`, flexShrink: 0 }} />
        {label}
      </Typography>
      {loading ? (
        <Skeleton width="60%" height={32} />
      ) : (
        <Typography sx={{ fontSize: { xs: "1.25rem", sm: "1.375rem" }, fontWeight: 700, lineHeight: 1.3 }}>{value}</Typography>
      )}
      <Typography variant="caption" color="text.secondary" component="div" noWrap>
        {note}
      </Typography>
    </Box>
  );
}

/** Tên ngắn cho ô hẹp. */
function shortName(code: string, fallback: string): string {
  return ({ npl: "Nợ xấu (NPL)", car: "Hệ số an toàn vốn", roe: "ROE", casa: "Tỷ lệ CASA" } as Record<string, string>)[code] ?? fallback;
}
