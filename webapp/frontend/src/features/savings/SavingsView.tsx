"use client";

import { Box, Card, Grid, Link as MuiLink, Stack } from "@mui/material";
import { IconCoins, IconScale, IconTrophy } from "@tabler/icons-react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { Disclaimer } from "@/components/common/Disclaimer";
import { PageHeader } from "@/components/common/PageHeader";
import { RealRateValue } from "@/components/common/RealRateValue";
import { SectionCard } from "@/components/common/SectionCard";
import { StatTile } from "@/components/common/StatTile";
import { EmptyState, ErrorState, LoadingBlock, UpdatingNote } from "@/components/common/States";
import { RankingSection } from "@/components/domain/RankingSection";
import { SaveNeedButton } from "@/features/needs/SaveNeedButton";
import { useInflation } from "@/hooks/use-inflation";
import { useScrollToResults } from "@/hooks/use-scroll-to-results";
import { queryKeys } from "@/lib/query/keys";
import { advisorRepository } from "@/repositories/advisor.repository";
import { marketRepository } from "@/repositories/market.repository";
import type { SavingsAdviceRequest } from "@/types/api";
import { formatMonth, formatPercent, formatVnd, formatVndCompact } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";
import { rateDayText } from "@/utils/today";
import { realRate } from "@/utils/real-rate";
import { DEFAULT_WEIGHTS, parseSavingsParams, toSavingsQuery } from "./savings-params";
import { SavingsForm } from "./SavingsForm";
import { SavingsOffersTable, type OfferHealth } from "./SavingsOffersTable";

/**
 * Trang chọn ngân hàng gửi tiết kiệm: form tiêu chí → gọi repository → bảng kết quả.
 * Tiêu chí nằm trên URL (chép link là mở lại đúng kết quả); dữ liệu do TanStack Query quản lý.
 */
export function SavingsView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const request = useMemo(() => parseSavingsParams(new URLSearchParams(searchParams.toString())), [searchParams]);

  const advice = useQuery({
    queryKey: ["advisor", "savings", request],
    queryFn: () => advisorRepository.savings(request),
    placeholderData: keepPreviousData,
  });

  const [resultsRef, expectResults] = useScrollToResults(
    searchParams.toString(),
    advice.isSuccess && !advice.isPlaceholderData && !advice.isFetching,
    advice.isError,
  );
  const submit = (values: SavingsAdviceRequest) => {
    const query = toSavingsQuery(values);
    expectResults(query);
    router.replace(`${pathname}?${query}`, { scroll: false });
  };

  const inflation = useInflation().data;
  const cpi = inflation?.latest ?? null;
  // Nợ xấu, CAR cạnh lãi suất: lỗi hay đang tải thì bảng vẫn hiện, chỉ thiếu hai cột này.
  const snapshot = useQuery({ queryKey: queryKeys.indicatorSnapshot, queryFn: marketRepository.indicatorSnapshot });
  const health = useMemo<OfferHealth | null>(
    () =>
      snapshot.data
        ? {
            latestPeriod: snapshot.data.latestPeriod,
            byTicker: new Map(snapshot.data.rows.map((r) => [r.ticker, { npl: r.values.npl, car: r.values.car }])),
          }
        : null,
    [snapshot.data],
  );

  const best = advice.data?.offers[0];
  const weights = request.weights ?? DEFAULT_WEIGHTS;

  return (
    <>
      <PageHeader
        title="Chọn ngân hàng gửi tiết kiệm"
        description="Nhập số tiền, kỳ hạn và kênh gửi. Hệ thống tính tiền lãi theo lãi suất niêm yết và xếp hạng ngân hàng theo cả lãi suất lẫn độ an toàn; phần tiền vượt hạn mức bảo hiểm tiền gửi càng lớn thì độ an toàn càng nặng."
        actions={
          <SaveNeedButton
            defaultLabel={`Gửi ${formatVndCompact(request.amount)}, ${request.termMonths} tháng`}
            need={{
              purpose: "SAVINGS",
              amount: request.amount,
              termMonths: request.termMonths,
              channel: request.channel,
              loanPurpose: null,
              repayment: null,
              weightRate: weights.rate,
              weightSafety: weights.safety,
              weightApp: weights.app,
            }}
          />
        }
      />

      <Grid container spacing={2.5}>
        {/* Thanh lọc ngang trên cùng, kết quả rộng cả trang (kiểu dashboard). */}
        <Grid size={12}>
          <Card sx={{ p: { xs: 2, sm: 2.5 } }}>
            {/* key: khi URL đổi (mở từ nhu cầu đã lưu) thì form nhận giá trị mới */}
            <SavingsForm
              key={toSavingsQuery(request)}
              initial={request}
              onSubmit={submit}
              submitting={advice.isFetching}
            />
          </Card>
        </Grid>

        <Grid size={12}>
          <Stack
            spacing={2.5}
            ref={resultsRef}
            tabIndex={-1}
            aria-label="Kết quả"
            sx={{ scrollMarginTop: 80, "&:focus": { outline: "none" } }}
          >
            {advice.isError ? (
              <ErrorState error={advice.error} onRetry={() => advice.refetch()} />
            ) : !advice.data ? (
              <LoadingBlock height={420} />
            ) : (
              <Box aria-busy={advice.isPlaceholderData} sx={{ opacity: advice.isPlaceholderData ? 0.55 : 1, transition: "opacity 150ms" }}>
                <Stack spacing={2.5}>
                  {advice.isPlaceholderData && <UpdatingNote />}
                  {best ? (
                    <Grid container spacing={2}>
                      <Grid size={{ xs: 12, sm: 4 }}>
                        <StatTile
                          icon={<IconTrophy size={18} aria-hidden />}
                          tone="primary"
                          label="Lãi suất cao nhất"
                          value={formatPercent(best.ratePercent)}
                          hint={`${best.shortName} · ${advice.data.termMonths} tháng, ${CHANNEL_LABEL[advice.data.channel].toLowerCase()}${
                            best.tierLabel ? ` · bậc ${best.tierLabel.toLowerCase()}` : ""
                          }`}
                        />
                      </Grid>
                      <Grid size={{ xs: 12, sm: 4 }}>
                        <StatTile
                          icon={<IconCoins size={18} aria-hidden />}
                          tone="success"
                          label="Tiền lãi ước tính"
                          value={formatVnd(best.interest)}
                          hint={`Nhận ${formatVnd(best.maturityAmount)} khi đáo hạn`}
                        />
                      </Grid>
                      <Grid size={{ xs: 12, sm: 4 }}>
                        <StatTile
                          icon={<IconScale size={18} aria-hidden />}
                          tone="info"
                          label="Lãi thực tham chiếu"
                          value={<RealRateValue value={cpi ? realRate(best.ratePercent, cpi.yoyPercent) : null} variant="inherit" />}
                          hint={
                            cpi ? (
                              <>
                                Mức cao nhất trừ CPI {formatMonth(cpi.month)} ({formatPercent(cpi.yoyPercent)}); không dự báo sức mua
                                {inflation?.sourceUrl && (
                                  <>
                                    {" "}
                                    (
                                    <MuiLink href={inflation.sourceUrl} target="_blank" rel="noopener noreferrer" color="inherit">
                                      TCTK
                                    </MuiLink>
                                    )
                                  </>
                                )}
                              </>
                            ) : (
                              "Chưa có số lạm phát"
                            )
                          }
                        />
                      </Grid>
                    </Grid>
                  ) : null}

                  {/* Chưa có xếp hạng: chỉ một dòng thông báo ngay trên bảng, không chiếm cả thẻ trước kết quả thật. */}
                  {advice.data.ranking.status === "NOT_AVAILABLE" ? (
                    <RankingSection purpose="SAVINGS" block={advice.data.ranking} />
                  ) : (
                    <SectionCard
                      title="Xếp hạng tổng hợp: lãi suất và độ an toàn"
                      subtitle="Bốn phương pháp đa tiêu chí, 10.000 lần rút trọng số trên số liệu công bố mới nhất; không dùng số dự báo."
                    >
                      <RankingSection purpose="SAVINGS" block={advice.data.ranking} />
                    </SectionCard>
                  )}

                  <SectionCard
                    title={`Lãi suất ${rateDayText(advice.data.rateDate)} · ${advice.data.termMonths} tháng · ${CHANNEL_LABEL[advice.data.channel].toLowerCase()}`}
                    subtitle={`Sắp theo lãi suất (một tiêu chí), theo bậc số tiền với ngân hàng có chia bậc. Tiền lãi tính cho ${formatVnd(advice.data.amount)}, trả cuối kỳ.`}
                    flush
                  >
                    {advice.data.offers.length === 0 ? (
                      <EmptyState
                        title="Không ngân hàng nào niêm yết kỳ hạn này"
                        description="Thử kỳ hạn khác hoặc đổi kênh gửi."
                      />
                    ) : (
                      <SavingsOffersTable offers={advice.data.offers} inflation={cpi?.yoyPercent} health={health} />
                    )}
                  </SectionCard>
                </Stack>
              </Box>
            )}
          </Stack>
        </Grid>
      </Grid>

      <Disclaimer>
        Tiền lãi là ước tính theo công thức lãi đơn trả cuối kỳ trên lãi suất niêm yết; ngân hàng tính theo số ngày thực tế và có
        thể áp mức khác theo số tiền gửi. Lãi suất thực tế do ngân hàng quyết định khi giao dịch. Lãi thực = lãi suất/năm trừ lạm
        phát tháng gần nhất so với cùng kỳ; lạm phát trong kỳ gửi có thể khác.
      </Disclaimer>
    </>
  );
}
