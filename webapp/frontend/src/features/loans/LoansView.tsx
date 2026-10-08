"use client";

import {
  Box,
  Card,
  Chip,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { IconAlertTriangle, IconCalendarDollar, IconCoins, IconPercentage } from "@tabler/icons-react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { BankLabel } from "@/components/common/BankLabel";
import { Disclaimer } from "@/components/common/Disclaimer";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { StatTile } from "@/components/common/StatTile";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { LendingOriginTag, lendingOriginLabel } from "@/components/domain/LendingOriginTag";
import { ProgramList } from "@/components/domain/ProgramList";
import { RankingSection } from "@/components/domain/RankingSection";
import { SaveNeedButton } from "@/features/needs/SaveNeedButton";
import { advisorRepository } from "@/repositories/advisor.repository";
import type { LoanAdvice, LoanAdviceRequest } from "@/types/api";
import { formatMonth, formatPercent, formatTerm, formatVnd, formatVndCompact } from "@/utils/format";
import { LOAN_PURPOSE_LABEL, REPAYMENT_LABEL } from "@/utils/labels";
import { LoanForm } from "./LoanForm";
import { parseLoanParams, toLoanQuery } from "./loan-params";

/** Số lãi cũ hơn mức này (tháng) thì gắn cảnh báo. */
const STALE_MONTHS = 3;

export function LoansView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const request = useMemo(() => parseLoanParams(new URLSearchParams(searchParams.toString())), [searchParams]);

  const advice = useQuery({
    queryKey: ["advisor", "loans", request],
    queryFn: () => advisorRepository.loans(request),
    placeholderData: keepPreviousData,
  });

  const submit = (values: LoanAdviceRequest) => router.replace(`${pathname}?${toLoanQuery(values)}`, { scroll: false });

  return (
    <>
      <PageHeader
        title="Chọn ngân hàng vay"
        description="Nhập mục đích, số tiền và thời hạn. Hệ thống ước tính tiền trả theo lãi suất cho vay bình quân mỗi ngân hàng công bố, và gợi ý chương trình ưu đãi phù hợp."
        actions={
          <SaveNeedButton
            defaultLabel={`Vay ${formatVndCompact(request.amount)}, ${formatTerm(request.termMonths)}`}
            need={{
              purpose: "LOAN",
              amount: request.amount,
              termMonths: request.termMonths,
              channel: null,
              loanPurpose: request.purpose,
              repayment: request.repayment,
              weightRate: null,
              weightSafety: null,
              weightApp: null,
            }}
          />
        }
      />

      <Grid container spacing={2.5}>
        {/* Chỉ chia cột form/kết quả từ lg: ở iPad (≤ 1199px, có thêm menu trái từ md) cột kết quả 8/12 còn ~470px,
            thẻ KPI bị cắt số và bảng phải cuộn ngang. Dưới lg form nằm trên, trường xếp nhiều cột. */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Card sx={{ p: { xs: 2, sm: 2.5 }, position: { lg: "sticky" }, top: { lg: 88 } }}>
            <LoanForm key={toLoanQuery(request)} initial={request} onSubmit={submit} submitting={advice.isFetching} />
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 8 }}>
          {advice.isError ? (
            <ErrorState error={advice.error} onRetry={() => advice.refetch()} />
          ) : !advice.data ? (
            <LoadingBlock height={420} />
          ) : (
            <Box sx={{ opacity: advice.isPlaceholderData ? 0.55 : 1, transition: "opacity 150ms" }}>
              <LoanResults data={advice.data} />
            </Box>
          )}
        </Grid>
      </Grid>

      <Disclaimer>
        Lãi suất cho vay bình quân là mức bình quân trên toàn bộ khách hàng cá nhân (hoặc toàn bộ danh mục cho vay) mà ngân
        hàng công bố, không phải lãi suất bạn sẽ được duyệt. Tiền trả hằng tháng chỉ để tham khảo; hệ thống không đánh giá khả
        năng vay của từng người.
      </Disclaimer>
    </>
  );
}

function LoanResults({ data }: { data: LoanAdvice }) {
  const cheapest = data.offers[0];
  const programNames = new Map(data.programs.map((p) => [p.code, p.name]));
  const declining = data.repayment === "DECLINING_BALANCE";

  return (
    <Stack spacing={2.5}>
      {cheapest && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <StatTile
              icon={<IconPercentage size={18} aria-hidden />}
              tone="primary"
              label="Lãi vay thấp nhất"
              value={formatPercent(cheapest.lendingAvgPercent)}
              hint={`${cheapest.shortName} · tháng ${formatMonth(cheapest.month)}${
                cheapest.segment || cheapest.source ? ` · ${lendingOriginLabel(cheapest).toLowerCase()}` : ""
              }`}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <StatTile
              icon={<IconCalendarDollar size={18} aria-hidden />}
              tone="info"
              label={declining ? "Trả tháng đầu" : "Trả mỗi tháng"}
              value={formatVnd(cheapest.firstPayment)}
              hint={declining ? `Giảm dần còn ${formatVnd(cheapest.lastPayment)} ở tháng cuối` : REPAYMENT_LABEL[data.repayment]}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <StatTile
              icon={<IconCoins size={18} aria-hidden />}
              tone="warning"
              label="Tổng tiền lãi cả kỳ"
              value={formatVndCompact(cheapest.totalInterest)}
              hint={`${LOAN_PURPOSE_LABEL[data.purpose]} · ${formatVndCompact(data.amount)} · ${formatTerm(data.termMonths)}`}
            />
          </Grid>
        </Grid>
      )}

      <SectionCard title="Xếp hạng tổng hợp" subtitle="Cân nhắc lãi suất cho vay, chương trình ưu đãi và sức khỏe tài chính.">
        <RankingSection purpose="LOAN" block={data.ranking} />
      </SectionCard>

      {data.programs.length > 0 && (
        <SectionCard
          title="Chương trình tín dụng ưu đãi liên quan"
          subtitle="Điều kiện vay do ngân hàng và văn bản của chương trình quy định; hãy hỏi ngân hàng trước khi quyết định."
        >
          <ProgramList programs={data.programs} />
        </SectionCard>
      )}

      <SectionCard
        title="Ước tính tiền trả theo lãi suất cho vay bình quân"
        subtitle={`Sắp theo lãi suất tăng dần. Mỗi ngân hàng một số: ưu tiên số khách hàng cá nhân ngân hàng công bố, không có thì số chung, cuối cùng là số báo tổng hợp; các số này không hoàn toàn cùng loại (rê chuột lên nhãn để xem). Tháng mới nhất trong dữ liệu: ${formatMonth(data.latestMonth)}.`}
        flush
      >
        {data.offers.length === 0 ? (
          <EmptyState title="Chưa có số liệu lãi suất cho vay" />
        ) : (
          <TableContainer>
            <Table size="small" aria-label="Ước tính tiền trả theo ngân hàng">
              <TableHead>
                <TableRow>
                  <TableCell>Ngân hàng</TableCell>
                  <TableCell align="right">Lãi bình quân</TableCell>
                  <TableCell align="right">{declining ? "Trả tháng đầu" : "Trả mỗi tháng"}</TableCell>
                  {declining && (
                    <TableCell align="right" sx={{ display: { xs: "none", md: "table-cell" } }}>
                      Trả tháng cuối
                    </TableCell>
                  )}
                  <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                    Tổng tiền lãi
                  </TableCell>
                  {data.programs.length > 0 && <TableCell>Chương trình</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {data.offers.map((offer) => (
                  <TableRow key={offer.ticker} hover>
                    <TableCell>
                      <BankLabel ticker={offer.ticker} shortName={offer.shortName} />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {formatPercent(offer.lendingAvgPercent)}
                      </Typography>
                      <Stack
                        direction="row"
                        spacing={0.5}
                        useFlexGap
                        sx={{ justifyContent: "flex-end", alignItems: "center", flexWrap: "wrap" }}
                      >
                        <LendingOriginTag origin={offer} />
                        {offer.monthsBehind >= STALE_MONTHS && (
                          <Tooltip title={`Số cũ hơn ${offer.monthsBehind} tháng so với tháng mới nhất`}>
                            <Box component="span" sx={{ color: "warning.main", display: "inline-flex" }}>
                              <IconAlertTriangle size={14} aria-label="Số liệu cũ" />
                            </Box>
                          </Tooltip>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          {formatMonth(offer.month)}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {formatVnd(offer.firstPayment)}
                    </TableCell>
                    {declining && (
                      <TableCell align="right" sx={{ display: { xs: "none", md: "table-cell" } }}>
                        {formatVnd(offer.lastPayment)}
                      </TableCell>
                    )}
                    <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                      {formatVnd(offer.totalInterest)}
                    </TableCell>
                    {data.programs.length > 0 && (
                      <TableCell>
                        <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>
                          {offer.programCodes.length === 0 ? (
                            <Typography variant="caption" color="text.secondary">
                              —
                            </Typography>
                          ) : (
                            offer.programCodes.map((code) => (
                              <Tooltip key={code} title={programNames.get(code) ?? code}>
                                <Chip size="small" label={code} variant="outlined" />
                              </Tooltip>
                            ))
                          )}
                        </Stack>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </SectionCard>
    </Stack>
  );
}
