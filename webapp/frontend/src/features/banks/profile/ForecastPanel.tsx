"use client";

import { Box, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { SeriesLineChart } from "@/components/charts/SeriesLineChart";
import { ErrorState, LoadingBlock, PendingResult } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import { marketRepository } from "@/repositories/market.repository";
import type { ForecastBlock, IndicatorSeries } from "@/types/api";
import { formatPercent, formatQuarter } from "@/utils/format";

/** Số quý lịch sử hiển thị trước phần dự báo. */
const HISTORY_QUARTERS = 8;

export function ForecastPanel({ ticker }: { ticker: string }) {
  const forecast = useQuery({ queryKey: queryKeys.bankForecasts(ticker), queryFn: () => bankRepository.forecasts(ticker) });
  const history = useQuery({ queryKey: queryKeys.bankIndicators(ticker), queryFn: () => bankRepository.indicators(ticker) });
  const catalog = useQuery({ queryKey: queryKeys.indicators, queryFn: marketRepository.indicators, staleTime: Infinity });

  if (forecast.isError) return <ErrorState error={forecast.error} onRetry={() => forecast.refetch()} />;
  if (!forecast.data) return <LoadingBlock height={240} />;

  if (forecast.data.status === "NOT_AVAILABLE") {
    return (
      <PendingResult
        title="Chưa có kết quả dự báo"
        description="Phần này sẽ hiển thị dự báo 1–4 quý tới cho sáu chỉ tiêu (NIM, chi phí vốn, nợ xấu, CASA, LDR, ROE), kèm vùng sai số và đường so sánh với cách dự báo đơn giản (giữ nguyên hoặc theo mùa vụ). Kết quả hiện ở đây khi mô hình dự báo hoàn tất và được huấn luyện lại mỗi quý."
      />
    );
  }

  return (
    <Grid container spacing={2}>
      {forecast.data.indicators.map((item) => (
        <Grid key={item.indicatorCode} size={{ xs: 12, md: 6 }}>
          <ForecastCard
            item={item}
            origin={forecast.data.originPeriod}
            name={catalog.data?.find((c) => c.code === item.indicatorCode)?.name ?? item.indicatorCode}
            history={history.data?.indicators.find((s) => s.indicator.code === item.indicatorCode)}
          />
        </Grid>
      ))}
    </Grid>
  );
}

function ForecastCard({
  item,
  origin,
  name,
  history,
}: {
  item: ForecastBlock["indicators"][number];
  origin: string | null;
  name: string;
  history: IndicatorSeries | undefined;
}) {
  const past = (history?.points ?? []).filter((p) => p.value !== null).slice(-HISTORY_QUARTERS);
  const periods = [...past.map((p) => p.period), ...item.points.map((p) => p.targetPeriod)];
  const actual = [...past.map((p) => p.value), ...item.points.map(() => null)];
  // Đường dự báo nối từ quý thật cuối cùng để liền mạch.
  const predicted = [
    ...past.map((p, i) => (i === past.length - 1 ? p.value : null)),
    ...item.points.map((p) => p.value),
  ];
  const naive = [...past.map(() => null), ...item.points.map((p) => p.naiveValue)];

  return (
    <Card sx={{ p: 2 }}>
      <Typography variant="subtitle1" component="h3">
        {name}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Dự báo từ {formatQuarter(origin)}
        {item.method ? ` · mô hình ${item.method}` : ""}
      </Typography>
      <Box sx={{ mx: -1 }}>
        <SeriesLineChart
          height={220}
          categories={periods}
          formatCategory={(p) => p.replace(/^20(\d{2})-Q(\d)$/, "Q$2/$1")}
          series={[
            { id: "actual", label: "Số thật", data: actual, colorIndex: 0 },
            { id: "forecast", label: "Dự báo", data: predicted, colorIndex: 1, dashed: true },
            { id: "naive", label: "Cách đơn giản", data: naive, kind: "reference" },
          ]}
          formatValue={(v) => formatPercent(v)}
          ariaLabel={`Dự báo ${name} 1–4 quý tới`}
        />
      </Box>
      <Table size="small" aria-label={`Khoảng dự báo ${name}`}>
        <TableHead>
          <TableRow>
            <TableCell>Quý</TableCell>
            <TableCell align="right">Dự báo</TableCell>
            <TableCell align="right">Khoảng</TableCell>
            <TableCell align="right">Cách đơn giản</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {item.points.map((p) => (
            <TableRow key={p.targetPeriod}>
              <TableCell>{formatQuarter(p.targetPeriod)}</TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>
                {formatPercent(p.value)}
              </TableCell>
              <TableCell align="right">
                {p.lower !== null && p.upper !== null ? `${formatPercent(p.lower)} – ${formatPercent(p.upper)}` : "—"}
              </TableCell>
              <TableCell align="right">{formatPercent(p.naiveValue)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
