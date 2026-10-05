"use client";

import { Box, type SxProps, type Theme } from "@mui/material";
import { LineChart } from "@mui/x-charts/LineChart";
import { useChartPalette } from "@/theme/chart-palette";
import { EMPTY } from "@/utils/format";

export interface ChartSeries {
  id: string;
  label: string;
  data: (number | null)[];
  /** "reference": đường tham chiếu xám (trung vị); "series": một thực thể (ngân hàng). */
  kind?: "series" | "reference";
  /** Vị trí màu cố định của thực thể (0–3). Mặc định theo thứ tự trong mảng. */
  colorIndex?: number;
  /** Nét đứt: chỉ dùng cho giá trị dự báo/ước tính, không dùng cho số thật. */
  dashed?: boolean;
}

interface SeriesLineChartProps {
  /** Nhãn trục x dạng chuỗi (quý, tháng) — dùng thang điểm đều. */
  categories?: string[];
  /** Hoặc ngày thật — dùng thang thời gian để khoảng cách đúng với thời gian. */
  dates?: Date[];
  series: ChartSeries[];
  height?: number;
  formatValue: (value: number) => string;
  formatCategory?: (value: string) => string;
  formatDate?: (value: Date) => string;
  ariaLabel: string;
}

export function SeriesLineChart({
  categories,
  dates,
  series,
  height = 260,
  formatValue,
  formatCategory,
  formatDate,
  ariaLabel,
}: SeriesLineChartProps) {
  const palette = useChartPalette();
  let entityIndex = 0;

  const chartSeries = series.map((s) => {
    const isReference = s.kind === "reference";
    const color = isReference
      ? palette.reference
      : palette.series[(s.colorIndex ?? entityIndex++) % palette.series.length];
    return {
      id: s.id,
      label: s.label,
      data: s.data,
      color,
      showMark: false,
      connectNulls: true,
      curve: "linear" as const,
      valueFormatter: (value: number | null) => (value === null ? EMPTY : formatValue(value)),
    };
  });

  const xAxis = dates
    ? [{ scaleType: "time" as const, data: dates, valueFormatter: (d: Date) => (formatDate ? formatDate(d) : d.toLocaleDateString("vi-VN")) }]
    : [{ scaleType: "point" as const, data: categories ?? [], valueFormatter: (v: string) => (formatCategory ? formatCategory(v) : v) }];

  // Nét mảnh 2px; đường dự báo nét đứt. (MUI X 9: class MuiLineChart-line + thuộc tính data-series.)
  // Khai báo kiểu tường minh: trải object động thẳng vào sx làm TypeScript báo "union type too complex" (TS2590).
  const dashed: Record<string, { strokeDasharray: string }> = Object.fromEntries(
    series.filter((s) => s.dashed).map((s) => [`& .MuiLineChart-line[data-series="${s.id}"]`, { strokeDasharray: "6 4" }]),
  );
  const chartSx: SxProps<Theme> = { width: "100%", "& .MuiLineChart-line": { strokeWidth: 2 }, ...dashed };

  return (
    <Box
      role="img"
      aria-label={ariaLabel}
      sx={chartSx}
    >
      <LineChart
        height={height}
        series={chartSeries}
        xAxis={xAxis}
        yAxis={[{ valueFormatter: (v: number) => formatValue(v), width: 56 }]}
        grid={{ horizontal: true }}
        hideLegend={series.length < 2}
        skipAnimation
      />
    </Box>
  );
}
