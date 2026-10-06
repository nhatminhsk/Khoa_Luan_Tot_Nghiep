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
import { IconInfoCircle, IconStarFilled } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { BankLabel } from "@/components/common/BankLabel";
import { RateDelta } from "@/components/common/RateDelta";
import { RealRateValue } from "@/components/common/RealRateValue";
import { useChartPalette } from "@/theme/chart-palette";
import type { SavingsOffer } from "@/types/api";
import { formatNumber, formatPercent, formatVnd } from "@/utils/format";
import { realRate } from "@/utils/real-rate";

type SortKey = "rate" | "app";

/**
 * Lãi suất hôm nay của các ngân hàng cho đúng kỳ hạn/kênh, kèm tiền lãi ước tính.
 *
 * @param inflation lạm phát so cùng kỳ của tháng mới nhất (%); có thì hiện cột lãi suất thực
 */
export function SavingsOffersTable({ offers, inflation }: { offers: SavingsOffer[]; inflation?: number | null }) {
  const showReal = inflation !== null && inflation !== undefined;
  const [sortKey, setSortKey] = useState<SortKey>("rate");
  const palette = useChartPalette();
  const maxRate = Math.max(...offers.map((o) => o.ratePercent), 0.01);

  const sorted = useMemo(() => {
    const copy = [...offers];
    if (sortKey === "app") copy.sort((a, b) => (b.appScore ?? -1) - (a.appScore ?? -1));
    return copy; // backend đã sắp theo lãi suất giảm dần
  }, [offers, sortKey]);

  return (
    <TableContainer>
      <Table size="small" aria-label="Lãi suất và tiền lãi ước tính theo ngân hàng">
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: { xs: 40, sm: 48 } }}>#</TableCell>
            <TableCell>Ngân hàng</TableCell>
            <TableCell align="right" sortDirection={sortKey === "rate" ? "desc" : false}>
              <TableSortLabel active={sortKey === "rate"} direction="desc" onClick={() => setSortKey("rate")}>
                Lãi suất/năm
              </TableSortLabel>
            </TableCell>
            {showReal && (
              <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                <Tooltip title={`Lãi suất/năm trừ lạm phát ${formatPercent(inflation)} (CPI so cùng kỳ). Dương: tiền gửi tăng được sức mua.`}>
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
            <TableCell align="right" sx={{ display: { xs: "none", xl: "table-cell" } }}>
              Nhận khi đáo hạn
            </TableCell>
            <TableCell align="right" sortDirection={sortKey === "app" ? "desc" : false} sx={{ display: { xs: "none", sm: "table-cell" } }}>
              <Tooltip title="Điểm đánh giá ứng dụng trên Google Play (không có thì App Store)">
                <TableSortLabel active={sortKey === "app"} direction="desc" onClick={() => setSortKey("app")}>
                  Điểm app
                </TableSortLabel>
              </Tooltip>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sorted.map((offer) => (
            <TableRow key={offer.ticker} hover>
              <TableCell>
                <Typography variant="body2" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {offer.rateOrder}
                </Typography>
              </TableCell>
              <TableCell>
                <BankLabel ticker={offer.ticker} shortName={offer.shortName} />
              </TableCell>
              <TableCell align="right">
                <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", justifyContent: "flex-end" }}>
                  {/* Thanh dữ liệu: dài theo lãi suất (từ 0), để quét nhanh 22 dòng. */}
                  <Box
                    aria-hidden
                    sx={{ width: 56, height: 6, borderRadius: 3, bgcolor: "action.hover", display: { xs: "none", xl: "block" } }}
                  >
                    <Box sx={{ width: `${(offer.ratePercent / maxRate) * 100}%`, height: "100%", borderRadius: 3, bgcolor: palette.series[0] }} />
                  </Box>
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {formatPercent(offer.ratePercent)}
                    </Typography>
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
                  sx={{ display: { xs: "none", sm: "block", xl: "none" }, fontWeight: 400, whiteSpace: "nowrap" }}
                >
                  Nhận {formatVnd(offer.maturityAmount)}
                </Typography>
              </TableCell>
              <TableCell align="right" sx={{ display: { xs: "none", xl: "table-cell" } }}>
                {formatVnd(offer.maturityAmount)}
              </TableCell>
              <TableCell align="right" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                {offer.appScore === null ? (
                  "—"
                ) : (
                  <Typography component="span" variant="body2" sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
                    {formatNumber(offer.appScore, 1)}
                    <IconStarFilled size={12} aria-label="sao" />
                  </Typography>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
