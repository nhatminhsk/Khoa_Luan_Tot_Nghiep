"use client";

import { Box, Card, Link as MuiLink, Stack, Typography } from "@mui/material";
import { keyframes } from "@mui/material/styles";
import { SparkLineChart } from "@mui/x-charts/SparkLineChart";
import { IconArrowDownRight, IconArrowUpRight, IconMinus } from "@tabler/icons-react";
import Link from "next/link";
import { useId, type ReactNode } from "react";
import { EMPTY, formatDelta } from "@/utils/format";

/** Màu nhấn của một trụ dashboard (khai báo trong theme). */
export type PillarTone = "deposit" | "loan" | "health" | "macro";

export interface PillarMetric {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  /** Thay đổi so với mốc trước (cùng đơn vị với giá trị). */
  delta?: { value: number | null; unit?: string; direction?: "up-good" | "down-good" | "neutral"; title?: string };
}

interface PillarCardProps {
  tone: PillarTone;
  icon: ReactNode;
  title: string;
  /** Phạm vi số liệu: kỳ hạn, kênh, tháng, quý. */
  scope?: ReactNode;
  metrics: [PillarMetric, PillarMetric];
  /** Sparkline của chỉ số thứ hai hoặc chỉ số chính (cũ → mới). */
  trend?: {
    values: number[];
    dates?: Date[];
    /** Nhãn mốc khi không có ngày (quý, tháng) — để tooltip ghi được mốc của từng điểm. */
    labels?: string[];
    format: (v: number) => string;
    formatDate?: (d: Date) => string;
    label: string;
    /** Lãi niêm yết đổi theo bậc: "stepAfter". Mặc định nối thẳng. */
    curve?: "linear" | "stepAfter";
  };
  href?: string;
  linkLabel?: string;
  /** Đổi khi số chuyển sang nguồn khác (đổi kênh): phần số hiện dần, khung thẻ giữ nguyên. */
  swapKey?: string;
}

const swapIn = keyframes`
  from { opacity: 0.25; transform: translateY(4px); }
  to { opacity: 1; transform: none; }
`;

/**
 * Thẻ KPI theo trụ (Gửi tiết kiệm / Vay / Sức khỏe / Vĩ mô): vạch màu trụ ở đầu thẻ, hai con số cạnh nhau, sparkline dưới cùng.
 * Màu trụ chỉ để nhận ra nhóm; tốt/xấu vẫn dùng xanh/đỏ kèm mũi tên.
 */
export function PillarCard({ tone, icon, title, scope, metrics, trend, href, linkLabel = "Xem", swapKey }: PillarCardProps) {
  return (
    <Card
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
        // Vạch màu trụ trên đỉnh thẻ.
        "&::before": { content: '""', position: "absolute", inset: "0 0 auto 0", height: 3, bgcolor: `${tone}.main` },
      }}
    >
      <Box sx={{ p: { xs: 1.75, sm: 2 }, pb: trend ? 0.5 : { xs: 1.75, sm: 2 }, flex: 1 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1.25 }}>
          <Box
            aria-hidden
            sx={{
              width: 28,
              height: 28,
              borderRadius: 2,
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
              color: `${tone}.main`,
              // Màu trụ là khóa palette tự thêm: MUI vẫn sinh biến mainChannel nhưng kiểu của theme.vars không có, nên ép kiểu.
              bgcolor: (t) => (t.vars ? `rgba(${(t.vars.palette[tone] as { mainChannel?: string }).mainChannel} / 0.14)` : "action.selected"),
            }}
          >
            {icon}
          </Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography variant="overline" component="h3" sx={{ color: `${tone}.main`, display: "block", lineHeight: 1.3 }}>
              {title}
            </Typography>
            {/* Tối đa hai dòng: phạm vi quyết định cách hiểu con số nên không được cắt mất. */}
            {scope && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "-webkit-box", lineHeight: 1.3, WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}
              >
                {scope}
              </Typography>
            )}
          </Box>
          {href && (
            <MuiLink component={Link} href={href} variant="caption" underline="hover" sx={{ fontWeight: 600, flexShrink: 0 }}>
              {linkLabel}
            </MuiLink>
          )}
        </Stack>
        <Box
          key={swapKey}
          sx={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            columnGap: 1.5,
            ...(swapKey !== undefined && {
              animation: `${swapIn} 900ms cubic-bezier(0.22, 1, 0.36, 1)`,
              "@media (prefers-reduced-motion: reduce)": { animation: "none" },
            }),
          }}
        >
          {metrics.map((m) => (
            <Metric key={m.label} metric={m} />
          ))}
        </Box>
      </Box>
      {trend && trend.values.length > 1 && <Spark trend={trend} tone={tone} />}
    </Card>
  );
}

function Metric({ metric }: { metric: PillarMetric }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.35 }}>
        {metric.label}
      </Typography>
      <Stack direction="row" spacing={0.75} useFlexGap sx={{ alignItems: "baseline", flexWrap: "wrap" }}>
        <Typography sx={{ fontSize: { xs: "1.25rem", sm: "1.5rem" }, fontWeight: 700, lineHeight: 1.2, letterSpacing: "-0.01em" }}>
          {metric.value}
        </Typography>
        {metric.delta && <Delta {...metric.delta} />}
      </Stack>
      {metric.hint && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.35, mt: 0.25 }}>
          {metric.hint}
        </Typography>
      )}
    </Box>
  );
}

function Delta({ value, unit = "", direction = "up-good", title }: NonNullable<PillarMetric["delta"]>) {
  if (value === null) return null;
  const flat = Math.abs(value) < 1e-9;
  const up = value > 0;
  const good = direction === "neutral" || flat ? null : direction === "up-good" ? up : !up;
  const Arrow = flat ? IconMinus : up ? IconArrowUpRight : IconArrowDownRight;
  return (
    <Stack
      direction="row"
      spacing={0.25}
      title={title}
      sx={{ alignItems: "center", color: good === null ? "text.secondary" : good ? "success.main" : "error.main" }}
    >
      <Arrow size={13} stroke={2.2} aria-hidden />
      <Typography component="span" sx={{ fontSize: "0.75rem", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
        {flat ? "0" : formatDelta(value)}
        {unit}
      </Typography>
    </Stack>
  );
}

function Spark({ trend, tone }: { trend: NonNullable<PillarCardProps["trend"]>; tone: PillarTone }) {
  const gradientId = `pillar-${useId().replace(/:/g, "")}`;
  return (
    <Box
      sx={{
        color: `${tone}.main`,
        "& .MuiLineChart-area": { fill: `url(#${gradientId})` },
        "& .MuiLineChart-line": { strokeWidth: 2 },
      }}
      aria-label={trend.label}
      role="img"
    >
      <SparkLineChart
        data={trend.values}
        height={44}
        area
        curve={trend.curve ?? "linear"}
        color="currentColor"
        showTooltip
        showHighlight
        baseline="min"
        xAxis={
          trend.dates
            ? { scaleType: "time", data: trend.dates, valueFormatter: (d: Date) => trend.formatDate?.(d) ?? "" }
            : trend.labels
              ? { scaleType: "point", data: trend.labels }
              : undefined
        }
        valueFormatter={(v) => (v === null ? EMPTY : trend.format(v))}
        margin={{ top: 4, bottom: 2, left: 0, right: 0 }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity={0.26} />
            <stop offset="100%" stopColor="currentColor" stopOpacity={0} />
          </linearGradient>
        </defs>
      </SparkLineChart>
    </Box>
  );
}
