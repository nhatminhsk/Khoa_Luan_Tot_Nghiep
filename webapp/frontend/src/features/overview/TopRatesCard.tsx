"use client";

import { Box, Button, Link as MuiLink, Stack, Tooltip, Typography } from "@mui/material";
import { IconArrowRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { BankAvatar } from "@/components/common/BankLabel";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { useChartPalette } from "@/theme/chart-palette";
import { formatDelta, formatPercent } from "@/utils/format";

const TERM = "12";
const TOP = 6;

/**
 * Danh sách thanh: các ngân hàng trả lãi 12 tháng trực tuyến cao nhất hôm nay.
 * Thanh bắt đầu từ 0 (độ dài đúng tỉ lệ lãi suất), số in ở đầu thanh; ngân hàng cùng mức thì cùng hạng.
 */
export function TopRatesCard() {
  const palette = useChartPalette();
  const table = useQuery({ queryKey: queryKeys.depositTable("ONLINE"), queryFn: () => marketRepository.depositTable("ONLINE") });

  const ranked = (table.data?.rows ?? [])
    .map((row) => ({ ticker: row.ticker, shortName: row.shortName, cell: row.cells[TERM] }))
    .filter((r): r is typeof r & { cell: NonNullable<typeof r.cell> } => Boolean(r.cell))
    .sort((a, b) => b.cell.rate - a.cell.rate);
  const top = ranked.slice(0, TOP);
  const scaleMax = top[0]?.cell.rate ?? 1;

  return (
    <SectionCard
      title="Top lãi 12 tháng hôm nay"
      subtitle="Kênh trực tuyến"
      action={
        <Button component={Link} href="/savings" size="small" endIcon={<IconArrowRight size={16} />} sx={{ minHeight: 32 }}>
          Tất cả
        </Button>
      }
      sx={{ height: "100%" }}
    >
      {table.isError ? (
        <ErrorState error={table.error} onRetry={() => table.refetch()} />
      ) : !table.data ? (
        <LoadingBlock height={300} />
      ) : top.length === 0 ? (
        <EmptyState title="Chưa có số liệu lãi suất" />
      ) : (
        <Stack component="ol" spacing={1.75} sx={{ listStyle: "none", m: 0, p: 0 }} aria-label="Ngân hàng trả lãi 12 tháng trực tuyến cao nhất">
          {top.map((row) => {
            const rank = ranked.findIndex((r) => r.cell.rate === row.cell.rate) + 1;
            const change = row.cell.change;
            return (
              <Stack component="li" key={row.ticker} direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ width: 14, textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}
                >
                  {rank}
                </Typography>
                <BankAvatar ticker={row.ticker} size={30} />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "baseline", mb: 0.5 }}>
                    <MuiLink
                      component={Link}
                      href={`/banks/${row.ticker}`}
                      underline="hover"
                      color="text.primary"
                      variant="body2"
                      sx={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    >
                      {row.shortName}
                    </MuiLink>
                    <Tooltip
                      title={
                        change === null || change === 0
                          ? "Không đổi so với ngày có số liệu liền trước"
                          : `${formatDelta(change)} điểm % so với ngày có số liệu liền trước`
                      }
                    >
                      <Typography variant="body2" sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums", ml: 1 }}>
                        {formatPercent(row.cell.rate)}
                      </Typography>
                    </Tooltip>
                  </Stack>
                  <Box sx={{ height: 8, borderRadius: 4, bgcolor: "action.hover", overflow: "hidden" }} aria-hidden>
                    <Box
                      sx={{
                        height: "100%",
                        width: `${(row.cell.rate / scaleMax) * 100}%`,
                        borderRadius: 4,
                        bgcolor: palette.series[0],
                      }}
                    />
                  </Box>
                </Box>
              </Stack>
            );
          })}
        </Stack>
      )}
    </SectionCard>
  );
}
