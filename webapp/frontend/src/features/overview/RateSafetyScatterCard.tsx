"use client";

import { Box, Stack, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { ChartsReferenceLine } from "@mui/x-charts/ChartsReferenceLine";
import { ScatterChart } from "@mui/x-charts/ScatterChart";
import type { ScatterMarkerProps } from "@mui/x-charts/ScatterChart";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { useChartPalette } from "@/theme/chart-palette";
import { formatDelta, formatNumber, formatPercent, formatQuarter } from "@/utils/format";

/** Trục ngang: chỉ tiêu an toàn. "goodSide": phía nào của trục là an toàn hơn. */
const SAFETY_AXES = {
  npl: { label: "Nợ xấu", axis: "Tỷ lệ nợ xấu (NPL, %)", goodSide: "left", quadrant: "Góc trên bên trái: lãi cao hơn và nợ xấu thấp hơn trung vị." },
  car: { label: "An toàn vốn", axis: "Hệ số an toàn vốn (CAR, %)", goodSide: "right", quadrant: "Góc trên bên phải: lãi cao hơn và CAR cao hơn trung vị." },
} as const;
type SafetyCode = keyof typeof SAFETY_AXES;

interface Point {
  ticker: string;
  shortName: string;
  x: number;
  y: number;
  period: string;
}

/**
 * "Lãi cao có đi kèm rủi ro cao không?": mỗi ngân hàng là một chấm, trục dọc là lãi 12 tháng trực tuyến hôm nay,
 * trục ngang là chỉ tiêu an toàn (số gần nhất trong 4 quý). Hai đường trung vị chia bốn góc; hệ số Spearman kèm
 * ngưỡng ý nghĩa 5% để người đọc không suy diễn quá mức (EDA: mọi khoảng tin cậy đều chứa 0).
 */
export function RateSafetyScatterCard() {
  const [code, setCode] = useState<SafetyCode>("npl");
  const snapshot = useQuery({ queryKey: queryKeys.indicatorSnapshot, queryFn: marketRepository.indicatorSnapshot });
  const rates = useQuery({ queryKey: queryKeys.depositTable("ONLINE"), queryFn: () => marketRepository.depositTable("ONLINE") });

  // Chỉ các ngân hàng có số ở quý tham chiếu (quý mới nhất của chỉ tiêu): trộn số quý cũ vào làm sai tương quan và trung vị.
  const { points, period } = useMemo<{ points: Point[]; period: string | null }>(() => {
    if (!snapshot.data || !rates.data) return { points: [], period: null };
    const rateOf = new Map(rates.data.rows.map((r) => [r.ticker, r.cells["12"]?.rate]));
    const ref = snapshot.data.rows.reduce<string | null>((p, r) => {
      const c = r.values[code];
      return c && (p === null || c.period > p) ? c.period : p;
    }, null);
    const kept = snapshot.data.rows.flatMap((row) => {
      const cell = row.values[code];
      const y = rateOf.get(row.ticker);
      return cell && cell.period === ref && y !== undefined ? [{ ticker: row.ticker, shortName: row.shortName, x: cell.value, y, period: cell.period }] : [];
    });
    return { points: kept, period: ref };
  }, [snapshot.data, rates.data, code]);

  const meta = SAFETY_AXES[code];
  const rho = spearman(points.map((p) => p.x), points.map((p) => p.y));
  const critical = criticalRho(points.length);

  return (
    <SectionCard
      title="Lãi gửi và chỉ tiêu tài chính"
      subtitle={
        rho === null
          ? "Lãi 12 tháng trực tuyến hôm nay so với chỉ tiêu an toàn"
          : `${meta.label} ${formatQuarter(period)}, ${points.length} NH · Spearman ρ = ${formatDelta(rho)} · ${Math.abs(rho) >= critical ? "có ý nghĩa thống kê ở mức 5%" : "chưa có ý nghĩa thống kê"}`
      }
      info={`Mỗi chấm là một ngân hàng. Trục dọc: lãi 12 tháng trực tuyến hôm nay; trục ngang: ${meta.axis.toLowerCase()} của quý mới nhất (ngân hàng chưa có số quý này không vẽ). Hai đường xám là trung vị. Với ${points.length} ngân hàng, |ρ| phải từ ${formatNumber(critical)} trở lên mới có ý nghĩa thống kê ở mức 5%, nên lãi suất cao chưa đủ để kết luận ngân hàng kém an toàn hơn. Rê chuột lên chấm để xem tên ngân hàng.`}
      action={
        <PeriodToggle
          value={code}
          options={(Object.keys(SAFETY_AXES) as SafetyCode[]).map((c) => ({ value: c, label: SAFETY_AXES[c].label, title: SAFETY_AXES[c].axis }))}
          onChange={setCode}
          ariaLabel="Chỉ tiêu an toàn trên trục ngang"
        />
      }
    >
      {snapshot.isError || rates.isError ? (
        <ErrorState
          error={snapshot.error ?? rates.error}
          onRetry={() => {
            snapshot.refetch();
            rates.refetch();
          }}
        />
      ) : !snapshot.data || !rates.data ? (
        <LoadingBlock height={340} />
      ) : points.length < 3 ? (
        <EmptyState title="Chưa đủ số liệu để vẽ" />
      ) : (
        <ScatterPlot points={points} code={code} />
      )}
    </SectionCard>
  );
}

function ScatterPlot({ points, code }: { points: Point[]; code: SafetyCode }) {
  const palette = useChartPalette();
  const theme = useTheme();
  const meta = SAFETY_AXES[code];
  const medianX = median(points.map((p) => p.x));
  const medianY = median(points.map((p) => p.y));

  // Nhãn chọn lọc (không ghi tên mọi chấm): lãi cao nhất/thấp nhất và hai đầu trục an toàn; còn lại xem bằng tooltip.
  // Hai chấm được chọn mà gần nhau thì gộp nhãn ("HDB, EIB") vào chấm đầu để chữ không chồng lên nhau.
  const labels = useMemo(() => {
    const byY = [...points].sort((a, b) => b.y - a.y);
    const byX = [...points].sort((a, b) => a.x - b.x);
    const chosen = new Set([...byY.slice(0, 4), ...byY.slice(-3), byX[0], byX[byX.length - 1]]);
    const xRange = byX[byX.length - 1].x - byX[0].x || 1;
    const yRange = byY[0].y - byY[byY.length - 1].y || 1;
    const out = new Map<string, string>();
    const anchors: Point[] = [];
    for (const p of [...chosen].sort((a, b) => a.x - b.x)) {
      const near = anchors.find((a) => Math.abs(a.x - p.x) <= xRange * 0.1 && Math.abs(a.y - p.y) <= yRange * 0.06);
      if (near) {
        // Gộp nhãn vào chấm bên phải của nhóm để chữ không chạy đè lên chấm kia.
        out.set(p.ticker, `${out.get(near.ticker)}, ${p.ticker}`);
        out.delete(near.ticker);
        anchors[anchors.indexOf(near)] = p;
      } else {
        anchors.push(p);
        out.set(p.ticker, p.ticker);
      }
    }
    return out;
  }, [points]);

  // Nới biên trục một chút để chấm ở mép không đè lên trục.
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xPad = (Math.max(...xs) - Math.min(...xs)) * 0.06 || 0.5;
  const yPad = (Math.max(...ys) - Math.min(...ys)) * 0.08 || 0.2;

  const Marker = useMemo(() => {
    function LabelledMarker({ x, y, size, color, dataIndex, isFaded, isHighlighted }: ScatterMarkerProps) {
      const p = points[dataIndex];
      return (
        <g opacity={isFaded ? 0.35 : 1}>
          <circle
            cx={x}
            cy={y}
            r={isHighlighted ? size + 2 : size}
            fill={color}
            stroke={theme.vars?.palette.background.paper ?? theme.palette.background.paper}
            strokeWidth={2}
          />
          {p && (labels.has(p.ticker) || isHighlighted) && (
            <text
              x={x + size + 4}
              y={y + 4}
              fontSize={11}
              fontWeight={600}
              fill={theme.vars?.palette.text.secondary ?? theme.palette.text.secondary}
              style={{ pointerEvents: "none" }}
            >
              {isHighlighted ? p.ticker : labels.get(p.ticker)}
            </text>
          )}
        </g>
      );
    }
    return LabelledMarker;
  }, [points, labels, theme]);

  return (
    <Box role="img" aria-label={`Biểu đồ phân tán: lãi 12 tháng trực tuyến theo ${meta.axis}, ${points.length} ngân hàng`}>
      <ScatterChart
        height={340}
        skipAnimation
        hideLegend
        grid={{ horizontal: true, vertical: true }}
        margin={{ top: 12, right: 24, bottom: 8, left: 8 }}
        xAxis={[{ label: meta.axis, height: 56, min: Math.max(0, Math.min(...xs) - xPad), max: Math.max(...xs) + xPad, valueFormatter: (v: number) => `${formatNumber(v, 1)}%` }]}
        yAxis={[{ label: "Lãi 12 tháng trực tuyến (%)", min: Math.min(...ys) - yPad, max: Math.max(...ys) + yPad, valueFormatter: (v: number) => `${formatNumber(v, 1)}%`, width: 64 }]}
        series={[
          {
            id: "banks",
            label: "Ngân hàng",
            markerSize: 6,
            color: palette.series[0],
            data: points.map((p, i) => ({ x: p.x, y: p.y, id: i })),
            valueFormatter: (_v, { dataIndex }) => {
              const p = points[dataIndex];
              return `${p.shortName}: lãi ${formatPercent(p.y)} · ${SAFETY_AXES[code].label.toLowerCase()} ${formatPercent(p.x)} (${formatQuarter(p.period)})`;
            },
          },
        ]}
        slots={{ marker: Marker }}
      >
        <ChartsReferenceLine x={medianX} lineStyle={{ stroke: palette.reference, strokeWidth: 1 }} />
        <ChartsReferenceLine
          y={medianY}
          lineStyle={{ stroke: palette.reference, strokeWidth: 1 }}
          label="Trung vị"
          labelAlign="end"
          labelStyle={{ fontSize: 11, fill: palette.reference }}
        />
      </ScatterChart>
      <Stack direction="row" spacing={1} sx={{ mt: 0.5, alignItems: "center" }}>
        <Box sx={{ width: 14, height: 1.5, bgcolor: palette.reference }} aria-hidden />
        <Typography variant="caption" color="text.secondary">
          Đường xám: trung vị. {meta.quadrant}
        </Typography>
      </Stack>
    </Box>
  );
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Hạng trung bình (cùng giá trị thì chia đều hạng). */
function ranks(values: number[]): number[] {
  const order = values.map((v, i) => [v, i] as const).sort((a, b) => a[0] - b[0]);
  const out = new Array<number>(values.length);
  for (let i = 0; i < order.length; ) {
    let j = i;
    while (j + 1 < order.length && order[j + 1][0] === order[i][0]) j++;
    for (let k = i; k <= j; k++) out[order[k][1]] = (i + j) / 2 + 1;
    i = j + 1;
  }
  return out;
}

/** Hệ số tương quan hạng Spearman = Pearson trên hạng. */
function spearman(xs: number[], ys: number[]): number | null {
  if (xs.length < 3) return null;
  const rx = ranks(xs);
  const ry = ranks(ys);
  const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;
  const mx = mean(rx);
  const my = mean(ry);
  let num = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < rx.length; i++) {
    num += (rx[i] - mx) * (ry[i] - my);
    dx += (rx[i] - mx) ** 2;
    dy += (ry[i] - my) ** 2;
  }
  return dx === 0 || dy === 0 ? null : num / Math.sqrt(dx * dy);
}

/**
 * Ngưỡng |ρ| có ý nghĩa ở mức 5% (hai phía), xấp xỉ qua phân phối t với n − 2 bậc tự do:
 * r* = t / √(t² + n − 2); t lấy theo khai triển Cornish–Fisher quanh z = 1,96 (sai số < 0,01 khi n ≥ 10).
 */
function criticalRho(n: number): number {
  const df = Math.max(n - 2, 1);
  const z = 1.959964;
  const t = z + (z ** 3 + z) / (4 * df) + (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2);
  return t / Math.sqrt(t * t + df);
}
