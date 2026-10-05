"use client";

import { Box, Stack, Typography } from "@mui/material";
import { LineChart } from "@mui/x-charts/LineChart";
import { useChartPalette } from "@/theme/chart-palette";
import { EMPTY } from "@/utils/format";

interface RangeBandChartProps {
  dates: Date[];
  min: number[];
  median: number[];
  max: number[];
  /** Đường tham chiếu (màu xám), ví dụ lạm phát; ô null là chưa có số, đường bị ngắt. */
  reference?: { label: string; data: (number | null)[] };
  height?: number;
  formatValue: (value: number) => string;
  formatDate: (value: Date) => string;
  ariaLabel: string;
}

/**
 * Phân bố theo thời gian: đường trung vị + vùng thấp nhất–cao nhất.
 * Vùng được vẽ bằng hai lớp diện tích xếp chồng (lớp đáy trong suốt = mức thấp nhất,
 * lớp trên = cao nhất − thấp nhất); tooltip vẫn hiện giá trị thật của từng mức.
 */
export function RangeBandChart({
  dates,
  min,
  median,
  max,
  reference,
  height = 280,
  formatValue,
  formatDate,
  ariaLabel,
}: RangeBandChartProps) {
  const palette = useChartPalette();
  const spread = max.map((value, i) => value - min[i]);

  return (
    <Box
      role="img"
      aria-label={ariaLabel}
      sx={{
        width: "100%",
        '& .MuiLineChart-line[data-series="median"]': { strokeWidth: 2 },
        '& .MuiLineChart-line[data-series="reference"]': { strokeWidth: 2 },
      }}
    >
      <Stack direction="row" spacing={2.5} sx={{ px: 1, mb: 0.5, flexWrap: "wrap", rowGap: 0.5 }} aria-hidden>
        <LegendKey swatch={<Box sx={{ width: 18, height: 2, bgcolor: palette.series[0] }} />} label="Trung vị" />
        <LegendKey
          swatch={<Box sx={{ width: 18, height: 10, bgcolor: palette.band, borderRadius: 0.5 }} />}
          label="Khoảng thấp nhất – cao nhất"
        />
        {reference && <LegendKey swatch={<Box sx={{ width: 18, height: 2, bgcolor: palette.reference }} />} label={reference.label} />}
      </Stack>
      <LineChart
        height={height}
        hideLegend
        skipAnimation
        grid={{ horizontal: true }}
        xAxis={[{ scaleType: "time", data: dates, valueFormatter: (d: Date) => formatDate(d) }]}
        yAxis={[{ valueFormatter: (v: number) => formatValue(v), width: 56 }]}
        series={[
          {
            id: "min",
            label: "Thấp nhất",
            data: min,
            stack: "range",
            area: true,
            showMark: false,
            color: "transparent",
            valueFormatter: (v) => (v === null ? EMPTY : formatValue(v)),
          },
          {
            id: "spread",
            label: "Cao nhất",
            data: spread,
            stack: "range",
            area: true,
            showMark: false,
            color: palette.band,
            valueFormatter: (_v, { dataIndex }) => formatValue(max[dataIndex]),
          },
          {
            id: "median",
            label: "Trung vị",
            data: median,
            showMark: false,
            color: palette.series[0],
            valueFormatter: (v) => (v === null ? EMPTY : formatValue(v)),
          },
          ...(reference
            ? [
                {
                  id: "reference",
                  label: reference.label,
                  data: reference.data,
                  showMark: false,
                  curve: "stepAfter" as const,
                  color: palette.reference,
                  valueFormatter: (v: number | null) => (v === null ? EMPTY : formatValue(v)),
                },
              ]
            : []),
        ]}
      />
    </Box>
  );
}

function LegendKey({ swatch, label }: { swatch: React.ReactNode; label: string }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
      {swatch}
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}
