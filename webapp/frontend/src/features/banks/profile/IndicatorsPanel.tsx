"use client";

import { Box, Card, Chip, Grid, Stack, ToggleButton, ToggleButtonGroup, Tooltip, Typography } from "@mui/material";
import { IconInfoCircle, IconLayoutGrid, IconTable } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SeriesLineChart } from "@/components/charts/SeriesLineChart";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import type { IndicatorSeries } from "@/types/api";
import { formatQuarter } from "@/utils/format";
import { directionHint, formatIndicator, rankLabel } from "@/utils/indicator";
import { CAMELS_LABEL, CAMELS_ORDER } from "@/utils/labels";
import { QUARTER_PRESETS, type QuarterPreset, quarterPresetCount } from "@/utils/period-presets";
import { BankSummaryCard } from "./BankSummaryCard";
import { IndicatorTable, type TableMode } from "./IndicatorTable";

type ViewMode = "CARDS" | "TABLE";

export function IndicatorsPanel({ ticker }: { ticker: string }) {
  const query = useQuery({ queryKey: queryKeys.bankIndicators(ticker), queryFn: () => bankRepository.indicators(ticker) });
  const [view, setView] = useState<ViewMode>("CARDS");
  const [tableMode, setTableMode] = useState<TableMode>("YEAR");
  const [period, setPeriod] = useState<QuarterPreset>("ALL");

  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (!query.data) return <LoadingBlock height={520} />;

  return (
    <Stack spacing={3}>
      <BankSummaryCard data={query.data} />

      <Stack spacing={1.5}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ flexWrap: "wrap", rowGap: 1.5, alignItems: { sm: "center" } }}>
          <Stack direction="row" spacing={0.75} sx={{ alignItems: "center", mr: { sm: "auto" } }}>
            <Typography variant="h3" component="h2">
              Chỉ tiêu theo khung CAMELS
            </Typography>
            <Tooltip
              title={`${
                view === "CARDS"
                  ? "Mỗi thẻ: số gần nhất của ngân hàng, trung vị 22 ngân hàng cùng quý và thứ hạng; biểu đồ so với trung vị."
                  : "Bảng nhiều kỳ: theo năm lấy số quý 4 (chỉ tiêu cộng 4 quý ở quý 4 là số cả năm), năm đang dở lấy quý mới nhất."
              } So sánh với nhóm ngân hàng cùng loại sẽ có khi mô hình phân nhóm hoàn tất. Chỉ tiêu cộng 4 quý (TTM) đã triệt tiêu mùa vụ; nợ xấu và CASA thường thấp ở quý 4 rồi tăng lại quý 1, nên so sánh cùng quý các năm.`}
            >
              <Box component="span" tabIndex={0} aria-label="Cách đọc" sx={{ display: "inline-flex", color: "text.disabled", cursor: "help" }}>
                <IconInfoCircle size={16} stroke={1.8} aria-hidden />
              </Box>
            </Tooltip>
          </Stack>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={view}
            onChange={(_, v: ViewMode | null) => v !== null && setView(v)}
            aria-label="Dạng xem"
          >
            <ToggleButton value="CARDS" sx={{ px: 1.5, gap: 0.75 }}>
              <IconLayoutGrid size={16} aria-hidden />
              Thẻ và biểu đồ
            </ToggleButton>
            <ToggleButton value="TABLE" sx={{ px: 1.5, gap: 0.75 }}>
              <IconTable size={16} aria-hidden />
              Bảng nhiều kỳ
            </ToggleButton>
          </ToggleButtonGroup>
          {view === "TABLE" ? (
            <ToggleButtonGroup
              exclusive
              size="small"
              value={tableMode}
              onChange={(_, v: TableMode | null) => v !== null && setTableMode(v)}
              aria-label="Kỳ của bảng"
            >
              <ToggleButton value="YEAR" sx={{ px: 1.5 }}>
                Theo năm
              </ToggleButton>
              <ToggleButton value="QUARTER" sx={{ px: 1.5 }}>
                Theo quý
              </ToggleButton>
            </ToggleButtonGroup>
          ) : (
            <PeriodToggle value={period} options={QUARTER_PRESETS} onChange={setPeriod} ariaLabel="Khoảng thời gian của biểu đồ" />
          )}
        </Stack>
      </Stack>

      {view === "TABLE" ? (
        <Card>
          <IndicatorTable data={query.data} mode={tableMode} />
        </Card>
      ) : (
        <Grid container spacing={2}>
          {CAMELS_ORDER.flatMap((group) => query.data.indicators.filter((s) => s.indicator.camelsGroup === group)).map((series) => (
            <Grid key={series.indicator.code} size={{ xs: 12, sm: 6, lg: 4 }}>
              <IndicatorCard series={series} maxQuarters={quarterPresetCount(period)} />
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}

function IndicatorCard({ series, maxQuarters }: { series: IndicatorSeries; maxQuarters: number | null }) {
  const { indicator, latest } = series;
  const points = maxQuarters === null ? series.points : series.points.slice(-maxQuarters);
  const isVnd = indicator.unit === "VND";
  // Biểu đồ số tiền dùng đơn vị nghìn tỷ để trục gọn.
  const scale = (v: number | null) => (v === null ? null : isVnd ? v / 1e12 : v);
  const formatAxis = (v: number) =>
    isVnd ? `${v.toLocaleString("vi-VN", { maximumFractionDigits: 0 })}` : `${v.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;

  return (
    <Card sx={{ p: 2, height: "100%" }}>
      <Typography variant="overline" color="text.disabled" component="div" sx={{ lineHeight: 1.6 }}>
        {CAMELS_LABEL[indicator.camelsGroup]}
      </Typography>
      <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", minWidth: 0 }}>
          <Typography variant="subtitle2" component="h3">
            {indicator.name}
          </Typography>
          <Tooltip title={`${indicator.description ?? ""} ${directionHint(indicator)}.`}>
            <Box component="span" sx={{ color: "text.secondary", display: "inline-flex" }} tabIndex={0} aria-label="Giải thích chỉ tiêu">
              <IconInfoCircle size={15} />
            </Box>
          </Tooltip>
        </Stack>
        {latest && (
          <Chip size="small" variant="outlined" label={rankLabel(latest.rank, latest.bankCount, indicator.direction)} />
        )}
      </Stack>

      {latest ? (
        <>
          <Typography sx={{ fontSize: "1.5rem", fontWeight: 700, mt: 0.5 }}>{formatIndicator(latest.value, indicator.unit)}</Typography>
          <Typography variant="caption" color="text.secondary">
            {formatQuarter(latest.period)} · trung vị 22 NH {formatIndicator(latest.median, indicator.unit)}
          </Typography>
        </>
      ) : (
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Chưa có số liệu
        </Typography>
      )}

      {points.some((p) => p.value !== null) && (
        <Box sx={{ mt: 1, mx: -1 }}>
          <SeriesLineChart
            height={170}
            categories={points.map((p) => p.period)}
            formatCategory={(p) => p.replace(/^20(\d{2})-Q(\d)$/, "Q$2/$1")}
            series={[
              { id: "bank", label: "Ngân hàng", data: points.map((p) => scale(p.value)), colorIndex: 0 },
              { id: "median", label: "Trung vị 22 NH", data: points.map((p) => scale(p.median)), kind: "reference" },
            ]}
            formatValue={(v) => (isVnd ? `${v.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} nghìn tỷ` : formatAxis(v))}
            ariaLabel={`${indicator.name} theo quý so với trung vị 22 ngân hàng`}
          />
        </Box>
      )}
    </Card>
  );
}
