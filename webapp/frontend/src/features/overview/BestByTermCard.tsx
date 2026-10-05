"use client";

import {
  Box,
  Link as MuiLink,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { IconChartBar, IconTable } from "@tabler/icons-react";
import Link from "next/link";
import { useState } from "react";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, LoadingBlock } from "@/components/common/States";
import { useChartPalette } from "@/theme/chart-palette";
import type { BestRate, BestRateItem } from "@/types/api";
import { EMPTY, formatPercent, formatTerm } from "@/utils/format";

/**
 * Lãi suất cao nhất theo kỳ hạn: cột "cao nhất trực tuyến" cạnh cột "trung vị" để thấy mức cao nhất vượt mức phổ biến
 * bao nhiêu ở từng kỳ hạn. Bảng (kèm tại quầy và tên ngân hàng) là chế độ xem thứ hai, cũng là bản cho trình đọc màn hình.
 */
export function BestByTermCard({ items }: { items: BestRateItem[] | undefined }) {
  const [view, setView] = useState<"chart" | "table">("chart");

  return (
    <SectionCard
      title="Lãi suất cao nhất theo kỳ hạn"
      subtitle="Trực tuyến, so với trung vị 22 ngân hàng"
      info="Ngân hàng trả cao nhất ở mỗi kỳ hạn hôm nay. Rê chuột lên cột để xem tên ngân hàng; chế độ Bảng có thêm kênh tại quầy."
      action={
        <ToggleButtonGroup exclusive size="small" value={view} onChange={(_, v) => v && setView(v)} aria-label="Cách xem">
          <ToggleButton value="chart" aria-label="Biểu đồ" sx={{ px: 1.5, gap: 0.75 }}>
            <IconChartBar size={16} aria-hidden /> Biểu đồ
          </ToggleButton>
          <ToggleButton value="table" aria-label="Bảng" sx={{ px: 1.5, gap: 0.75 }}>
            <IconTable size={16} aria-hidden /> Bảng
          </ToggleButton>
        </ToggleButtonGroup>
      }
      flush={view === "table"}
      sx={{ height: "100%" }}
    >
      {!items ? (
        <Box sx={{ p: view === "table" ? 2.5 : 0 }}>
          <LoadingBlock height={300} />
        </Box>
      ) : items.length === 0 ? (
        <EmptyState title="Chưa có số liệu lãi suất" />
      ) : view === "chart" ? (
        <BestByTermChart items={items} />
      ) : (
        <BestByTermTable items={items} />
      )}
    </SectionCard>
  );
}

function BestByTermChart({ items }: { items: BestRateItem[] }) {
  const palette = useChartPalette();
  const labels = items.map((i) => formatTerm(i.termMonths));
  return (
    <Box role="img" aria-label="Biểu đồ cột: lãi suất trực tuyến cao nhất và trung vị theo kỳ hạn" sx={{ width: "100%" }}>
      <Stack direction="row" spacing={2.5} sx={{ mb: 0.5 }} aria-hidden>
        <LegendKey color={palette.series[0]} label="Cao nhất (trực tuyến)" />
        <LegendKey color={palette.reference} label="Trung vị 22 ngân hàng" />
      </Stack>
      <BarChart
        height={290}
        hideLegend
        skipAnimation
        borderRadius={4}
        grid={{ horizontal: true }}
        xAxis={[{ scaleType: "band", data: labels, categoryGapRatio: 0.5, barGapRatio: 0.2 }]}
        yAxis={[{ valueFormatter: (v: number) => `${v}%`, width: 44 }]}
        margin={{ left: 0, right: 8, top: 8, bottom: 0 }}
        series={[
          {
            id: "best",
            label: "Cao nhất (trực tuyến)",
            data: items.map((i) => i.online?.rate ?? null),
            color: palette.series[0],
            valueFormatter: (v, { dataIndex }) => (v === null ? EMPTY : `${formatPercent(v)} · ${bankText(items[dataIndex].online)}`),
          },
          {
            id: "median",
            label: "Trung vị",
            data: items.map((i) => i.medianOnline),
            color: palette.reference,
            valueFormatter: (v) => (v === null ? EMPTY : formatPercent(v)),
          },
        ]}
      />
    </Box>
  );
}

function bankText(best: BestRate | null): string {
  if (!best) return EMPTY;
  return best.tiedCount > 0 ? `${best.shortName} và ${best.tiedCount} NH khác` : best.shortName;
}

function LegendKey({ color, label }: { color: string; label: string }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
      <Box sx={{ width: 10, height: 10, borderRadius: 0.75, bgcolor: color }} />
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}

function BestByTermTable({ items }: { items: BestRateItem[] }) {
  return (
    <TableContainer>
      <Table size="small" aria-label="Lãi suất cao nhất theo kỳ hạn">
        <TableHead>
          <TableRow>
            <TableCell>Kỳ hạn</TableCell>
            <TableCell>Trực tuyến cao nhất</TableCell>
            <TableCell>Tại quầy cao nhất</TableCell>
            <TableCell align="right">Trung vị trực tuyến</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.termMonths} hover>
              <TableCell sx={{ fontWeight: 600 }}>{formatTerm(item.termMonths)}</TableCell>
              <TableCell>
                <BestCell best={item.online} />
              </TableCell>
              <TableCell>
                <BestCell best={item.counter} />
              </TableCell>
              <TableCell align="right">{formatPercent(item.medianOnline)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/** Lãi suất in đậm, ngân hàng ở dòng dưới — gọn để bảng không phải cuộn ngang. */
function BestCell({ best }: { best: BestRate | null }) {
  if (!best) return <Typography color="text.secondary">—</Typography>;
  return (
    <Box>
      <Typography sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums", lineHeight: 1.3 }}>{formatPercent(best.rate)}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.3 }}>
        <MuiLink component={Link} href={`/banks/${best.ticker}`} color="inherit" underline="hover">
          {best.shortName}
        </MuiLink>
        {best.tiedCount > 0 && ` và ${best.tiedCount} NH khác`}
      </Typography>
    </Box>
  );
}
