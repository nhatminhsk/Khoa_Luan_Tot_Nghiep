"use client";

import {
  Alert,
  Autocomplete,
  Box,
  Chip,
  Grid,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { IconCheck } from "@tabler/icons-react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Fragment, useMemo, useState } from "react";
import { SeriesLineChart } from "@/components/charts/SeriesLineChart";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { useBanks } from "@/hooks/use-banks";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { useChartPalette } from "@/theme/chart-palette";
import type { Bank, Indicator } from "@/types/api";
import { formatNumber, formatPercent, formatQuarter } from "@/utils/format";
import { formatIndicator, isBetter } from "@/utils/indicator";
import { CAMELS_LABEL, CAMELS_ORDER } from "@/utils/labels";
import { rateDayText } from "@/utils/today";

const MAX_BANKS = 4;
/** Ví dụ bấm nhanh khi chưa chọn ngân hàng — chỉ để thử trang, không phải gợi ý nên chọn ngân hàng nào. */
const EXAMPLES: string[][] = [
  ["VCB", "BID", "CTG"],
  ["VCB", "TCB"],
  ["MBB", "ACB", "VPB"],
];

/**
 * Gán màu cố định cho từng ngân hàng: ngân hàng đã chọn giữ màu khi thêm/bớt ngân hàng khác
 * (màu theo thực thể, không theo thứ tự) — ngân hàng mới nhận màu trống đầu tiên.
 */
function useStableSlots(tickers: string[]): Map<string, number> {
  const key = tickers.join(",");
  const [state, setState] = useState(() => ({ key, slots: assignSlots(new Map(), tickers) }));
  // Mẫu "điều chỉnh state khi prop đổi" của React: tính lại ngay trong lần render này, không cần effect.
  if (state.key !== key) {
    const slots = assignSlots(state.slots, tickers);
    setState({ key, slots });
    return slots;
  }
  return state.slots;
}

function assignSlots(previous: Map<string, number>, tickers: string[]): Map<string, number> {
  const next = new Map<string, number>();
  for (const t of tickers) if (previous.has(t)) next.set(t, previous.get(t)!);
  for (const t of tickers) {
    if (next.has(t)) continue;
    let slot = 0;
    while ([...next.values()].includes(slot)) slot++;
    next.set(t, slot);
  }
  return next;
}

export function CompareView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { banks, byTicker } = useBanks();
  const palette = useChartPalette();

  const tickers = useMemo(
    () =>
      [...new Set((searchParams.get("tickers") ?? "").split(",").map((t) => t.trim().toUpperCase()).filter(Boolean))].slice(
        0,
        MAX_BANKS,
      ),
    [searchParams],
  );
  const indicatorCode = searchParams.get("indicator") ?? "nim";
  const slots = useStableSlots(tickers);

  const catalog = useQuery({ queryKey: queryKeys.indicators, queryFn: marketRepository.indicators, staleTime: Infinity });
  const snapshot = useQuery({ queryKey: queryKeys.indicatorSnapshot, queryFn: marketRepository.indicatorSnapshot });
  const rates = useQuery({ queryKey: queryKeys.depositTable("ONLINE"), queryFn: () => marketRepository.depositTable("ONLINE") });
  const comparison = useQuery({
    queryKey: queryKeys.indicatorComparison(indicatorCode, tickers),
    queryFn: () => marketRepository.indicatorComparison(indicatorCode, tickers),
    enabled: tickers.length > 0,
    placeholderData: keepPreviousData,
  });

  const update = (next: { tickers?: string[]; indicator?: string }) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next.tickers) params.set("tickers", next.tickers.join(","));
    if (next.indicator) params.set("indicator", next.indicator);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const selected = tickers.map((t) => byTicker.get(t)).filter((b): b is Bank => !!b);
  const indicator = catalog.data?.find((c) => c.code === indicatorCode);

  return (
    <>
      <PageHeader
        title="So sánh ngân hàng"
        description="Đặt 2–4 ngân hàng cạnh nhau trên cùng các chỉ tiêu. Mỗi ngân hàng giữ một màu cố định trên biểu đồ và bảng."
      />

      <SectionCard sx={{ mb: 2.5 }}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Autocomplete
              multiple
              options={banks}
              value={selected}
              onChange={(_, value) => update({ tickers: value.slice(0, MAX_BANKS).map((b) => b.ticker) })}
              getOptionLabel={(b) => `${b.ticker} · ${b.shortName}`}
              isOptionEqualToValue={(a, b) => a.ticker === b.ticker}
              getOptionDisabled={() => selected.length >= MAX_BANKS}
              filterSelectedOptions
              renderValue={(value, getItemProps) =>
                value.map((bank, index) => {
                  const { key, ...itemProps } = getItemProps({ index });
                  return (
                    <Chip
                      key={key}
                      {...itemProps}
                      label={bank.shortName}
                      icon={<Swatch color={palette.series[slots.get(bank.ticker) ?? 0]} />}
                    />
                  );
                })
              }
              renderInput={(params) => (
                <TextField {...params} label="Ngân hàng" helperText={`Chọn tối đa ${MAX_BANKS} ngân hàng`} />
              )}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              select
              fullWidth
              label="Chỉ tiêu trên biểu đồ"
              value={catalog.data ? indicatorCode : ""}
              onChange={(e) => update({ indicator: e.target.value })}
            >
              {(catalog.data ?? []).map((c) => (
                <MenuItem key={c.code} value={c.code}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>
      </SectionCard>

      {tickers.length === 0 ? (
        <SectionCard>
          <EmptyState
            title="Chọn ngân hàng để so sánh"
            description="Gõ mã hoặc tên ngân hàng vào ô phía trên, chọn 2–4 ngân hàng. Hoặc thử một ví dụ:"
            action={
              <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", justifyContent: "center", mt: 0.5 }}>
                {EXAMPLES.map((group) => (
                  <Chip key={group.join()} label={group.join(" · ")} variant="outlined" clickable onClick={() => update({ tickers: group })} />
                ))}
              </Stack>
            }
          />
        </SectionCard>
      ) : (
        <Stack spacing={2.5}>
          {tickers.length === 1 && (
            <Alert severity="info">Chọn thêm ít nhất một ngân hàng để so sánh.</Alert>
          )}
          <SectionCard title={indicator ? `${indicator.name} theo quý` : "Biểu đồ"} subtitle={`Đường xám là trung vị các ngân hàng có số cùng quý.${indicator?.unit === "VND" ? " Đơn vị: nghìn tỷ đồng." : ""}`}
          >
            {comparison.isError ? (
              <ErrorState error={comparison.error} onRetry={() => comparison.refetch()} />
            ) : !comparison.data ? (
              <LoadingBlock height={320} />
            ) : (
              <Box sx={{ opacity: comparison.isPlaceholderData ? 0.5 : 1 }}>
                <SeriesLineChart
                  height={320}
                  categories={comparison.data.periods}
                  formatCategory={(p) => p.replace(/^20(\d{2})-Q(\d)$/, "Q$2/$1")}
                  series={[
                    ...comparison.data.banks.map((b) => ({
                      id: b.ticker,
                      label: b.shortName,
                      data: comparison.data.indicator.unit === "VND" ? b.values.map((v) => (v === null ? null : v / 1e12)) : b.values,
                      colorIndex: slots.get(b.ticker) ?? 0,
                    })),
                    {
                      id: "median",
                      label: "Trung vị các NH",
                      data:
                        comparison.data.indicator.unit === "VND"
                          ? comparison.data.median.map((v) => (v === null ? null : v / 1e12))
                          : comparison.data.median,
                      kind: "reference" as const,
                    },
                  ]}
                  formatValue={(v) =>
                    comparison.data.indicator.unit === "VND" ? `${formatNumber(v, 1)} nghìn tỷ` : formatPercent(v)
                  }
                  formatAxis={(v) => (comparison.data.indicator.unit === "VND" ? formatNumber(v, 0) : formatPercent(v))}
                  ariaLabel={`So sánh ${comparison.data.indicator.name} giữa ${selected.map((b) => b.shortName).join(", ")}`}
                />
              </Box>
            )}
          </SectionCard>

          <SectionCard
            title="Bảng so sánh"
            subtitle={`Số gần nhất trong 4 quý (mới nhất ${formatQuarter(snapshot.data?.latestPeriod)}). Dấu ✓ đánh dấu giá trị tốt nhất ở chỉ tiêu có chiều tốt/xấu rõ ràng, chỉ khi các ngân hàng có số cùng kỳ.`}
            flush
          >
            {snapshot.isError || catalog.isError ? (
              <Box sx={{ p: 2.5 }}>
                <ErrorState
                  error={snapshot.error ?? catalog.error}
                  onRetry={() => (snapshot.isError ? snapshot.refetch() : catalog.refetch())}
                />
              </Box>
            ) : !snapshot.data || !catalog.data ? (
              <Box sx={{ p: 2.5 }}>
                <LoadingBlock height={400} />
              </Box>
            ) : (
              <CompareTable
                banks={selected}
                slots={slots}
                colors={palette.series}
                indicators={catalog.data}
                latestPeriod={snapshot.data.latestPeriod}
                values={new Map(snapshot.data.rows.map((r) => [r.ticker, r.values]))}
                rate12={new Map((rates.data?.rows ?? []).map((r) => [r.ticker, r.cells["12"]?.rate ?? null]))}
                rateFailed={rates.isError}
                rateDate={rates.data?.rateDate ?? null}
              />
            )}
          </SectionCard>
        </Stack>
      )}
    </>
  );
}

function Swatch({ color }: { color: string }) {
  return <Box component="span" aria-hidden sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: color, ml: "8px !important" }} />;
}

interface CompareTableProps {
  banks: Bank[];
  slots: Map<string, number>;
  colors: readonly string[];
  indicators: Indicator[];
  latestPeriod: string | null;
  values: Map<string, Record<string, { value: number; period: string }>>;
  rate12: Map<string, number | null>;
  rateFailed: boolean;
  rateDate: string | null;
}

function CompareTable({ banks, slots, colors, indicators, latestPeriod, values, rate12, rateFailed, rateDate }: CompareTableProps) {
  /**
   * Giá trị tốt nhất để đánh ✓. `basis` là kỳ báo cáo của từng số: khác nhau thì không so ngang được,
   * không đánh ✓ (số và kỳ vẫn hiện).
   */
  const bestOf = (numbers: (number | null)[], direction: Indicator["direction"], basis?: (string | null)[]): number | null => {
    const present = numbers.filter((n): n is number => n !== null);
    if (present.length < 2 || direction === "NEUTRAL") return null;
    if (basis && new Set(basis.filter((b, i) => numbers[i] !== null)).size > 1) return null;
    return present.reduce((best, n) => (isBetter(n, best, direction) ? n : best));
  };
  const failedText = "Không tải được";

  const valueCell = (key: string, text: string, isBest: boolean, caption?: string) => (
    <TableCell key={key} align="right" sx={{ fontWeight: isBest ? 700 : 400 }}>
      <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end", alignItems: "center" }}>
        {isBest && (
          <Box component="span" sx={{ color: "success.main", display: "inline-flex" }}>
            <IconCheck size={14} aria-label="tốt nhất" />
          </Box>
        )}
        <span>{text}</span>
      </Stack>
      {caption && (
        <Typography variant="caption" color="text.secondary" component="div">
          {caption}
        </Typography>
      )}
    </TableCell>
  );

  const rateNumbers = banks.map((b) => rate12.get(b.ticker) ?? null);
  const bestRate = bestOf(rateNumbers, "HIGHER_BETTER");

  return (
    <TableContainer>
      <Table
        size="small"
        aria-label="Bảng so sánh chỉ tiêu giữa các ngân hàng"
        sx={{
          // Cột tên chỉ tiêu đủ rộng để đọc (trước đây bị bóp còn một chữ mỗi dòng trên điện thoại),
          // và đứng yên khi bảng cuộn ngang qua các ngân hàng.
          "& thead th:first-of-type, & tbody td:first-of-type:not([colspan])": {
            minWidth: { xs: 132, sm: 200 },
            position: { xs: "sticky", md: "static" },
            left: 0,
            zIndex: 1,
            bgcolor: "background.paper",
            boxShadow: { xs: "inset -1px 0 0 var(--mui-palette-divider)", md: "none" },
          },
          "& thead th:first-of-type": {
            backgroundImage: "linear-gradient(rgba(148, 163, 184, 0.06), rgba(148, 163, 184, 0.06))",
          },
        }}
      >
        <TableHead>
          <TableRow>
            <TableCell>Chỉ tiêu</TableCell>
            {banks.map((b) => (
              <TableCell key={b.ticker} align="right">
                <Stack direction="row" spacing={0.75} sx={{ justifyContent: "flex-end", alignItems: "center" }}>
                  <Box component="span" aria-hidden sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: colors[slots.get(b.ticker) ?? 0] }} />
                  {/* Điện thoại: tiêu đề cột ghi mã (VCB) thay vì tên (Vietcombank) cho hẹp cột. */}
                  <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>
                    {b.shortName}
                  </Box>
                  <Box component="span" sx={{ display: { xs: "inline", sm: "none" } }} title={b.shortName}>
                    {b.ticker}
                  </Box>
                </Stack>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell colSpan={banks.length + 1} sx={{ bgcolor: "action.hover", fontWeight: 600 }}>
              Cho người gửi tiền
            </TableCell>
          </TableRow>
          <TableRow hover>
            <TableCell>Lãi 12 tháng trực tuyến {rateDayText(rateDate)}</TableCell>
            {banks.map((b, i) =>
              valueCell(b.ticker, rateFailed ? failedText : formatPercent(rateNumbers[i]), !rateFailed && rateNumbers[i] !== null && rateNumbers[i] === bestRate),
            )}
          </TableRow>
          {CAMELS_ORDER.map((group) => {
            const rows = indicators.filter((ind) => ind.camelsGroup === group);
            if (rows.length === 0) return null;
            return (
              <Fragment key={group}>
                <TableRow>
                  <TableCell colSpan={banks.length + 1} sx={{ bgcolor: "action.hover", fontWeight: 600 }}>
                    {CAMELS_LABEL[group]}
                  </TableCell>
                </TableRow>
                {rows.map((ind) => {
                  const cells = banks.map((b) => values.get(b.ticker)?.[ind.code] ?? null);
                  const best = bestOf(
                    cells.map((c) => c?.value ?? null),
                    ind.direction,
                    cells.map((c) => c?.period ?? null),
                  );
                  return (
                    <TableRow key={ind.code} hover>
                      <TableCell>{ind.name}</TableCell>
                      {banks.map((b, i) => {
                        const cell = cells[i];
                        return valueCell(
                          b.ticker,
                          cell ? formatIndicator(cell.value, ind.unit) : "—",
                          cell !== null && cell.value === best,
                          cell && cell.period !== latestPeriod ? formatQuarter(cell.period) : undefined,
                        );
                      })}
                    </TableRow>
                  );
                })}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
