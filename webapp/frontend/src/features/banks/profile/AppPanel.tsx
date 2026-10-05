"use client";

import { Grid, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { IconDeviceMobile, IconStarFilled } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { SeriesLineChart } from "@/components/charts/SeriesLineChart";
import { SectionCard } from "@/components/common/SectionCard";
import { StatTile } from "@/components/common/StatTile";
import { EmptyState, ErrorState, LoadingBlock, PendingResult } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import { formatDate, formatNumber, formatQuarter } from "@/utils/format";
import { ASPECT_LABEL, STORE_LABEL } from "@/utils/labels";

export function AppPanel({ ticker }: { ticker: string }) {
  const query = useQuery({ queryKey: queryKeys.bankApp(ticker), queryFn: () => bankRepository.app(ticker) });

  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (!query.data) return <LoadingBlock height={420} />;
  const { stores, monthly, aspects } = query.data;
  const latestAspectPeriod = aspects.items.at(-1)?.period;

  return (
    <Grid container spacing={2.5}>
      {stores.length === 0 ? (
        <Grid size={12}>
          <EmptyState title="Chưa có dữ liệu kho ứng dụng" />
        </Grid>
      ) : (
        stores.map((store) => (
          <Grid key={store.store} size={{ xs: 12, sm: 6 }}>
            <StatTile
              icon={<IconDeviceMobile size={18} aria-hidden />}
              label={`${STORE_LABEL[store.store]}${store.appName ? ` · ${store.appName}` : ""}`}
              value={
                <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }} component="span">
                  <span>{formatNumber(store.score, 2)}</span>
                  <IconStarFilled size={20} aria-label="sao" />
                </Stack>
              }
              hint={`${formatNumber(store.ratings, 0)} lượt chấm · chụp ngày ${formatDate(store.snapshotDate)}`}
            />
          </Grid>
        ))
      )}

      <Grid size={12}>
        <SectionCard
          title="Điểm đánh giá trung bình theo tháng (Google Play)"
          subtitle="Chỉ tính review có nội dung nên lệch về hai cực (1 và 5 sao); tháng quá ít review hoặc bị spam đánh giá được bỏ trống. Hai lần giảm chung của cả ngành: 7/2024 (xác thực sinh trắc học, QĐ 2345) và 1/2025 (TT 17/2024)."
        >
          {monthly.length === 0 ? (
            <EmptyState title="Chưa có review theo tháng" />
          ) : (
            <SeriesLineChart
              height={260}
              categories={monthly.map((m) => m.month)}
              formatCategory={(m) => m.replace(/^20(\d{2})-(\d{2})$/, "$2/$1")}
              series={[
                {
                  id: "score",
                  label: "Điểm trung bình",
                  data: monthly.map((m) => (m.usable ? m.meanScore : null)),
                  colorIndex: 0,
                },
              ]}
              formatValue={(v) => `${formatNumber(v, 2)} sao`}
              ariaLabel="Điểm đánh giá ứng dụng trung bình theo tháng"
            />
          )}
        </SectionCard>
      </Grid>

      <Grid size={12}>
        <SectionCard title="Đánh giá theo khía cạnh" subtitle="Tách review thành 8 khía cạnh bằng mô hình ngôn ngữ (NLP).">
          {aspects.status === "NOT_AVAILABLE" ? (
            <PendingResult
              title="Chưa có kết quả phân tích khía cạnh"
              description="Phần này sẽ cho biết người dùng khen/chê ứng dụng ở đâu: lỗi giao dịch, đăng nhập/OTP, cập nhật và giao diện, tốc độ, chăm sóc khách hàng, thẻ/ATM, phí, tiền gửi/tiết kiệm. Kết quả hiện ở đây khi mô hình NLP hoàn tất."
            />
          ) : (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Quý {formatQuarter(latestAspectPeriod)}; điểm từ −1 (rất tiêu cực) tới +1 (rất tích cực).
              </Typography>
              <Table size="small" aria-label="Điểm theo khía cạnh">
                <TableHead>
                  <TableRow>
                    <TableCell>Khía cạnh</TableCell>
                    <TableCell align="right">Điểm</TableCell>
                    <TableCell align="right">Số review</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {aspects.items
                    .filter((a) => a.period === latestAspectPeriod)
                    .map((a) => (
                      <TableRow key={a.aspect}>
                        <TableCell>{ASPECT_LABEL[a.aspect] ?? a.aspect}</TableCell>
                        <TableCell align="right">{formatNumber(a.score, 2)}</TableCell>
                        <TableCell align="right">{formatNumber(a.reviewCount, 0)}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </>
          )}
        </SectionCard>
      </Grid>
    </Grid>
  );
}
