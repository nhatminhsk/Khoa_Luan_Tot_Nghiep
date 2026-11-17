"use client";

import {
  Box,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Tooltip,
  Typography,
} from "@mui/material";
import { IconInfoCircle } from "@tabler/icons-react";
import { BankLabel } from "@/components/common/BankLabel";
import { RateDelta } from "@/components/common/RateDelta";
import { RealRateValue } from "@/components/common/RealRateValue";
import { useChartPalette } from "@/theme/chart-palette";
import type { SavingsOffer, SnapshotCell } from "@/types/api";
import { formatPercent, formatQuarter, formatVnd } from "@/utils/format";
import { realRate } from "@/utils/real-rate";

/** Nợ xấu và CAR gần nhất của từng ngân hàng (từ snapshot chỉ tiêu), đặt cạnh lãi suất để người gửi xem cùng lúc. */
export interface OfferHealth {
  /** Quý mới nhất của snapshot: ô có quý khác thì ghi kèm quý. */
  latestPeriod: string | null;
  byTicker: Map<string, { npl?: SnapshotCell; car?: SnapshotCell }>;
}

/**
 * Lãi suất hôm nay của các ngân hàng cho đúng kỳ hạn/kênh, kèm tiền lãi ước tính.
 *
 * @param inflation lạm phát so cùng kỳ của tháng mới nhất (%); có thì hiện cột lãi suất thực
 * @param health nợ xấu và CAR; không có (đang tải, lỗi) thì bỏ hai cột, bảng lãi suất vẫn hiện
 */
export function SavingsOffersTable({
  offers,
  inflation,
  health,
}: {
  offers: SavingsOffer[];
  inflation?: number | null;
  health?: OfferHealth | null;
}) {
  const showReal = inflation !== null && inflation !== undefined;
  const palette = useChartPalette();
  const maxRate = Math.max(...offers.map((o) => o.ratePercent), 0.01);


  return (
    <TableContainer>
      <Table size="small" aria-label="Lãi suất và tiền lãi ước tính theo ngân hàng">
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: { xs: 40, sm: 48 } }}>#</TableCell>
            <TableCell>Ngân hàng</TableCell>
            {/* Backend đã sắp theo lãi suất giảm dần. */}
            <TableCell align="right" sortDirection="desc">
              <TableSortLabel active direction="desc">
                Lãi suất/năm
              </TableSortLabel>
            </TableCell>
            {showReal && (
              <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                <Tooltip title={`Tham chiếu: lãi suất niêm yết hôm nay trừ lạm phát ${formatPercent(inflation)} (CPI tháng gần nhất so với cùng kỳ năm trước); không dự báo sức mua trong kỳ gửi.`}>
                  <Box component="span" tabIndex={0} sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
                    Lãi thực
                    <IconInfoCircle size={14} aria-hidden />
                  </Box>
                </Tooltip>
              </TableCell>
            )}
            {/* Tiêu đề ngắn để bảng vừa cột kết quả 8/12 trên laptop; "ước tính" và số tiền gốc đã ghi ở phụ đề thẻ. */}
            <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
              Tiền lãi
            </TableCell>
            <TableCell align="right" sx={{ display: { xs: "none", lg: "table-cell" } }}>
              Nhận khi đáo hạn
            </TableCell>
            {/* Số trung tính (không tô tốt/xấu): đặt cạnh lãi suất để xem cùng lúc, không phải đánh giá hay khuyến nghị. */}
            {health && (
              <>
                <TableCell align="right" sx={{ display: { xs: "none", md: "table-cell" } }}>
                  <Tooltip title="Tỷ lệ nợ xấu, số gần nhất trong 4 quý">
                    <span>
                      Nợ xấu
                      <Box component="span" sx={{ display: "block", fontWeight: 400 }}>
                        {formatQuarter(health.latestPeriod)}
                      </Box>
                    </span>
                  </Tooltip>
                </TableCell>
                <TableCell align="right" sx={{ display: { xs: "none", md: "table-cell" } }}>
                  <Tooltip title="Hệ số an toàn vốn, số gần nhất trong 4 quý">
                    <span>
                      CAR
                      <Box component="span" sx={{ display: "block", fontWeight: 400 }}>
                        {formatQuarter(health.latestPeriod)}
                      </Box>
                    </span>
                  </Tooltip>
                </TableCell>
              </>
            )}
          </TableRow>
        </TableHead>
        <TableBody>
          {offers.map((offer) => (
            <TableRow key={offer.ticker} hover>
              <TableCell>
                <Typography variant="body2" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {offer.rateOrder}
                </Typography>
              </TableCell>
              <TableCell>
                <BankLabel ticker={offer.ticker} shortName={offer.shortName} />
                {/* Điện thoại, iPad dọc: hai cột nợ xấu/CAR ẩn, ghi gọn dưới tên ngân hàng. */}
                {health && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: { xs: "block", md: "none" }, lineHeight: 1.3 }}>
                    Nợ xấu {healthText(health, offer.ticker, "npl")}
                    <br />
                    CAR {healthText(health, offer.ticker, "car")}
                  </Typography>
                )}
              </TableCell>
              <TableCell align="right">
                <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", justifyContent: "flex-end" }}>
                  {/* Thanh dữ liệu: dài theo lãi suất (từ 0), để quét nhanh 22 dòng. */}
                  <Box
                    aria-hidden
                    sx={{ width: 56, height: 6, borderRadius: 3, bgcolor: "action.hover", display: { xs: "none", lg: "block" } }}
                  >
                    <Box sx={{ width: `${(offer.ratePercent / maxRate) * 100}%`, height: "100%", borderRadius: 3, bgcolor: palette.series[0] }} />
                  </Box>
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {formatPercent(offer.ratePercent)}
                    </Typography>
                    {/* Ngân hàng có lãi theo bậc số tiền: ghi bậc đã áp để người dùng biết vì sao khác bảng lãi chung. */}
                    {offer.tierLabel && (
                      <Typography variant="caption" color="primary.main" sx={{ display: "block", whiteSpace: "nowrap", fontWeight: 500 }}>
                        Bậc {offer.tierLabel.toLowerCase()}
                      </Typography>
                    )}
                    <RateDelta value={offer.changeFromPrevious} />
                    {/* Điện thoại: cột tiền lãi bị ẩn, hiện ngay dưới lãi suất. */}
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: { xs: "block", sm: "none" }, whiteSpace: "nowrap" }}
                    >
                      Lãi {formatVnd(offer.interest)}
                    </Typography>
                  </Box>
                </Stack>
              </TableCell>
              {showReal && (
                <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                  <RealRateValue value={realRate(offer.ratePercent, inflation)} />
                </TableCell>
              )}
              <TableCell align="right" sx={{ fontWeight: 600, display: { xs: "none", sm: "table-cell" } }}>
                {formatVnd(offer.interest)}
                {/* iPad và màn laptop: cột "Nhận khi đáo hạn" ẩn cho bảng vừa khung, số đó hiện dưới tiền lãi. */}
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: { xs: "none", sm: "block", lg: "none" }, fontWeight: 400, whiteSpace: "nowrap" }}
                >
                  Nhận {formatVnd(offer.maturityAmount)}
                </Typography>
              </TableCell>
              <TableCell align="right" sx={{ display: { xs: "none", lg: "table-cell" } }}>
                {formatVnd(offer.maturityAmount)}
              </TableCell>
              {health && (
                <>
                  <HealthCell health={health} ticker={offer.ticker} code="npl" />
                  <HealthCell health={health} ticker={offer.ticker} code="car" />
                </>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function healthText(health: OfferHealth, ticker: string, code: "npl" | "car"): string {
  const cell = health.byTicker.get(ticker)?.[code];
  if (!cell) return "—";
  return cell.period === health.latestPeriod ? formatPercent(cell.value) : `${formatPercent(cell.value)} (${formatQuarter(cell.period)})`;
}

function HealthCell({ health, ticker, code }: { health: OfferHealth; ticker: string; code: "npl" | "car" }) {
  const cell = health.byTicker.get(ticker)?.[code];
  return (
    <TableCell align="right" sx={{ display: { xs: "none", md: "table-cell" }, whiteSpace: "nowrap" }}>
      {cell ? formatPercent(cell.value) : "—"}
      {cell && cell.period !== health.latestPeriod && (
        <Typography variant="caption" color="text.secondary" component="div">
          {formatQuarter(cell.period)}
        </Typography>
      )}
    </TableCell>
  );
}
