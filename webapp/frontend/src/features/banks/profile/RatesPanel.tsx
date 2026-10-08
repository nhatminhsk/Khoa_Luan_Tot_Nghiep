"use client";

import {
  Box,
  Grid,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { SeriesLineChart } from "@/components/charts/SeriesLineChart";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { RateDelta } from "@/components/common/RateDelta";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { LendingOriginTag } from "@/components/domain/LendingOriginTag";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import { formatDate, formatMonth, formatPercent, formatTerm } from "@/utils/format";
import { DAILY_PRESETS, type DailyPreset, indexesInDailyPreset, pick } from "@/utils/period-presets";

export function RatesPanel({ ticker }: { ticker: string }) {
  const rates = useQuery({ queryKey: queryKeys.bankRates(ticker), queryFn: () => bankRepository.rates(ticker) });
  const lending = useQuery({ queryKey: queryKeys.bankLending(ticker), queryFn: () => bankRepository.lendingRates(ticker) });
  const [term, setTerm] = useState(12);
  const [period, setPeriod] = useState<DailyPreset>("1Y");

  const history = useMemo(() => {
    const points = (rates.data?.history ?? []).filter((p) => p.termMonths === term);
    const allDates = [...new Set(points.map((p) => p.date))].sort();
    const dates = pick(allDates, indexesInDailyPreset(allDates, period));
    const byKey = new Map(points.map((p) => [`${p.date}|${p.channel}`, p.rate]));
    return {
      dates,
      online: dates.map((d) => byKey.get(`${d}|ONLINE`) ?? null),
      counter: dates.map((d) => byKey.get(`${d}|COUNTER`) ?? null),
    };
  }, [rates.data, term, period]);

  if (rates.isError) return <ErrorState error={rates.error} onRetry={() => rates.refetch()} />;
  if (!rates.data) return <LoadingBlock height={420} />;

  const terms = rates.data.current.map((c) => c.termMonths);

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, md: 5 }}>
        <SectionCard title="Lãi suất tiết kiệm niêm yết" subtitle={`Ngày ${formatDate(rates.data.rateDate)}, so với ngày có số liệu liền trước.`} flush>
          {rates.data.current.length === 0 ? (
            <EmptyState title="Chưa có số liệu lãi suất" />
          ) : (
            <TableContainer>
              <Table size="small" aria-label="Lãi suất theo kỳ hạn và kênh">
                <TableHead>
                  <TableRow>
                    <TableCell>Kỳ hạn</TableCell>
                    <TableCell align="right">Trực tuyến</TableCell>
                    <TableCell align="right">Tại quầy</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rates.data.current.map((row) => (
                    <TableRow key={row.termMonths} hover selected={row.termMonths === term}>
                      <TableCell sx={{ fontWeight: 600 }}>{formatTerm(row.termMonths)}</TableCell>
                      <TableCell align="right">
                        {formatPercent(row.online)} <RateDelta value={row.onlineChange} />
                      </TableCell>
                      <TableCell align="right">
                        {formatPercent(row.counter)} <RateDelta value={row.counterChange} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </SectionCard>
      </Grid>

      <Grid size={{ xs: 12, md: 7 }}>
        <SectionCard
          title="Lịch sử lãi suất niêm yết"
          subtitle="Trước 2026 số liệu lấy theo các ngày lưu trữ nên thưa hơn."
          action={
            <TextField select size="small" label="Kỳ hạn" value={term} onChange={(e) => setTerm(Number(e.target.value))} sx={{ minWidth: 130 }}>
              {terms.map((t) => (
                <MenuItem key={t} value={t}>
                  {formatTerm(t)}
                </MenuItem>
              ))}
            </TextField>
          }
        >
          <Box sx={{ mb: 1.5 }}>
            <PeriodToggle value={period} options={DAILY_PRESETS} onChange={setPeriod} />
          </Box>
          {history.dates.length === 0 ? (
            <EmptyState title="Chưa có lịch sử cho kỳ hạn này" />
          ) : (
            <SeriesLineChart
              height={300}
              dates={history.dates.map((d) => new Date(d))}
              formatDate={(d) =>
                d.toLocaleDateString("vi-VN", period === "1M" || period === "3M" ? { day: "2-digit", month: "2-digit" } : { month: "2-digit", year: "numeric" })
              }
              series={[
                { id: "online", label: "Trực tuyến", data: history.online, colorIndex: 0 },
                { id: "counter", label: "Tại quầy", data: history.counter, colorIndex: 1 },
              ]}
              formatValue={(v) => formatPercent(v)}
              ariaLabel={`Lịch sử lãi suất ${formatTerm(term)} trực tuyến và tại quầy`}
            />
          )}
        </SectionCard>
      </Grid>

      <Grid size={12}>
        <SectionCard
          title="Lãi suất cho vay và huy động bình quân"
          subtitle="Ngân hàng tự công bố trên web theo tháng (Chỉ thị 01/CT-NHNN); tháng chưa lấy được thì dùng số báo VietnamNet tổng hợp. Là mức bình quân của khách hàng cá nhân hoặc toàn danh mục, xem cột Loại số."
          flush
        >
          {lending.isLoading ? (
            <Box sx={{ p: 2.5 }}>
              <LoadingBlock height={120} />
            </Box>
          ) : !lending.data || lending.data.length === 0 ? (
            <EmptyState title="Ngân hàng chưa công bố số liệu này" />
          ) : (
            <TableContainer>
              <Table
                size="small"
                aria-label="Lãi suất cho vay và huy động bình quân theo tháng"
                // Điện thoại: tiêu đề "Cho vay bình quân" xuống hai dòng để 4 cột vừa màn hình.
                sx={{ "& th": { whiteSpace: { xs: "normal", sm: "nowrap" } } }}
              >
                <TableHead>
                  <TableRow>
                    <TableCell>Tháng</TableCell>
                    <TableCell align="right">Cho vay bình quân</TableCell>
                    <TableCell align="right">Huy động bình quân</TableCell>
                    <TableCell align="right">Chênh lệch</TableCell>
                    <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>Loại số</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {[...lending.data].reverse().map((row) => (
                    <TableRow key={row.month} hover>
                      <TableCell>{formatMonth(row.month)}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>
                        {formatPercent(row.lendingAvgPercent)}
                      </TableCell>
                      <TableCell align="right">{formatPercent(row.depositAvgPercent)}</TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" color="text.secondary">
                          {row.depositAvgPercent === null
                            ? "—"
                            : `${(row.lendingAvgPercent - row.depositAvgPercent).toLocaleString("vi-VN", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })} điểm %`}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>
                        <LendingOriginTag origin={row} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </SectionCard>
      </Grid>
    </Grid>
  );
}
