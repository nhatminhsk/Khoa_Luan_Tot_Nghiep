"use client";

import { Box, Link as MuiLink, Stack, Tooltip, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { useChartPalette } from "@/theme/chart-palette";
import type { Channel, DepositRateTable } from "@/types/api";
import { formatDelta, formatPercent, formatTerm } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";

const INK_DARK = "#0b1120";
const INK_LIGHT = "#ffffff";

/**
 * Bản đồ nhiệt lãi suất hôm nay: hàng = kỳ hạn, cột = ngân hàng (sắp theo lãi 12 tháng giảm dần).
 * Màu so trong cùng một kỳ hạn (mỗi hàng một thang), vì lãi các kỳ hạn chênh nhau nhiều — so cả bảng thì hàng ngắn hạn
 * nhạt hết, không thấy được ai trả cao trong kỳ hạn đó. Số in trong ô nên không đọc bằng màu đơn độc;
 * bảng HTML thật nên trình đọc màn hình đọc được như bảng số.
 */
export function RateHeatmapCard() {
  const [channel, setChannel] = useState<Channel>("ONLINE");
  const table = useQuery({ queryKey: queryKeys.depositTable(channel), queryFn: () => marketRepository.depositTable(channel) });

  return (
    <SectionCard
      title="Bản đồ lãi suất hôm nay"
      subtitle={`22 ngân hàng × kỳ hạn · ${CHANNEL_LABEL[channel].toLowerCase()}`}
      info="Mỗi hàng là một kỳ hạn, tô màu so với các ngân hàng khác trong cùng kỳ hạn đó: ô càng nổi là lãi càng cao. Số đậm là mức cao nhất của kỳ hạn. Cột sắp theo lãi 12 tháng giảm dần; ô “—” là ngân hàng không niêm yết kỳ hạn này."
      action={
        <PeriodToggle
          value={channel}
          options={(["ONLINE", "COUNTER"] as Channel[]).map((c) => ({ value: c, label: CHANNEL_LABEL[c], title: CHANNEL_LABEL[c] }))}
          onChange={setChannel}
          ariaLabel="Kênh gửi"
        />
      }
    >
      {table.isError ? (
        <ErrorState error={table.error} onRetry={() => table.refetch()} />
      ) : !table.data ? (
        <LoadingBlock height={320} />
      ) : table.data.rows.length === 0 ? (
        <EmptyState title="Chưa có số liệu lãi suất" />
      ) : (
        <Heatmap data={table.data} />
      )}
    </SectionCard>
  );
}

function Heatmap({ data }: { data: DepositRateTable }) {
  const { sequential } = useChartPalette();
  const banks = [...data.rows].sort((a, b) => (b.cells["12"]?.rate ?? -1) - (a.cells["12"]?.rate ?? -1));
  const terms = data.terms;

  // Min/max và thứ hạng của từng kỳ hạn (ngân hàng cùng mức thì cùng hạng).
  const stats = new Map(
    terms.map((term) => {
      const rates = banks.map((b) => b.cells[String(term)]?.rate).filter((r): r is number => r !== undefined);
      const sorted = [...rates].sort((a, b) => b - a);
      return [term, { min: Math.min(...rates), max: Math.max(...rates), count: rates.length, rankOf: (r: number) => sorted.indexOf(r) + 1 }];
    }),
  );

  const binOf = (term: number, rate: number) => {
    const s = stats.get(term)!;
    const t = s.max === s.min ? 0.5 : (rate - s.min) / (s.max - s.min);
    return Math.min(sequential.length - 1, Math.round(t * (sequential.length - 1)));
  };

  return (
    <Box>
      <Box sx={{ overflowX: "auto", mx: -0.5, pb: 0.5 }}>
        <Box
          component="table"
          aria-label={`Lãi suất niêm yết hôm nay theo ngân hàng và kỳ hạn, kênh ${CHANNEL_LABEL[data.channel].toLowerCase()}`}
          sx={{
            borderCollapse: "separate",
            borderSpacing: "2px", // khe 2px màu nền giữa các ô
            width: "100%",
            minWidth: 22 * 44 + 84,
            tableLayout: "fixed",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <thead>
            <tr>
              <Box component="th" scope="col" sx={{ width: 84 }} />
              {banks.map((b) => (
                <Box component="th" scope="col" key={b.ticker} sx={{ pb: 0.5, fontWeight: 600 }}>
                  <MuiLink
                    component={Link}
                    href={`/banks/${b.ticker}`}
                    underline="hover"
                    color="text.secondary"
                    sx={{ fontSize: "0.6875rem", letterSpacing: "0.02em" }}
                    title={b.shortName}
                  >
                    {b.ticker}
                  </MuiLink>
                </Box>
              ))}
            </tr>
          </thead>
          <tbody>
            {terms.map((term) => {
              const s = stats.get(term)!;
              return (
                <tr key={term}>
                  <Box
                    component="th"
                    scope="row"
                    sx={{ textAlign: "left", pr: 1, fontSize: "0.75rem", fontWeight: 600, color: "text.secondary", whiteSpace: "nowrap" }}
                  >
                    {formatTerm(term)}
                  </Box>
                  {banks.map((b) => {
                    const cell = b.cells[String(term)];
                    if (!cell) {
                      return (
                        <Box
                          component="td"
                          key={b.ticker}
                          sx={{ height: 32, textAlign: "center", fontSize: "0.75rem", color: "text.disabled", bgcolor: "action.hover", borderRadius: 1 }}
                        >
                          —
                        </Box>
                      );
                    }
                    const fill = sequential[binOf(term, cell.rate)];
                    const isTop = cell.rate === s.max;
                    const change = cell.change;
                    return (
                      <Tooltip
                        key={b.ticker}
                        title={`${b.shortName} · ${formatTerm(term)}: ${formatPercent(cell.rate)} · hạng ${s.rankOf(cell.rate)}/${s.count}${
                          change ? ` · ${formatDelta(change)} điểm so với hôm trước` : ""
                        }`}
                      >
                        <Box
                          component="td"
                          sx={{
                            height: 32,
                            textAlign: "center",
                            fontSize: "0.75rem",
                            fontWeight: isTop ? 700 : 500,
                            bgcolor: fill,
                            color: readableInk(fill),
                            borderRadius: 1,
                            cursor: "default",
                            outline: "2px solid transparent",
                            "&:hover": { outlineColor: "text.primary" },
                          }}
                        >
                          {formatPercent(cell.rate).replace("%", "")}
                        </Box>
                      </Tooltip>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </Box>
      </Box>
      <Stack direction="row" spacing={1} sx={{ mt: 1.5, alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          Thấp
        </Typography>
        <Stack direction="row" spacing="2px" aria-hidden>
          {sequential.map((c) => (
            <Box key={c} sx={{ width: 22, height: 10, borderRadius: 0.5, bgcolor: c }} />
          ))}
        </Stack>
        <Typography variant="caption" color="text.secondary">
          Cao (so trong cùng kỳ hạn) · đơn vị %/năm · số đậm là mức cao nhất của kỳ hạn
        </Typography>
      </Stack>
    </Box>
  );
}

/** Chữ trắng hay chữ đậm trên nền ô: chọn bên có tương phản cao hơn. */
function readableInk(hex: string): string {
  const l = luminance(hex);
  const onDark = (1.05) / (l + 0.05);
  const onLight = (l + 0.05) / (luminance(INK_DARK) + 0.05);
  return onDark >= onLight ? INK_LIGHT : INK_DARK;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
