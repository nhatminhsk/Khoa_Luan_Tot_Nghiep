"use client";

import { Box, Button, Link as MuiLink, Stack, Tooltip, Typography } from "@mui/material";
import { keyframes } from "@mui/material/styles";
import { IconArrowRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { BankAvatar } from "@/components/common/BankLabel";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { useChartPalette } from "@/theme/chart-palette";
import type { Channel } from "@/types/api";
import { formatDelta, formatPercent } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";
import { rateDayText } from "@/utils/today";

const TERM = "12";
/** Số dòng mặc định; Tổng quan truyền ít hơn vì thẻ xếp chồng với thẻ Vay. */
const TOP = 6;

// Giống thẻ KPI (StatTile swapKey): danh sách hiện dần khi đổi kênh để người xem thấy số vừa đổi.
const swapIn = keyframes`
  from { opacity: 0.15; transform: translateY(6px); }
  to { opacity: 1; transform: none; }
`;

/**
 * Danh sách các ngân hàng trả lãi 12 tháng cao nhất hôm nay cho một kênh; ngân hàng cùng mức thì cùng hạng.
 * Mỗi dòng ghi chênh lệch so với trung vị mọi ngân hàng có số. (Trước đây là thanh từ 0: 6,9% và 7,4% dài gần bằng nhau,
 * thanh không cho thêm thông tin; cắt gốc thanh thì lại phóng đại chênh lệch.)
 *
 * @param channel kênh đang hiện; trang Tổng quan truyền kênh của thẻ KPI để hai khối tự chuyển cùng nhau
 */
export function TopRatesCard({ channel = "ONLINE", limit = TOP }: { channel?: Channel; limit?: number }) {
  const palette = useChartPalette();
  // Tải sẵn cả hai kênh: lúc tự chuyển kênh danh sách đổi ngay, không hiện khung chờ.
  const online = useQuery({ queryKey: queryKeys.depositTable("ONLINE"), queryFn: () => marketRepository.depositTable("ONLINE") });
  const counter = useQuery({ queryKey: queryKeys.depositTable("COUNTER"), queryFn: () => marketRepository.depositTable("COUNTER") });
  const table = channel === "COUNTER" ? counter : online;
  const channelText = CHANNEL_LABEL[channel].toLowerCase();

  const ranked = (table.data?.rows ?? [])
    .map((row) => ({ ticker: row.ticker, shortName: row.shortName, cell: row.cells[TERM] }))
    .filter((r): r is typeof r & { cell: NonNullable<typeof r.cell> } => Boolean(r.cell))
    .sort((a, b) => b.cell.rate - a.cell.rate);
  const top = ranked.slice(0, limit);
  // Trung vị của mọi ngân hàng có số ở kỳ hạn/kênh này (không phải của riêng sáu dòng top).
  const mid = ranked.length > 0 ? median(ranked.map((r) => r.cell.rate)) : null;

  return (
    <SectionCard
      title={`Top lãi 12 tháng ${rateDayText(table.data?.rateDate)}`}
      subtitle={mid === null ? CHANNEL_LABEL[channel] : `${CHANNEL_LABEL[channel]} · trung vị ${ranked.length} NH ${formatPercent(mid)}`}
      action={
        <Button
          component={Link}
          href={`/savings?term=${TERM}&channel=${channel}`}
          size="small"
          endIcon={<IconArrowRight size={16} />}
          sx={{ minHeight: 32 }}
        >
          Tất cả
        </Button>
      }
    >
      {table.isError ? (
        <ErrorState error={table.error} onRetry={() => table.refetch()} />
      ) : !table.data ? (
        <LoadingBlock height={300} />
      ) : top.length === 0 ? (
        <EmptyState title="Chưa có số liệu lãi suất" />
      ) : (
        <Stack
          key={channel}
          component="ol"
          spacing={1.75}
          aria-label={`Ngân hàng trả lãi 12 tháng ${channelText} cao nhất`}
          sx={{
            listStyle: "none",
            m: 0,
            p: 0,
            animation: `${swapIn} 1000ms cubic-bezier(0.22, 1, 0.36, 1)`,
            "@media (prefers-reduced-motion: reduce)": { animation: "none" },
          }}
        >
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
                  <MuiLink
                    component={Link}
                    href={`/banks/${row.ticker}`}
                    underline="hover"
                    color="text.primary"
                    variant="body2"
                    sx={{ display: "block", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  >
                    {row.shortName}
                  </MuiLink>
                  {/* Trung tính (không tô xanh): lãi cao hơn trung vị là thông tin so sánh, chưa phải đánh giá ngân hàng. */}
                  {mid !== null && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontVariantNumeric: "tabular-nums" }}>
                      {Math.abs(row.cell.rate - mid) < 1e-9 ? "Bằng trung vị" : `${formatDelta(row.cell.rate - mid)} điểm % so với trung vị`}
                    </Typography>
                  )}
                </Box>
                <Tooltip
                  title={
                    change === null || change === 0
                      ? "Không đổi so với ngày có số liệu liền trước"
                      : `${formatDelta(change)} điểm % so với ngày có số liệu liền trước`
                  }
                >
                  <Typography sx={{ fontWeight: 700, fontSize: "1rem", fontVariantNumeric: "tabular-nums", color: palette.series[0] }}>
                    {formatPercent(row.cell.rate)}
                  </Typography>
                </Tooltip>
              </Stack>
            );
          })}
        </Stack>
      )}
    </SectionCard>
  );
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
