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
import { EmptyState, ErrorState, LoadingBlock, UpdatingNote } from "@/components/common/States";
import { LendingOriginTag, lendingOriginLabel } from "@/components/domain/LendingOriginTag";
import { ProgramList } from "@/components/domain/ProgramList";
import { RankingSection } from "@/components/domain/RankingSection";
import { SaveNeedButton } from "@/features/needs/SaveNeedButton";
import { useScrollToResults } from "@/hooks/use-scroll-to-results";
import { advisorRepository } from "@/repositories/advisor.repository";
import type { LoanAdvice, LoanAdviceRequest } from "@/types/api";
import { formatMonth, formatPercent, formatTerm, formatVnd, formatVndCompact } from "@/utils/format";
import { LOAN_PURPOSE_LABEL, REPAYMENT_LABEL } from "@/utils/labels";
import { STALE_MONTHS, isComparableLending } from "@/utils/lending";
import { LoanForm } from "./LoanForm";
import { parseLoanParams, toLoanQuery } from "./loan-params";


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

  const [resultsRef, expectResults] = useScrollToResults(
    searchParams.toString(),
    advice.isSuccess && !advice.isPlaceholderData && !advice.isFetching,
    advice.isError,
  );
  const submit = (values: LoanAdviceRequest) => {
    const query = toLoanQuery(values);
    expectResults(query);
    router.replace(`${pathname}?${query}`, { scroll: false });
  };

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
        {/* Thanh lọc ngang trên cùng, kết quả rộng cả trang (cùng bố cục trang Gửi tiết kiệm). */}
        <Grid size={12}>
          <Card sx={{ p: { xs: 2, sm: 2.5 } }}>
            <LoanForm key={toLoanQuery(request)} initial={request} onSubmit={submit} submitting={advice.isFetching} />
          </Card>
        </Grid>
        <Grid
          size={12}
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
              {advice.isPlaceholderData && <UpdatingNote sx={{ mb: 1.5 }} />}
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
  // Thẻ số đặt cạnh nhau phải so được với nhau: ưu tiên số KH cá nhân do ngân hàng tự công bố và không cũ (cùng cách thẻ Vay ở
  // Tổng quan); bảng bên dưới vẫn có đủ mọi loại số. Không có số nào như vậy thì lấy dòng đầu bảng (thấp nhất chung).
  const comparable = data.offers.find((o) => isComparableLending(o, data.latestMonth));
  const cheapest = comparable ?? data.offers[0];
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
              // Mức bình quân ngân hàng công bố (không phải lãi được duyệt); số có thể cũ hơn tháng mới nhất của bảng.
              label={comparable ? "Bình quân thấp nhất (KH cá nhân)" : "Bình quân thấp nhất trong dữ liệu"}
              value={formatPercent(cheapest.lendingAvgPercent)}
              hint={`${cheapest.shortName} · tháng ${formatMonth(cheapest.month)}${
                cheapest.segment || cheapest.source ? ` · ${lendingOriginLabel(cheapest).toLowerCase()}` : ""
              }${cheapest.monthsBehind >= STALE_MONTHS ? ` · cũ hơn ${cheapest.monthsBehind} tháng` : ""}`}
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

      {cheapest && (
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: -1 }}>
          Minh họa theo {cheapest.shortName} {formatPercent(cheapest.lendingAvgPercent)}/năm, giả định lãi giữ nguyên suốt{" "}
          {formatTerm(data.termMonths)}; không phải lãi suất được duyệt.
        </Typography>
      )}

      {data.ranking.status !== "NOT_AVAILABLE" && (
        <SectionCard
          title="Xếp hạng tổng hợp cho người vay"
          subtitle="Giá vay (lãi cho vay bình quân, lợi suất cho vay), phù hợp với khách hàng cá nhân, sức cho vay; bốn phương pháp đa tiêu chí, 10.000 lần rút trọng số."
        >
          <RankingSection purpose="LOAN" block={data.ranking} />
        </SectionCard>
      )}

      {data.programs.length > 0 && (
        <SectionCard
          title="Chương trình tín dụng ưu đãi liên quan"
          subtitle="Điều kiện vay do ngân hàng và văn bản của chương trình quy định; hãy hỏi ngân hàng trước khi quyết định."
        >
          <ProgramList programs={data.programs} />
        </SectionCard>
      )}

      {/* Chưa có xếp hạng: một dòng ngay trên bảng (dòng này nói "bảng dưới"), sau thẻ chương trình ưu đãi nếu có. */}
      {data.ranking.status === "NOT_AVAILABLE" && <RankingSection purpose="LOAN" block={data.ranking} />}

      <SectionCard
        title="Ước tính tiền trả theo lãi suất cho vay bình quân"
        subtitle={`Sắp theo lãi suất tăng dần, mỗi ngân hàng một số. Các số khác nhau về tháng và phạm vi công bố (nhãn cạnh số), không phải lãi suất bạn được duyệt. Tháng mới nhất: ${formatMonth(data.latestMonth)}.`}
        info="Thứ tự chọn số cho mỗi ngân hàng: số khách hàng cá nhân ngân hàng công bố; không có thì số chung; rồi đến nhóm hẹp ngân hàng chỉ công bố riêng (trung dài hạn, vay tiêu dùng); cuối cùng là số báo tổng hợp. Các số này không hoàn toàn cùng loại — rê chuột hoặc chạm vào nhãn cạnh số để xem chi tiết và nguồn. Dấu tam giác vàng: số cũ hơn 3 tháng so với tháng mới nhất."
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
                          {offer.basis ? ` · ${offer.basis === "NEW_LOANS" ? "vay mới" : "dư nợ"}` : ""}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {formatVnd(offer.firstPayment)}
                      {/* Điện thoại ẩn cột tổng tiền lãi (và trả tháng cuối đến md): ghi gọn dưới ô này để vẫn đọc được từng ngân hàng. */}
                      <Typography variant="caption" color="text.secondary" component="div" sx={{ display: { xs: "block", sm: "none" }, fontWeight: 400 }}>
                        Tổng lãi {formatVndCompact(offer.totalInterest)}
                      </Typography>
                      {declining && (
                        <Typography variant="caption" color="text.secondary" component="div" sx={{ display: { xs: "block", md: "none" }, fontWeight: 400 }}>
                          Tháng cuối {formatVndCompact(offer.lastPayment)}
                        </Typography>
                      )}
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
