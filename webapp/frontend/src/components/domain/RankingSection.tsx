"use client";

import { Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Typography } from "@mui/material";
import { IconArrowDownRight, IconArrowUpRight } from "@tabler/icons-react";
import { BankLabel } from "@/components/common/BankLabel";
import { LoadingBlock, PendingResult } from "@/components/common/States";
import type { Purpose, RankingBlock } from "@/types/api";
import { formatDate, formatMonth, formatPercent, formatQuarter, formatVndCompact } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";

/** Hạn mức bảo hiểm tiền gửi (Thông tư 05/2026/TT-NHNN, từ 13/07/2026), tính cả gốc lẫn lãi. */
const DEPOSIT_INSURANCE_LIMIT = 350_000_000;

const PENDING_TEXT: Record<Purpose, string> = {
  SAVINGS:
    "Xếp hạng tổng hợp cho người gửi cân nhắc lãi suất và độ an toàn của ngân hàng (vốn, nợ xấu, thanh khoản…). Kết quả hiện ở đây khi pipeline ghi bảng xếp hạng.",
  LOAN: "Xếp hạng tổng hợp cho người vay cân nhắc giá vay, mức phù hợp với khách hàng cá nhân và sức cho vay. Kết quả hiện ở đây khi pipeline ghi bảng xếp hạng.",
};

/** Một dòng đặt ngay trên bảng kết quả ở trang Gửi tiết kiệm / Vay khi chưa có xếp hạng: bảng đang sắp theo một tiêu chí. */
const PENDING_SHORT: Record<Purpose, string> = {
  SAVINGS: "Bảng dưới đang sắp theo lãi suất hôm nay (một tiêu chí), chưa phải xếp hạng tổng hợp.",
  LOAN: "Bảng dưới đang sắp theo lãi suất cho vay bình quân (một tiêu chí), chưa phải xếp hạng tổng hợp.",
};

const TERM_NOT_RANKED =
  "Kỳ hạn và kênh này không có trong dữ liệu xếp hạng (nguồn lãi chỉ có kỳ 1, 3, 6, 12, 18, 24, 36 tháng). Bảng dưới sắp theo lãi suất.";

/** Khối chờ của Tổng quan khi cả hai xếp hạng chưa có: một thông báo chung thay cho hai tab giống nhau. */
export const PENDING_BOTH =
  "Xếp hạng cho người gửi tiết kiệm (lãi suất, độ an toàn) và cho người vay (giá vay, phù hợp với cá nhân, sức cho vay) sẽ hiện ở đây khi pipeline ghi bảng xếp hạng.";

/** Cách đọc tần suất và khoảng hạng: đặt ở chú thích dưới bảng và tooltip tiêu đề cột. */
const SHARE_NOTE =
  "Tần suất trong 10.000 lần rút trọng số quanh mặc định, trung bình 4 phương pháp (SAW, TOPSIS, VIKOR, PROMETHEE II). Đây không phải xác suất ngân hàng tốt nhất.";
const RANGE_NOTE = "Hạng tốt nhất (5%) và tệ nhất (95%) qua các lần rút trọng số, bao ngoài 4 phương pháp.";

/** Dòng mô tả bảng: số liệu dùng, và trọng số (gửi: theo mốc tiền và hạn mức bảo hiểm tiền gửi). */
function describe(block: RankingBlock): string[] {
  const data = [`BCTC ${formatQuarter(block.asOfPeriod)}`];
  if (block.purpose === "SAVINGS") {
    if (block.ratesAsOf) data.push(`lãi ngày ${formatDate(block.ratesAsOf)}`);
    if (block.termMonths && block.channel) data.push(`${block.termMonths} tháng, ${CHANNEL_LABEL[block.channel].toLowerCase()}`);
  } else if (block.ratesAsOf) {
    data.push(`lãi vay tới ${formatMonth(block.ratesAsOf)}`);
  }
  const lines = [data.join(" · ")];
  if (block.purpose === "LOAN") {
    lines.push("Trọng số: giá vay, phù hợp với khách hàng cá nhân, sức cho vay, mỗi nhóm 1/3.");
  } else if (block.amountVnd === null) {
    lines.push(`Trọng số mặc định: lãi suất ${formatPercent((1 - (block.safetyWeight ?? 0.375)) * 100, 1)}, an toàn ${formatPercent((block.safetyWeight ?? 0.375) * 100, 1)}.`);
  } else if ((block.uninsuredShare ?? 0) === 0) {
    lines.push(
      `Mốc ${formatVndCompact(block.amountVnd)}: cả gốc lẫn lãi nằm trong hạn mức bảo hiểm tiền gửi ${formatVndCompact(DEPOSIT_INSURANCE_LIMIT)}, nên xếp theo lãi suất; an toàn chỉ để phân định khi lãi bằng nhau.`,
    );
  } else {
    lines.push(
      `Mốc ${formatVndCompact(block.amountVnd)}: ${formatPercent((block.uninsuredShare ?? 0) * 100, 0)} số tiền (gốc + lãi) vượt hạn mức bảo hiểm tiền gửi ${formatVndCompact(DEPOSIT_INSURANCE_LIMIT)}, nên độ an toàn chiếm ${formatPercent((block.safetyWeight ?? 0) * 100, 0)} trọng số.`,
    );
  }
  return lines;
}

interface RankingSectionProps {
  purpose: Purpose;
  block: RankingBlock | undefined;
  isLoading?: boolean;
  compact?: boolean;
}

export function RankingSection({ purpose, block, isLoading, compact }: RankingSectionProps) {
  if (isLoading || !block) return <LoadingBlock height={compact ? 96 : 160} />;

  if (block.status === "NOT_AVAILABLE") {
    if (block.reason === "TERM_NOT_RANKED") {
      return <PendingResult title="Chưa có xếp hạng cho lựa chọn này" description={TERM_NOT_RANKED} compact={compact} />;
    }
    // Trên trang Gửi tiết kiệm / Vay khối này nằm trên bảng thật: chỉ một dòng, giải thích dài ẩn sau "Xem thêm".
    return compact ? (
      <PendingResult title="Chưa có kết quả xếp hạng" description={PENDING_TEXT[purpose]} compact />
    ) : (
      <PendingResult title="Chưa có xếp hạng tổng hợp" description={PENDING_SHORT[purpose]} details={PENDING_TEXT[purpose]} />
    );
  }

  const [dataLine, weightLine] = describe(block);
  return (
    <Stack spacing={1}>
      <Typography variant="body2" color="text.secondary">
        {dataLine}
        {!compact && (
          <>
            <br />
            {weightLine}
          </>
        )}
      </Typography>
      <TableContainer>
        <Table size="small" aria-label="Bảng xếp hạng ngân hàng">
          <TableHead>
            <TableRow>
              <TableCell>Hạng</TableCell>
              <TableCell>Ngân hàng</TableCell>
              <TableCell align="right">
                <Tooltip title={SHARE_NOTE}>
                  <span>Đứng đầu</span>
                </Tooltip>
              </TableCell>
              {!compact && (
                <TableCell align="right">
                  <Tooltip title={SHARE_NOTE}>
                    <span>Lọt top 3</span>
                  </Tooltip>
                </TableCell>
              )}
              <TableCell align="center">
                <Tooltip title={RANGE_NOTE}>
                  <span>Khoảng hạng</span>
                </Tooltip>
              </TableCell>
              {!compact && <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Kéo hạng lên / xuống nhiều nhất</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {block.items.map((item) => (
              <TableRow key={item.ticker} hover>
                <TableCell>
                  <Typography sx={{ fontWeight: 700 }}>{item.rank}</Typography>
                </TableCell>
                <TableCell>
                  <BankLabel ticker={item.ticker} shortName={item.shortName} />
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {shareText(item.shareTop1)}
                </TableCell>
                {!compact && (
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {shareText(item.shareTop3)}
                  </TableCell>
                )}
                <TableCell align="center" sx={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
                  {item.rankLow !== null && item.rankHigh !== null
                    ? item.rankLow === item.rankHigh
                      ? item.rankLow
                      : `${item.rankLow}–${item.rankHigh}`
                    : "—"}
                </TableCell>
                {!compact && (
                  <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>
                    <Stack spacing={0.25}>
                      {item.topPositive && (
                        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", color: "success.main" }}>
                          <IconArrowUpRight size={14} aria-label="Kéo hạng lên" />
                          <Typography variant="caption" color="text.primary">
                            {item.topPositive}
                          </Typography>
                        </Stack>
                      )}
                      {item.topNegative && (
                        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", color: "error.main" }}>
                          <IconArrowDownRight size={14} aria-label="Kéo hạng xuống" />
                          <Typography variant="caption" color="text.primary">
                            {item.topNegative}
                          </Typography>
                        </Stack>
                      )}
                    </Stack>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {!compact && (
        <Typography variant="caption" color="text.secondary">
          {SHARE_NOTE} Khoảng hạng: {RANGE_NOTE.charAt(0).toLowerCase() + RANGE_NOTE.slice(1)} Kéo hạng lên / xuống: tiêu chí đóng
          góp nhiều nhất so với ngân hàng trung bình, ở trọng số mặc định.
        </Typography>
      )}
    </Stack>
  );
}

/** "89%"; dưới 0,5% ghi "<1%" thay vì "0%" khi vẫn có lần đứng đầu. */
function shareText(value: number | null): string {
  if (value === null) return "—";
  if (value > 0 && value < 0.005) return "<1%";
  return formatPercent(value * 100, 0);
}
