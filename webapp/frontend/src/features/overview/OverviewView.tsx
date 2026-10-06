"use client";

import { Box, Chip, Grid, IconButton, Stack, Tab, Tabs, ToggleButton, ToggleButtonGroup, Tooltip } from "@mui/material";
import {
  IconArrowsUpDown,
  IconChartLine,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
  IconScale,
  IconTrendingDown,
  IconTrophy,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { RangeBandChart } from "@/components/charts/RangeBandChart";
import { Disclaimer } from "@/components/common/Disclaimer";
import { PageHeader } from "@/components/common/PageHeader";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { StatTile, type StatDelta } from "@/components/common/StatTile";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { SectionCard } from "@/components/common/SectionCard";
import { RankingSection } from "@/components/domain/RankingSection";
import { BestByTermCard } from "@/features/overview/BestByTermCard";
import { RateHeatmapCard } from "@/features/overview/RateHeatmapCard";
import { RateMoversCard } from "@/features/overview/RateMoversCard";
import { RateSafetyScatterCard } from "@/features/overview/RateSafetyScatterCard";
import { RecentChangesCard } from "@/features/overview/RecentChangesCard";
import { TopRatesCard } from "@/features/overview/TopRatesCard";
import { WatchlistWidget } from "@/features/overview/WatchlistWidget";
import { useInflation } from "@/hooks/use-inflation";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { Channel, InflationPoint, MarketSummary, Purpose, RateTrendPoint } from "@/types/api";
import { formatDate, formatMonth, formatNumber, formatPercent } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";
import { DAILY_PRESETS, type DailyPreset, dailyPresetStart, indexesInDailyPreset, pick } from "@/utils/period-presets";
import { inflationByDate, realRate } from "@/utils/real-rate";

const TREND_TERMS = [6, 12, 24] as const;
/** Sparkline trong thẻ KPI: 3 tháng gần nhất; thay đổi so với mốc 1 tháng trước. */
const SPARK_PRESET: DailyPreset = "3M";
const KPI_CHANNELS: Channel[] = ["ONLINE", "COUNTER"];
/** Thẻ KPI tự chuyển giữa hai kênh sau mỗi khoảng này (đủ để đọc con số; rê chuột để dừng xem sparkline). */
const KPI_ROTATE_MS = 5000;

export function OverviewView() {
  const overview = useQuery({ queryKey: queryKeys.overview, queryFn: marketRepository.overview });
  const [rankingTab, setRankingTab] = useState<Purpose>("SAVINGS");
  const data = overview.data;
  // Backend bản cũ chưa trả số tại quầy: thẻ KPI đứng yên ở kênh trực tuyến.
  const hasCounter = Boolean(data?.counterMarket);
  const kpi = useRotatingChannel(hasCounter);

  if (overview.isError) return <ErrorState error={overview.error} onRetry={() => overview.refetch()} />;
  const market = (kpi.channel === "COUNTER" ? data?.counterMarket : data?.market) ?? undefined;
  const channelText = CHANNEL_LABEL[kpi.channel].toLowerCase();

  return (
    <>
      <PageHeader
        eyebrow={data?.rateDate ? `Lãi suất niêm yết ngày ${formatDate(data.rateDate)} · thẻ số: kỳ hạn 12 tháng, ${channelText}` : "Tổng quan"}
        title="Tổng quan thị trường"
        description="Lãi suất tiết kiệm của 22 ngân hàng hôm nay, diễn biến theo thời gian và xếp hạng quý mới nhất."
        actions={
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
            {hasCounter && <KpiChannelControl kpi={kpi} />}
            {market && data?.previousRateDate && (
              <Chip
                icon={<IconArrowsUpDown size={16} />}
                variant="outlined"
                label={`So với ${formatDate(data.previousRateDate)}: ${market.banksRaised} tăng · ${market.banksLowered} giảm · ${market.banksUnchanged} giữ nguyên`}
                sx={{ height: "auto", minHeight: 34, maxWidth: "100%", px: 0.5, "& .MuiChip-label": { whiteSpace: "normal", py: 0.5 } }}
              />
            )}
          </Stack>
        }
      />

      <Grid container spacing={2}>
        <Grid size={12}>
          <Box onMouseEnter={() => kpi.setPaused(true)} onMouseLeave={() => kpi.setPaused(false)}>
            <KpiRow market={market} channel={kpi.channel} hasCounter={hasCounter} />
          </Box>
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <MarketTrendCard />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          {/* Cùng kênh với thẻ KPI (tự chuyển, ghim, tạm dừng khi rê chuột). */}
          <Box sx={{ height: "100%" }} onMouseEnter={() => kpi.setPaused(true)} onMouseLeave={() => kpi.setPaused(false)}>
            <TopRatesCard channel={kpi.channel} />
          </Box>
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <RateMoversCard />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <RecentChangesCard />
        </Grid>

        <Grid size={12}>
          <RateHeatmapCard />
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <RateSafetyScatterCard />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <WatchlistWidget />
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <BestByTermCard items={data?.bestRates} />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <SectionCard title="Xếp hạng quý mới nhất" subtitle="Năm ngân hàng đứng đầu theo từng mục đích" sx={{ height: "100%" }}>
            <Tabs
              value={rankingTab}
              onChange={(_, value: Purpose) => setRankingTab(value)}
              sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
            >
              <Tab value="SAVINGS" label="Gửi tiết kiệm" />
              <Tab value="LOAN" label="Vay" />
            </Tabs>
            <RankingSection
              purpose={rankingTab}
              block={rankingTab === "SAVINGS" ? data?.savingsRanking : data?.loanRanking}
              isLoading={overview.isLoading}
              compact
            />
          </SectionCard>
        </Grid>
      </Grid>

      <Disclaimer />
    </>
  );
}

type RotatingChannel = ReturnType<typeof useRotatingChannel>;

/**
 * Kênh của thẻ KPI và thẻ Top lãi 12 tháng: tự chuyển trực tuyến ↔ tại quầy sau mỗi KPI_ROTATE_MS.
 * Dừng khi người dùng chọn một kênh hoặc bấm nút dừng (ghim), và tạm dừng khi rê chuột lên các thẻ đó.
 * Không phụ thuộc prefers-reduced-motion: đổi số không phải chuyển động (chỉ hiệu ứng mờ dần bị tắt),
 * và Windows tắt "Animation effects" là bật cờ này cho mọi trình duyệt.
 */
function useRotatingChannel(enabled: boolean) {
  const [selected, setSelected] = useState<Channel>("ONLINE");
  const [pinned, setPinned] = useState(false);
  const [paused, setPaused] = useState(false);
  const rotating = enabled && !pinned && !paused;

  useEffect(() => {
    if (!rotating) return;
    const id = window.setInterval(() => setSelected((c) => (c === "ONLINE" ? "COUNTER" : "ONLINE")), KPI_ROTATE_MS);
    return () => window.clearInterval(id);
  }, [rotating]);

  const channel: Channel = enabled ? selected : "ONLINE";
  return {
    channel,
    pinned,
    setPaused,
    choose: (c: Channel) => {
      setSelected(c);
      setPinned(true);
    },
    resume: () => setPinned(false),
  };
}

/** Nút chọn kênh cho thẻ KPI và thẻ Top lãi, kèm nút dừng/tiếp tục tự chuyển. */
function KpiChannelControl({ kpi }: { kpi: RotatingChannel }) {
  const autoLabel = kpi.pinned ? "Tự chuyển giữa trực tuyến và tại quầy" : "Dừng tự chuyển kênh";
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
      {/* Không dùng onChange của nhóm: bấm lại nút đang chọn cho giá trị null, trong khi ở đây nó nghĩa là "giữ kênh này". */}
      <ToggleButtonGroup exclusive size="small" value={kpi.channel} aria-label="Kênh gửi của thẻ số và top lãi">
        {KPI_CHANNELS.map((c) => (
          <ToggleButton key={c} value={c} title={`Thẻ số và top lãi: ${CHANNEL_LABEL[c].toLowerCase()}`} onClick={() => kpi.choose(c)} sx={{ px: 1.5 }}>
            {CHANNEL_LABEL[c]}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      <Tooltip title={autoLabel}>
        <IconButton size="small" aria-label={autoLabel} onClick={() => (kpi.pinned ? kpi.resume() : kpi.choose(kpi.channel))}>
          {kpi.pinned ? <IconPlayerPlayFilled size={14} /> : <IconPlayerPauseFilled size={14} />}
        </IconButton>
      </Tooltip>
    </Stack>
  );
}

/**
 * Bốn thẻ KPI cho kỳ hạn tham chiếu (12 tháng) của một kênh: cao nhất, trung vị, thấp nhất, lãi suất thực.
 * Số hôm nay lấy từ /overview; sparkline và mức thay đổi 1 tháng lấy từ chuỗi diễn biến cùng kỳ hạn và kênh.
 * Chuỗi của cả hai kênh được tải sẵn để lúc chuyển kênh sparkline không trống.
 */
function KpiRow({ market, channel, hasCounter }: { market: MarketSummary | undefined; channel: Channel; hasCounter: boolean }) {
  const term = market?.referenceTermMonths ?? 12;
  const online = useQuery({ queryKey: queryKeys.rateTrend(term, "ONLINE"), queryFn: () => marketRepository.rateTrend(term, "ONLINE") });
  const counter = useQuery({
    queryKey: queryKeys.rateTrend(term, "COUNTER"),
    queryFn: () => marketRepository.rateTrend(term, "COUNTER"),
    enabled: hasCounter,
  });
  const trend = channel === "COUNTER" ? counter : online;
  const inflation = useInflation();
  const cpi = inflation.data?.latest ?? null;

  const spark = useMemo(() => buildSpark(trend.data ?? [], inflation.data?.series ?? []), [trend.data, inflation.data]);

  if (!market) {
    return (
      <Grid container spacing={{ xs: 1.5, sm: 2 }}>
        {[0, 1, 2, 3].map((i) => (
          <Grid key={i} size={{ xs: 6, lg: 3 }}>
            <LoadingBlock height={178} />
          </Grid>
        ))}
      </Grid>
    );
  }

  const fmtDate = (d: Date) => formatDate(d.toISOString().slice(0, 10));
  const sparkOf = (values: (number | null)[]) => {
    const kept = spark.dates.flatMap((d, i) => (values[i] === null ? [] : [{ d, v: values[i] as number }]));
    return { dates: kept.map((k) => k.d), values: kept.map((k) => k.v), format: (v: number) => formatPercent(v), formatDate: fmtDate };
  };
  const monthDelta = (values: (number | null)[], today: number | null): StatDelta => ({
    value: today === null || spark.baseIndex === null || values[spark.baseIndex] === null ? null : today - (values[spark.baseIndex] as number),
    label: spark.baseDate ? `so với ${formatDate(spark.baseDate)}` : "",
    unit: " điểm",
  });
  const real = realRate(market.median, cpi?.yoyPercent);
  const channelText = CHANNEL_LABEL[channel].toLowerCase();

  return (
    // Thẻ giữ nguyên khi đổi kênh (dựng lại cả thẻ làm sparkline trống một nhịp → nháy); chỉ phần chữ hiện dần theo swapKey.
    <Grid container spacing={{ xs: 1.5, sm: 2 }}>
      <Grid size={{ xs: 6, lg: 3 }}>
        <StatTile
          swapKey={channel}
          icon={<IconTrophy size={18} aria-hidden />}
          tone="primary"
          label={`Cao nhất · ${term} tháng · ${channelText}`}
          value={formatPercent(market.highest?.rate)}
          hint={market.highest ? (market.highest.tiedCount > 0 ? `${market.highest.shortName} +${market.highest.tiedCount}` : market.highest.shortName) : undefined}
          delta={monthDelta(spark.max, market.highest?.rate ?? null)}
          trend={sparkOf(spark.max)}
        />
      </Grid>
      <Grid size={{ xs: 6, lg: 3 }}>
        <StatTile
          swapKey={channel}
          icon={<IconChartLine size={18} aria-hidden />}
          tone="info"
          label={`Trung vị · ${market.banksQuoted} ngân hàng · ${channelText}`}
          value={formatPercent(market.median)}
          delta={monthDelta(spark.median, market.median)}
          trend={sparkOf(spark.median)}
        />
      </Grid>
      <Grid size={{ xs: 6, lg: 3 }}>
        <StatTile
          swapKey={channel}
          icon={<IconTrendingDown size={18} aria-hidden />}
          tone="secondary"
          label={`Thấp nhất · ${term} tháng · ${channelText}`}
          value={formatPercent(market.lowest)}
          hint={`Kém mức cao nhất ${formatNumber(market.highest && market.lowest !== null ? market.highest.rate - market.lowest : null)} điểm`}
          delta={monthDelta(spark.min, market.lowest)}
          trend={sparkOf(spark.min)}
        />
      </Grid>
      <Grid size={{ xs: 6, lg: 3 }}>
        <StatTile
          swapKey={channel}
          icon={<IconScale size={18} aria-hidden />}
          tone="success"
          label={`Lãi suất thực · trung vị ${channelText}`}
          value={real === null ? "—" : `${real > 0 ? "+" : ""}${formatPercent(real)}`}
          hint={cpi ? `Lạm phát ${formatMonth(cpi.month)}: ${formatPercent(cpi.yoyPercent)}` : "Chưa có số lạm phát"}
          delta={monthDelta(spark.real, real)}
          trend={sparkOf(spark.real)}
        />
      </Grid>
    </Grid>
  );
}

/**
 * Chuỗi cho sparkline: 3 tháng gần nhất của min/trung vị/max, cộng lãi suất thực = trung vị − lạm phát.
 * Lạm phát tháng chưa công bố lấy số tháng gần nhất đã có (giống cách tính ở thẻ KPI), để đường không đứt ở cuối.
 */
function buildSpark(points: RateTrendPoint[], cpiSeries: InflationPoint[]) {
  const kept = pick(points, indexesInDailyPreset(points.map((p) => p.date), SPARK_PRESET));
  const isoDates = kept.map((p) => p.date.slice(0, 10));
  const sortedCpi = [...cpiSeries].sort((a, b) => a.month.localeCompare(b.month));
  const byMonth = inflationByDate(isoDates, cpiSeries);
  const cpiAt = isoDates.map((d, i) => {
    if (byMonth[i] !== null) return byMonth[i];
    const earlier = sortedCpi.filter((p) => p.month <= d.slice(0, 7));
    return earlier.length ? earlier[earlier.length - 1].yoyPercent : null;
  });

  const latest = isoDates[isoDates.length - 1];
  const base = latest ? dailyPresetStart("1M", latest) : null;
  let baseIndex: number | null = null;
  if (base) {
    for (let i = 0; i < isoDates.length; i++) if (isoDates[i] <= base) baseIndex = i;
    if (baseIndex === null && isoDates.length > 0) baseIndex = 0;
  }

  return {
    dates: isoDates.map((d) => new Date(d)),
    min: kept.map((p) => p.min),
    median: kept.map((p) => p.median),
    max: kept.map((p) => p.max),
    real: kept.map((p, i) => realRate(p.median, cpiAt[i])),
    baseIndex,
    baseDate: baseIndex === null ? null : isoDates[baseIndex],
  };
}

function MarketTrendCard() {
  const [term, setTerm] = useState<number>(12);
  const [channel, setChannel] = useState<Channel>("ONLINE");
  const [period, setPeriod] = useState<DailyPreset>("1Y");
  const inflation = useInflation();
  const trend = useQuery({
    queryKey: queryKeys.rateTrend(term, channel),
    queryFn: () => marketRepository.rateTrend(term, channel),
    placeholderData: (previous) => previous,
  });

  const view = useMemo(() => {
    const points = trend.data ?? [];
    const kept = pick(points, indexesInDailyPreset(points.map((p) => p.date), period));
    return { points: kept, cpi: inflationByDate(kept.map((p) => p.date), inflation.data?.series ?? []) };
  }, [trend.data, period, inflation.data]);

  return (
    <SectionCard
      title="Diễn biến lãi suất thị trường"
      subtitle={`${term} tháng · ${CHANNEL_LABEL[channel].toLowerCase()} · so với lạm phát`}
      info="Trung vị và khoảng thấp nhất – cao nhất của các ngân hàng tại mỗi ngày có số liệu. Khoảng cách giữa đường lãi suất và đường lạm phát là lãi suất thực. Trước 2026 số liệu lấy theo các ngày lưu trữ nên thưa hơn."
      sx={{ height: "100%" }}
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap", rowGap: 1 }}>
        <ToggleGroup
          value={term}
          options={TREND_TERMS.map((t) => ({ value: t, label: `${t}T`, title: `${t} tháng` }))}
          onChange={setTerm}
          ariaLabel="Kỳ hạn"
        />
        <ToggleGroup
          value={channel}
          options={(["ONLINE", "COUNTER"] as Channel[]).map((c) => ({ value: c, label: CHANNEL_LABEL[c], title: CHANNEL_LABEL[c] }))}
          onChange={setChannel}
          ariaLabel="Kênh gửi"
        />
        <Box sx={{ flex: 1 }} />
        <PeriodToggle value={period} options={DAILY_PRESETS} onChange={setPeriod} />
      </Stack>
      {trend.isError ? (
        <ErrorState error={trend.error} onRetry={() => trend.refetch()} />
      ) : !trend.data ? (
        <LoadingBlock height={300} />
      ) : view.points.length === 0 ? (
        <EmptyState title="Chưa có số liệu cho kỳ hạn này" />
      ) : (
        <Box sx={{ opacity: trend.isPlaceholderData ? 0.5 : 1, transition: "opacity 150ms" }}>
          <RangeBandChart
            height={300}
            dates={view.points.map((p) => new Date(p.date))}
            min={view.points.map((p) => p.min)}
            median={view.points.map((p) => p.median)}
            max={view.points.map((p) => p.max)}
            reference={view.cpi.some((v) => v !== null) ? { label: "Lạm phát (CPI so cùng kỳ)", data: view.cpi } : undefined}
            formatValue={(v) => formatPercent(v)}
            formatDate={(d) =>
              d.toLocaleDateString("vi-VN", period === "1M" || period === "3M" ? { day: "2-digit", month: "2-digit" } : { month: "2-digit", year: "numeric" })
            }
            ariaLabel={`Diễn biến lãi suất ${term} tháng ${CHANNEL_LABEL[channel].toLowerCase()}: trung vị và khoảng thấp nhất đến cao nhất theo ngày, so với lạm phát`}
          />
        </Box>
      )}
    </SectionCard>
  );
}

/** Nhóm nút chọn một giá trị (dùng chung kiểu "pill" của PeriodToggle). */
function ToggleGroup<T extends string | number>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: { value: T; label: string; title: string }[];
  onChange: (value: T) => void;
  ariaLabel: string;
}) {
  return (
    <PeriodToggle
      value={String(value)}
      options={options.map((o) => ({ value: String(o.value), label: o.label, title: o.title }))}
      onChange={(v) => {
        const found = options.find((o) => String(o.value) === v);
        if (found) onChange(found.value);
      }}
      ariaLabel={ariaLabel}
    />
  );
}
