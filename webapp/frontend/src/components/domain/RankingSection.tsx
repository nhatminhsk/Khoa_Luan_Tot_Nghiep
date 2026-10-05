"use client";

import { Chip, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Typography } from "@mui/material";
import { IconArrowDownRight, IconArrowUpRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { BankLabel } from "@/components/common/BankLabel";
import { LoadingBlock, PendingResult } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { Purpose, RankingBlock } from "@/types/api";
import { formatNumber, formatQuarter } from "@/utils/format";

const PENDING_TEXT: Record<Purpose, string> = {
  SAVINGS:
    "Xếp hạng tổng hợp cho người gửi tiết kiệm sẽ cân nhắc ba tiêu chí riêng: lãi suất, độ an toàn của ngân hàng và trải nghiệm ứng dụng, theo mức ưu tiên bạn chọn. Kết quả hiện ở đây khi mô hình xếp hạng hoàn tất; trong lúc chờ, bảng dưới sắp các ngân hàng theo lãi suất hôm nay.",
  LOAN:
    "Xếp hạng tổng hợp cho người vay sẽ cân nhắc lãi suất cho vay, chương trình ưu đãi và sức khỏe tài chính của ngân hàng. Kết quả hiện ở đây khi mô hình xếp hạng hoàn tất; trong lúc chờ, bảng dưới sắp theo lãi suất cho vay bình quân.",
};

interface RankingSectionProps {
  purpose: Purpose;
  block: RankingBlock | undefined;
  isLoading?: boolean;
  compact?: boolean;
}

export function RankingSection({ purpose, block, isLoading, compact }: RankingSectionProps) {
  const catalog = useQuery({ queryKey: queryKeys.indicators, queryFn: marketRepository.indicators, staleTime: Infinity });
  if (isLoading || !block) return <LoadingBlock height={compact ? 96 : 160} />;

  if (block.status === "NOT_AVAILABLE") {
    return <PendingResult title="Chưa có kết quả xếp hạng" description={PENDING_TEXT[purpose]} compact={compact} />;
  }

  const indicatorName = (code: string | null) =>
    code ? catalog.data?.find((indicator) => indicator.code === code)?.name ?? code : null;

  return (
    <Stack spacing={1}>
      <Typography variant="body2" color="text.secondary">
        Theo số liệu {formatQuarter(block.asOfPeriod)}
        {block.methodVersion ? ` · phương pháp ${block.methodVersion}` : ""}
        {block.personalized ? " · đã tính theo mức ưu tiên của bạn" : " · xếp hạng mặc định"}
      </Typography>
      <TableContainer>
        <Table size="small" aria-label="Bảng xếp hạng ngân hàng">
          <TableHead>
            <TableRow>
              <TableCell>Hạng</TableCell>
              <TableCell>Ngân hàng</TableCell>
              {!compact && <TableCell align="right">Điểm</TableCell>}
              {!compact && <TableCell>Nhóm</TableCell>}
              {!compact && <TableCell>Tiêu chí tác động nhiều nhất</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {block.items.map((item) => (
              <TableRow key={item.ticker} hover>
                <TableCell>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <Typography sx={{ fontWeight: 700 }}>{item.rank}</Typography>
                    {item.rankLow !== null && item.rankHigh !== null && item.rankLow !== item.rankHigh && (
                      <Tooltip title="Khoảng hạng khi dữ liệu thiếu hoặc trọng số thay đổi">
                        <Chip size="small" variant="outlined" label={`${item.rankLow}–${item.rankHigh}`} />
                      </Tooltip>
                    )}
                  </Stack>
                </TableCell>
                <TableCell>
                  <BankLabel ticker={item.ticker} shortName={item.shortName} />
                </TableCell>
                {!compact && <TableCell align="right">{formatNumber(item.score, 3)}</TableCell>}
                {!compact && <TableCell>{item.groupLabel ?? "—"}</TableCell>}
                {!compact && (
                  <TableCell>
                    <Stack spacing={0.25}>
                      {item.topPositive && (
                        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", color: "success.main" }}>
                          <IconArrowUpRight size={14} aria-label="Kéo hạng lên" />
                          <Typography variant="caption" color="text.primary">
                            {indicatorName(item.topPositive)}
                          </Typography>
                        </Stack>
                      )}
                      {item.topNegative && (
                        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", color: "error.main" }}>
                          <IconArrowDownRight size={14} aria-label="Kéo hạng xuống" />
                          <Typography variant="caption" color="text.primary">
                            {indicatorName(item.topNegative)}
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
    </Stack>
  );
}
