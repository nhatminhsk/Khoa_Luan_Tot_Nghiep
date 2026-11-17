"use client";

import {
  Box,
  Button,
  Link as MuiLink,
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
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { Indicator, IndicatorSnapshot, SnapshotCell } from "@/types/api";
import { formatQuarter } from "@/utils/format";
import { formatIndicator } from "@/utils/indicator";

/** Cột của ma trận: các chỉ tiêu người gửi/vay thường xem đầu tiên. */
const COLUMNS = [
  { code: "npl", short: "Nợ xấu" },
  { code: "loans_g2", short: "Nhóm 2" },
  { code: "npl_coverage", short: "Bao phủ" },
  { code: "car", short: "CAR" },
  { code: "ldr", short: "LDR" },
  { code: "casa", short: "CASA" },
  { code: "roe", short: "ROE" },
] as const;
type ColumnCode = (typeof COLUMNS)[number]["code"];
type SortKey = "bank" | ColumnCode;
type Tone = "success" | "error";

/** Chỉ chia nhóm khi có ít nhất chừng này ngân hàng cùng quý (quy ước hiển thị, tránh chia 3 nhóm trên mẫu quá ít). */
const MIN_BANKS_FOR_TONE = 5;
/** Dưới lg chỉ hiện chừng này dòng, có nút xem đủ. */
const COLLAPSED_ROWS = 10;

interface ColumnStats {
  indicator: Indicator;
  /** Quý tham chiếu: quý mới nhất có số của chỉ tiêu này. */
  period: string | null;
  /** Số ngân hàng có số ở quý tham chiếu. */
  count: number;
  median: number | null;
  /** Nhóm của một giá trị cùng quý tham chiếu; null = không tô (nhóm giữa, chỉ tiêu không có chiều tốt/xấu, mẫu ít). */
  toneOf: (value: number) => Tone | null;
}

/**
 * Ma trận chỉ tiêu tài chính 22 ngân hàng, số gần nhất trong 4 quý.
 * Mỗi chỉ tiêu chỉ so các ngân hàng có số **cùng quý tham chiếu** (quý mới nhất của chỉ tiêu đó): trung vị và nhóm tô màu chỉ tính
 * trên tập này; số của quý cũ hơn vẫn hiện kèm quý nhưng không tô, không góp vào trung vị. Nhóm theo vị trí tương đối
 * s = (số NH kém thuận lợi hơn + 0,5 × số NH bằng điểm) / (N − 1): s ≥ 2/3 tô xanh, s ≤ 1/3 tô đỏ. LDR không tô.
 * Đây là nhóm trong dữ liệu, không phải ngưỡng an toàn hay xếp hạng tổng hợp.
 */
export function HealthMatrixCard() {
  const snapshot = useQuery({ queryKey: queryKeys.indicatorSnapshot, queryFn: marketRepository.indicatorSnapshot });
  const latest = snapshot.data?.latestPeriod ?? null;

  return (
    <SectionCard
      title="Chỉ tiêu tài chính 22 ngân hàng"
      subtitle={`Mỗi cột so các NH có số cùng quý${latest ? ` (${formatQuarter(latest)})` : ""}; số quý cũ ghi kèm quý · bấm tiêu đề cột để sắp`}
      info="Mỗi cột so các ngân hàng có số cùng quý mới nhất của chỉ tiêu đó. Nền xanh: nhóm tương đối thuận lợi (1/3 đầu) theo chiều của chỉ tiêu; nền đỏ: nhóm tương đối kém thuận lợi (1/3 cuối). Nợ xấu, nợ nhóm 2 thấp là thuận lợi; bao phủ nợ xấu, CAR, CASA, ROE cao là thuận lợi. LDR không tô vì cao hay thấp đều có rủi ro riêng. Số của quý cũ ghi kèm quý và không tô. Đây không phải ngưỡng an toàn hay xếp hạng tổng hợp."
      flush
    >
      {snapshot.isError ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <ErrorState error={snapshot.error} onRetry={() => snapshot.refetch()} />
        </Box>
      ) : !snapshot.data ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <LoadingBlock height={420} />
        </Box>
      ) : snapshot.data.rows.length === 0 ? (
        <EmptyState title="Chưa có số liệu tài chính" />
      ) : (
        <Matrix data={snapshot.data} />
      )}
    </SectionCard>
  );
}

function columnStats(data: IndicatorSnapshot, indicator: Indicator): ColumnStats {
  const cells = data.rows.map((r) => r.values[indicator.code]).filter((c): c is SnapshotCell => c !== undefined);
  const period = cells.reduce<string | null>((p, c) => (p === null || c.period > p ? c.period : p), null);
  const values = cells.filter((c) => c.period === period && Number.isFinite(c.value)).map((c) => c.value);
  const n = values.length;
  const toneOf = (v: number): Tone | null => {
    if (indicator.direction === "NEUTRAL" || n < MIN_BANKS_FOR_TONE) return null;
    const worse = values.filter((x) => (indicator.direction === "HIGHER_BETTER" ? x < v : x > v)).length;
    const ties = values.filter((x) => x === v).length - 1;
    const s = (worse + 0.5 * ties) / (n - 1);
    return s >= 2 / 3 ? "success" : s <= 1 / 3 ? "error" : null;
  };
  return { indicator, period, count: n, median: medianOf(values), toneOf };
}

function Matrix({ data }: { data: IndicatorSnapshot }) {
  const theme = useTheme();
  const wide = useMediaQuery(theme.breakpoints.up("lg"));
  const [expanded, setExpanded] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: "bank", asc: true });
  const meta = new Map(data.indicators.map((i) => [i.code, i]));
  const columns = COLUMNS.filter((c) => meta.has(c.code));
  const stats = new Map(columns.map((c) => [c.code, columnStats(data, meta.get(c.code)!)]));

  const sorted = [...data.rows].sort((a, b) => {
    const dir = sort.asc ? 1 : -1;
    if (sort.key === "bank") return dir * a.ticker.localeCompare(b.ticker);
    const av = a.values[sort.key]?.value;
    const bv = b.values[sort.key]?.value;
    if (av === undefined) return 1;
    if (bv === undefined) return -1;
    return dir * (av - bv);
  });
  // Từ lg ma trận đứng cạnh hai thẻ biến động (cao) nên hiện đủ; màn hẹp thu gọn để trang không quá dài.
  const showAll = wide || expanded;
  const rows = showAll ? sorted : sorted.slice(0, COLLAPSED_ROWS);
  const toggle = (key: SortKey) => setSort((s) => (s.key === key ? { key, asc: !s.asc } : { key, asc: true }));

  return (
    <>
      <TableContainer>
        <Table
          size="small"
          aria-label="Chỉ tiêu tài chính của các ngân hàng"
          sx={{
            "& td, & th": { px: { xs: 1, sm: 1.25 }, py: 0.75 },
            // Cột ngân hàng đứng yên khi cuộn ngang trên điện thoại.
            "& td:first-of-type, & th:first-of-type": { pl: { xs: 2, sm: 2.5 }, position: "sticky", left: 0, zIndex: 1, bgcolor: "background.paper" },
          }}
        >
          <TableHead>
            <TableRow>
              <TableCell sortDirection={sort.key === "bank" ? (sort.asc ? "asc" : "desc") : false}>
                <TableSortLabel active={sort.key === "bank"} direction={sort.asc ? "asc" : "desc"} onClick={() => toggle("bank")}>
                  Ngân hàng
                </TableSortLabel>
              </TableCell>
              {columns.map((c) => {
                const st = stats.get(c.code)!;
                return (
                  <TableCell key={c.code} align="right" sortDirection={sort.key === c.code ? (sort.asc ? "asc" : "desc") : false}>
                    <Tooltip title={`${st.indicator.name} · so ${st.count} NH có số ${formatQuarter(st.period)}`}>
                      <TableSortLabel active={sort.key === c.code} direction={sort.asc ? "asc" : "desc"} onClick={() => toggle(c.code)}>
                        {c.short}
                        {st.period !== data.latestPeriod && (
                          <Box component="span" sx={{ display: "block", fontWeight: 400 }}>
                            {formatQuarter(st.period)}
                          </Box>
                        )}
                      </TableSortLabel>
                    </Tooltip>
                  </TableCell>
                );
              })}
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell sx={{ fontWeight: 600, color: "text.secondary" }}>Trung vị</TableCell>
              {columns.map((c) => {
                const st = stats.get(c.code)!;
                return (
                  <TableCell
                    key={c.code}
                    align="right"
                    title={`Trung vị ${st.count} NH có số ${formatQuarter(st.period)}`}
                    sx={{ fontWeight: 600, color: "text.secondary" }}
                  >
                    {formatIndicator(st.median, st.indicator.unit)}
                    <Typography variant="caption" color="text.secondary" component="div" sx={{ fontWeight: 400 }}>
                      {st.count} NH
                    </Typography>
                  </TableCell>
                );
              })}
            </TableRow>
            {rows.map((row) => (
              <TableRow key={row.ticker} hover>
                <TableCell>
                  <MuiLink component={Link} href={`/banks/${row.ticker}`} underline="hover" color="text.primary" sx={{ fontWeight: 600 }}>
                    {row.ticker}
                  </MuiLink>
                </TableCell>
                {columns.map((c) => (
                  <MatrixCell key={c.code} ticker={row.ticker} cell={row.values[c.code]} stats={stats.get(c.code)!} />
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Stack direction="row" spacing={2} useFlexGap sx={{ px: { xs: 2, sm: 2.5 }, py: 1.25, flexWrap: "wrap", alignItems: "center" }}>
        {!wide && sorted.length > COLLAPSED_ROWS && (
          <Button size="small" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded} sx={{ ml: -1 }}>
            {expanded ? "Thu gọn" : `Xem đủ ${sorted.length} ngân hàng`}
          </Button>
        )}
        <Legend tone="success" label="Nhóm tương đối thuận lợi" />
        <Legend tone="error" label="Nhóm tương đối kém thuận lợi" />
        <Typography variant="caption" color="text.secondary">
          theo từng chỉ tiêu, so các NH cùng quý
        </Typography>
      </Stack>
    </>
  );
}

function MatrixCell({ ticker, cell, stats }: { ticker: string; cell: SnapshotCell | undefined; stats: ColumnStats }) {
  if (!cell) {
    return (
      <TableCell align="right" sx={{ color: "text.disabled" }} title={`${ticker}: chưa có số ${stats.indicator.name}`}>
        —
      </TableCell>
    );
  }
  const current = cell.period === stats.period;
  const tone = current ? stats.toneOf(cell.value) : null;
  const value = formatIndicator(cell.value, stats.indicator.unit);
  const group = tone === "success" ? "nhóm tương đối thuận lợi" : tone === "error" ? "nhóm tương đối kém thuận lợi" : current ? "nhóm giữa hoặc không chia nhóm" : "số quý cũ, không so";
  const describe = `${ticker} · ${stats.indicator.name}: ${value} (${formatQuarter(cell.period)}); trung vị ${formatIndicator(stats.median, stats.indicator.unit)} của ${stats.count} NH ${formatQuarter(stats.period)}; ${group}`;
  return (
    <TableCell
      align="right"
      title={describe}
      aria-label={describe}
      sx={(t) => ({
        whiteSpace: "nowrap",
        ...(tone &&
          t.vars && {
            bgcolor: `rgba(${t.vars.palette[tone].mainChannel} / 0.10)`,
            ...t.applyStyles("dark", { bgcolor: `rgba(${t.vars.palette[tone].mainChannel} / 0.14)` }),
          }),
      })}
    >
      {value}
      {!current && (
        <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
          {formatQuarter(cell.period)}
        </Typography>
      )}
    </TableCell>
  );
}

function Legend({ tone, label }: { tone: Tone; label: string }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
      <Box
        aria-hidden
        sx={{
          width: 14,
          height: 14,
          borderRadius: 0.75,
          bgcolor: (t) => (t.vars ? `rgba(${t.vars.palette[tone].mainChannel} / 0.28)` : `${tone}.main`),
        }}
      />
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}

function medianOf(values: number[]): number | null {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
