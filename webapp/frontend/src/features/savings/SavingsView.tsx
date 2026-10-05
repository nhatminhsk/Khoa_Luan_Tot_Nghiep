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
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { RankingSection } from "@/components/domain/RankingSection";
import { SaveNeedButton } from "@/features/needs/SaveNeedButton";
import { useInflation } from "@/hooks/use-inflation";
import { advisorRepository } from "@/repositories/advisor.repository";
import type { SavingsAdviceRequest } from "@/types/api";
import { formatMonth, formatPercent, formatVnd, formatVndCompact } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";
import { realRate } from "@/utils/real-rate";
import { DEFAULT_WEIGHTS, parseSavingsParams, toSavingsQuery } from "./savings-params";
import { SavingsForm } from "./SavingsForm";
import { SavingsOffersTable } from "./SavingsOffersTable";

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

  const submit = (values: SavingsAdviceRequest) =>
    router.replace(`${pathname}?${toSavingsQuery(values)}`, { scroll: false });

  const inflation = useInflation().data;
  const cpi = inflation?.latest ?? null;

  const best = advice.data?.offers[0];
  const weights = request.weights ?? DEFAULT_WEIGHTS;

  return (
    <>
      <PageHeader
        title="Chọn ngân hàng gửi tiết kiệm"
        description="Nhập số tiền, kỳ hạn, kênh gửi và điều bạn coi trọng. Hệ thống tính tiền lãi ước tính theo lãi suất niêm yết hôm nay."
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
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ p: 2.5, position: { md: "sticky" }, top: { md: 88 } }}>
            {/* key: khi URL đổi (mở từ nhu cầu đã lưu) thì form nhận giá trị mới */}
            <SavingsForm key={toSavingsQuery(request)} initial={request} onSubmit={submit} submitting={advice.isFetching} />
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          <Stack spacing={2.5}>
            {advice.isError ? (
              <ErrorState error={advice.error} onRetry={() => advice.refetch()} />
            ) : !advice.data ? (
              <LoadingBlock height={420} />
            ) : (
              <Box sx={{ opacity: advice.isPlaceholderData ? 0.55 : 1, transition: "opacity 150ms" }}>
                <Stack spacing={2.5}>
                  {best ? (
                    <Grid container spacing={2}>
                      <Grid size={{ xs: 12, sm: 4 }}>
                        <StatTile
                          icon={<IconTrophy size={18} aria-hidden />}
                          tone="primary"
                          label="Lãi suất cao nhất"
                          value={formatPercent(best.ratePercent)}
                          hint={`${best.shortName} · ${advice.data.termMonths} tháng, ${CHANNEL_LABEL[advice.data.channel].toLowerCase()}`}
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
                          label="Lãi suất thực"
                          value={<RealRateValue value={cpi ? realRate(best.ratePercent, cpi.yoyPercent) : null} variant="inherit" />}
                          hint={
                            cpi ? (
                              <>
                                Của mức cao nhất · lạm phát {formatMonth(cpi.month)}: {formatPercent(cpi.yoyPercent)}
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

                  <SectionCard title="Xếp hạng tổng hợp" subtitle="Cân nhắc cả lãi suất, độ an toàn và trải nghiệm ứng dụng.">
                    <RankingSection purpose="SAVINGS" block={advice.data.ranking} />
                  </SectionCard>

                  <SectionCard
                    title={`Lãi suất hôm nay · ${advice.data.termMonths} tháng · ${CHANNEL_LABEL[advice.data.channel].toLowerCase()}`}
                    subtitle={`Sắp theo lãi suất (một tiêu chí). Tiền lãi tính cho ${formatVnd(advice.data.amount)}, trả cuối kỳ.`}
                    flush
                  >
                    {advice.data.offers.length === 0 ? (
                      <EmptyState
                        title="Không ngân hàng nào niêm yết kỳ hạn này"
                        description="Thử kỳ hạn khác hoặc đổi kênh gửi."
                      />
                    ) : (
                      <SavingsOffersTable offers={advice.data.offers} inflation={cpi?.yoyPercent} />
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
