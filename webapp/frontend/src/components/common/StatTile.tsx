"use client";

import { Box, Card, Stack, Typography } from "@mui/material";
import { keyframes } from "@mui/material/styles";
import { SparkLineChart } from "@mui/x-charts/SparkLineChart";
import { IconArrowDownRight, IconArrowUpRight, IconMinus } from "@tabler/icons-react";
import { useId, type ReactNode } from "react";
import { useChartPalette } from "@/theme/chart-palette";
import { EMPTY, formatDelta } from "@/utils/format";

export type StatTone = "primary" | "success" | "warning" | "info" | "secondary";

export interface StatDelta {
  /** Mức thay đổi (cùng đơn vị với giá trị, ví dụ điểm %). */
  value: number | null;
  /** Mốc so sánh, ví dụ "so với 30 ngày trước". */
  label: string;
  /** Tăng là tốt (xanh) hay xấu (đỏ); "neutral": không tô màu tốt/xấu. Mặc định tăng là tốt. */
  direction?: "up-good" | "down-good" | "neutral";
  /** Đơn vị in sau số, ví dụ " điểm %". */
  unit?: string;
}

interface StatTileProps {
  label: string;
  value: ReactNode;
  /** Dòng phụ dưới con số: nguồn, ngân hàng, so sánh. */
  hint?: ReactNode;
  icon?: ReactNode;
  /** Màu ô icon. */
  tone?: StatTone;
  delta?: StatDelta;
  /** Chuỗi nhỏ cho sparkline (cũ → mới); cần ít nhất 2 điểm. */
  trend?: { dates: Date[]; values: number[]; format: (v: number) => string; formatDate: (d: Date) => string };
  /**
   * Đổi khi số chuyển sang nguồn khác (ví dụ đổi kênh): phần chữ hiện dần để người xem thấy số vừa đổi.
   * Sparkline không dựng lại, chỉ cập nhật dữ liệu — dựng lại sẽ trống một nhịp và trông như nháy.
   */
  swapKey?: string;
}

const swapIn = keyframes`
  from { opacity: 0.15; transform: translateY(6px); }
  to { opacity: 1; transform: none; }
`;

/**
 * Thẻ KPI: ô icon màu + nhãn, con số lớn, chip thay đổi có mũi tên (không dùng màu đơn độc) và sparkline.
 * Con số dùng chữ số tỉ lệ (không tabular-nums) vì đứng một mình.
 */
export function StatTile({ label, value, hint, icon, tone = "primary", delta, trend, swapKey }: StatTileProps) {
  return (
    <Card sx={{ p: 2.25, height: "100%", display: "flex", flexDirection: "column" }}>
      <Box
        key={swapKey}
        sx={
          swapKey === undefined
            ? undefined
            : { animation: `${swapIn} 1000ms cubic-bezier(0.22, 1, 0.36, 1)`, "@media (prefers-reduced-motion: reduce)": { animation: "none" } }
        }
      >
        <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", mb: 1.5 }}>
          {icon && (
            <Box
              aria-hidden
              sx={{
                width: 34,
                height: 34,
                borderRadius: 2.5,
                display: "grid",
                placeItems: "center",
                flexShrink: 0,
                color: `${tone}.main`,
                bgcolor: (t) => (t.vars ? `rgba(${t.vars.palette[tone].mainChannel} / 0.14)` : "action.selected"),
              }}
            >
              {icon}
            </Box>
          )}
          <Typography variant="body2" color="text.secondary" component="h3" sx={{ fontWeight: 500, lineHeight: 1.35 }}>
            {label}
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
          <Typography sx={{ fontSize: "1.75rem", fontWeight: 700, lineHeight: 1.15, letterSpacing: "-0.01em" }}>{value}</Typography>
          {delta && <DeltaChip delta={delta} />}
        </Stack>
        {(hint || delta) && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, fontSize: "0.8125rem" }}>
            {hint}
            {hint && delta ? " · " : null}
            {delta?.label}
          </Typography>
        )}
      </Box>
      {trend && trend.values.length > 1 && <TrendSpark trend={trend} tone={tone} />}
    </Card>
  );
}

function DeltaChip({ delta }: { delta: StatDelta }) {
  const v = delta.value;
  if (v === null) return null;
  const flat = Math.abs(v) < 1e-9;
  const up = v > 0;
  const direction = delta.direction ?? "up-good";
  const good = direction === "neutral" || flat ? null : direction === "up-good" ? up : !up;
  const color = good === null ? "text.secondary" : good ? "success.main" : "error.main";
  const Arrow = flat ? IconMinus : up ? IconArrowUpRight : IconArrowDownRight;
  return (
    <Stack
      direction="row"
      spacing={0.25}
      sx={{
        alignItems: "center",
        px: 0.75,
        py: 0.25,
        borderRadius: 1.5,
        color,
        bgcolor: (t) => {
          if (!t.vars || good === null) return "action.hover";
          const channel = good ? t.vars.palette.success.mainChannel : t.vars.palette.error.mainChannel;
          return `rgba(${channel} / 0.12)`;
        },
      }}
    >
      <Arrow size={14} stroke={2.2} aria-hidden />
      <Typography component="span" sx={{ fontSize: "0.75rem", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
        {flat ? "0" : formatDelta(v)}
        {delta.unit ?? ""}
      </Typography>
    </Stack>
  );
}

function TrendSpark({ trend, tone }: { trend: NonNullable<StatTileProps["trend"]>; tone: StatTone }) {
  const palette = useChartPalette();
  const gradientId = `spark-${useId().replace(/:/g, "")}`;
  // Sparkline dùng màu định danh 1 của biểu đồ cho mọi thẻ: đây là cùng một đại lượng (lãi suất), khác nhau ở mức.
  const color = tone === "success" ? palette.series[2] : tone === "warning" ? palette.series[3] : palette.series[0];
  return (
    <Box
      sx={{
        mt: "auto",
        pt: 1.5,
        mx: -0.5,
        [`& .MuiLineChart-area`]: { fill: `url(#${gradientId})` },
        [`& .MuiLineChart-line`]: { strokeWidth: 2 },
      }}
    >
      <SparkLineChart
        data={trend.values}
        height={48}
        area
        curve="linear"
        color={color}
        showTooltip
        showHighlight
        baseline="min"
        xAxis={{ scaleType: "time", data: trend.dates, valueFormatter: (d: Date) => trend.formatDate(d) }}
        valueFormatter={(v) => (v === null ? EMPTY : trend.format(v))}
        margin={{ top: 4, bottom: 2, left: 4, right: 4 }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.28} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
      </SparkLineChart>
    </Box>
  );
}
