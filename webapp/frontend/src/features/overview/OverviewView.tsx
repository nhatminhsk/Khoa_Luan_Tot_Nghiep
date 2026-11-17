"use client";

import { Box, Chip, Grid, IconButton, Stack, Tab, Tabs, ToggleButton, ToggleButtonGroup, Tooltip, Typography, useMediaQuery, useTheme } from "@mui/material";
import {
  IconArrowsUpDown,
  IconHomeDollar,
  IconPigMoney,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
  IconScale,
  IconShieldCheck,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { RangeBandChart } from "@/components/charts/RangeBandChart";
import { Disclaimer } from "@/components/common/Disclaimer";
import { PageHeader } from "@/components/common/PageHeader";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { PillarCard } from "@/components/common/PillarCard";
import { EmptyState, ErrorState, LoadingBlock, PendingResult } from "@/components/common/States";
import { SectionCard } from "@/components/common/SectionCard";
import { PENDING_BOTH, RankingSection } from "@/components/domain/RankingSection";
import { HealthMatrixCard } from "@/features/overview/HealthMatrixCard";
import { LendingRatesCard } from "@/features/overview/LendingRatesCard";
import { RateHeatmapCard } from "@/features/overview/RateHeatmapCard";
import { RateMoversCard } from "@/features/overview/RateMoversCard";
import { RateSafetyScatterCard } from "@/features/overview/RateSafetyScatterCard";
import { RecentChangesCard } from "@/features/overview/RecentChangesCard";
import { TopRatesCard } from "@/features/overview/TopRatesCard";
import { WatchlistWidget } from "@/features/overview/WatchlistWidget";
import { useInflation } from "@/hooks/use-inflation";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { Channel, IndicatorComparison, InflationPoint, LendingRate, MarketSummary, Purpose, RateTrendPoint } from "@/types/api";
import { formatDate, formatMonth, formatPercent, formatQuarter } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";
import { DAILY_PRESETS, type DailyPreset, dailyPresetStart, indexesInDailyPreset, pick } from "@/utils/period-presets";
import { isComparableLending, latestMonthOf } from "@/utils/lending";
import { inflationByDate, realRate } from "@/utils/real-rate";

const TREND_TERMS = [6, 12, 24] as const;
/** Sparkline trong thẻ KPI: 3 tháng gần nhất; thay đổi so với mốc 1 tháng trước. */
const SPARK_PRESET: DailyPreset = "3M";
const KPI_CHANNELS: Channel[] = ["ONLINE", "COUNTER"];
/** Thẻ KPI tự chuyển giữa hai kênh sau mỗi khoảng này (đủ để đọc con số; rê chuột để dừng xem sparkline). */
const KPI_ROTATE_MS = 5000;
/** Cặp thẻ ở cột phải: xếp chồng khi đứng cạnh thẻ lớn (lg+) hoặc trên điện thoại; iPad ngang (md) đặt cạnh nhau cho đỡ thưa. */
const PAIR_DIRECTION = { xs: "column", md: "row", lg: "column" } as const;
const PAIR_SX = { "& > *": { flex: 1, minWidth: 0 } } as const;
/** Mã bất kỳ để gọi endpoint so sánh chỉ lấy chuỗi trung vị ngành (endpoint cần ít nhất một ngân hàng). */
const MEDIAN_PROBE = "VCB";

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
        description="Theo dõi lãi gửi, lãi vay bình quân ngân hàng công bố và chỉ tiêu tài chính của 22 ngân hàng."
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

      {/* Bố cục (lg+, 12 cột): dải 4 thẻ trụ → diễn biến lãi gửi | Top gửi + lãi vay → ma trận chỉ tiêu tài chính | tăng/giảm +
          biến động → bản đồ lãi gửi → lãi gửi × chỉ tiêu | theo dõi + xếp hạng. Thẻ phụ cao theo nội dung (không kéo giãn lấp chỗ).
          Điện thoại: thẻ trụ → Top gửi → lãi vay → biểu đồ → ma trận (order). */}
      <Grid container spacing={2}>
        <Grid size={12}>
          <Box {...kpi.pauseHandlers}>
            <PillarRow market={market} channel={kpi.channel} hasCounter={hasCounter} />
          </Box>
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }} sx={{ order: { xs: 2, lg: 1 } }}>
          <MarketTrendCard />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }} sx={{ order: { xs: 1, lg: 2 } }}>
          <Stack direction={PAIR_DIRECTION} spacing={2} sx={PAIR_SX}>
            {/* Cùng kênh với thẻ trụ Gửi tiết kiệm (tự chuyển, ghim, tạm dừng khi rê chuột hoặc focus). */}
            <Box {...kpi.pauseHandlers}>
              <TopRatesCard channel={kpi.channel} limit={3} />
            </Box>
            <LendingRatesCard />
          </Stack>
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }} sx={{ order: 3 }}>
          <HealthMatrixCard />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }} sx={{ order: 4 }}>
          <Stack direction={PAIR_DIRECTION} spacing={2} sx={PAIR_SX}>
            <RateMoversCard compact />
            <RecentChangesCard />
          </Stack>
        </Grid>

        <Grid size={12} sx={{ order: 5 }}>
          <RateHeatmapCard />
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }} sx={{ order: 6 }}>
          <RateSafetyScatterCard />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }} sx={{ order: 7 }}>
          <Stack direction={PAIR_DIRECTION} spacing={2} sx={PAIR_SX}>
            <WatchlistWidget />
            <SectionCard title="Xếp hạng tổng hợp" subtitle="Năm ngân hàng đứng đầu: gửi 12 tháng trực tuyến (trọng số mặc định) và vay">
              {/* Cả hai chưa có kết quả: một thông báo chung, không để hai tab hiện cùng một nội dung chờ. */}
              {data?.savingsRanking.status === "NOT_AVAILABLE" && data.loanRanking.status === "NOT_AVAILABLE" ? (
                <PendingResult title="Chưa có kết quả xếp hạng" description={PENDING_BOTH} compact />
              ) : (
                <>
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
                </>
              )}
            </SectionCard>
          </Stack>
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
    /** Rê chuột hoặc focus bàn phím vào khối thì tạm dừng; rời khỏi (focus ra ngoài khối) thì chạy tiếp. */
    pauseHandlers: {
      onMouseEnter: () => setPaused(true),
      onMouseLeave: () => setPaused(false),
      onFocus: () => setPaused(true),
      onBlur: (e: React.FocusEvent<HTMLElement>) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setPaused(false);
      },
    },
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
      <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5, fontWeight: 600 }}>
        Kênh gửi
      </Typography>
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
 * Dải KPI theo bốn trụ: Gửi tiết kiệm (kỳ hạn tham chiếu 12 tháng, kênh tự chuyển), Vay (lãi cho vay bình quân khách hàng cá
 * nhân do ngân hàng công bố), Sức khỏe (trung vị ngành quý mới nhất) và Vĩ mô (lạm phát, lãi thực).
 * Lãi gửi hôm nay lấy từ /overview; sparkline và mức thay đổi 1 tháng lấy từ chuỗi diễn biến cùng kỳ hạn và kênh (tải sẵn cả hai
 * kênh để lúc chuyển kênh sparkline không trống). Thẻ giữ nguyên khi đổi kênh, chỉ phần số hiện dần (swapKey).
 */
function PillarRow({ market, channel, hasCounter }: { market: MarketSummary | undefined; channel: Channel; hasCounter: boolean }) {
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
  const lending = useQuery({ queryKey: queryKeys.lendingRates, queryFn: marketRepository.lendingRates });
  // Trung vị ngành theo quý: endpoint so sánh luôn trả kèm chuỗi trung vị mọi ngân hàng, mã ngân hàng truyền vào không ảnh hưởng.
  const npl = useQuery({
    queryKey: queryKeys.indicatorComparison("npl", [MEDIAN_PROBE]),
    queryFn: () => marketRepository.indicatorComparison("npl", [MEDIAN_PROBE]),
  });
  const car = useQuery({
    queryKey: queryKeys.indicatorComparison("car", [MEDIAN_PROBE]),
    queryFn: () => marketRepository.indicatorComparison("car", [MEDIAN_PROBE]),
  });

  const spark = useMemo(() => buildSpark(trend.data ?? [], inflation.data?.series ?? []), [trend.data, inflation.data]);

  if (!market) {
    return (
      <Grid container spacing={{ xs: 1.5, sm: 2 }}>
        {[0, 1, 2, 3].map((i) => (
          <Grid key={i} size={{ xs: 12, sm: 6, lg: 3 }}>
            <LoadingBlock height={168} />
          </Grid>
        ))}
      </Grid>
    );
  }

  const fmtDate = (d: Date) => formatDate(d.toISOString().slice(0, 10));
  const monthDelta = (values: (number | null)[], today: number | null) => ({
    value: today === null || spark.baseIndex === null || values[spark.baseIndex] === null ? null : today - (values[spark.baseIndex] as number),
    unit: " điểm %",
    title: spark.baseDate ? `So với ${formatDate(spark.baseDate)}` : undefined,
  });
  const median = spark.dates.flatMap((d, i) => (spark.median[i] === null ? [] : [{ d, v: spark.median[i] as number }]));
  const real = realRate(market.median, cpi?.yoyPercent);
  const channelText = CHANNEL_LABEL[channel].toLowerCase();

  // Vay: chỉ số khách hàng cá nhân do chính ngân hàng công bố (cùng loại, so ngang được); mỗi ngân hàng tháng mới nhất.
  const lendingLatest = latestMonthOf(lending.data ?? []);
  const individual = (lending.data ?? []).filter((r) => isComparableLending(r, lendingLatest));
  const cheapest = individual.reduce<LendingRate | null>((m, r) => (m === null || r.lendingAvgPercent < m.lendingAvgPercent ? r : m), null);
  const lendingMedian = medianOf(individual.map((r) => r.lendingAvgPercent));

  const nplH = industryMedian(npl.data);
  const carH = industryMedian(car.data);
  const cpiSeries = [...(inflation.data?.series ?? [])].sort((a, b) => a.month.localeCompare(b.month)).slice(-12);
  const cpiPrev = cpiSeries.length > 1 ? cpiSeries[cpiSeries.length - 2].yoyPercent : null;

  return (
    <Grid container spacing={{ xs: 1.5, sm: 2 }}>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <PillarCard
          tone="deposit"
          icon={<IconPigMoney size={16} />}
          title="Gửi tiết kiệm"
          scope={`Kỳ hạn ${term} tháng · ${channelText}${spark.baseDate ? ` · thay đổi so với ${formatDate(spark.baseDate)}` : ""}`}
          swapKey={channel}
          href={`/savings?term=${term}&channel=${channel}`}
          metrics={[
            {
              label: "Cao nhất",
              value: formatPercent(market.highest?.rate),
              delta: monthDelta(spark.max, market.highest?.rate ?? null),
              hint: market.highest
                ? market.highest.tiedCount > 0
                  ? `${market.highest.shortName} +${market.highest.tiedCount}`
                  : market.highest.shortName
                : undefined,
            },
            {
              label: `Trung vị ${market.banksQuoted} NH`,
              value: formatPercent(market.median),
              delta: monthDelta(spark.median, market.median),
              hint: `Thấp nhất ${formatPercent(market.lowest)}`,
            },
          ]}
          trend={{
            values: median.map((m) => m.v),
            dates: median.map((m) => m.d),
            format: (v) => formatPercent(v),
            formatDate: fmtDate,
            curve: "stepAfter",
            label: `Trung vị lãi ${term} tháng ${channelText} 3 tháng gần nhất`,
          }}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <PillarCard
          tone="loan"
          icon={<IconHomeDollar size={16} />}
          title="Vay"
          scope="Lãi cho vay bình quân KH cá nhân, NH tự công bố"
          href="/loans"
          metrics={[
            {
              label: "Bình quân thấp nhất",
              value: lending.isLoading ? "…" : formatPercent(cheapest?.lendingAvgPercent),
              hint: cheapest ? `${cheapest.shortName} · ${formatMonth(cheapest.month)}` : lending.isError ? "Không tải được" : undefined,
            },
            {
              label: individual.length ? `Trung vị ${individual.length} NH` : "Trung vị",
              value: lending.isLoading ? "…" : formatPercent(lendingMedian),
              hint: "Khác tháng, cơ sở tính",
            },
          ]}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <PillarCard
          tone="health"
          icon={<IconShieldCheck size={16} />}
          title="Chỉ tiêu tài chính"
          scope={nplH.last ? `Trung vị các NH có dữ liệu · ${formatQuarter(nplH.last.p)}` : "Trung vị các NH có dữ liệu"}
          href="/banks"
          metrics={[
            {
              label: "Nợ xấu",
              value: npl.isLoading ? "…" : npl.isError ? "Lỗi tải" : formatPercent(nplH.last?.v),
              delta: { value: nplH.yoy, unit: " điểm %", direction: "down-good", title: "So với cùng quý năm trước" },
              hint: nplH.last ? `so ${formatQuarter(shiftYear(nplH.last.p))}` : undefined,
            },
            {
              label: "Hệ số an toàn vốn",
              value: car.isLoading ? "…" : car.isError ? "Lỗi tải" : formatPercent(carH.last?.v),
              delta: { value: carH.yoy, unit: " điểm %", direction: "up-good", title: "So với cùng quý năm trước" },
              // CAR nhiều ngân hàng công bố bán niên: quý mới nhất của CAR có thể khác của nợ xấu.
              hint: carH.last
                ? carH.last.p !== nplH.last?.p
                  ? `${formatQuarter(carH.last.p)} · so ${formatQuarter(shiftYear(carH.last.p))}`
                  : `so ${formatQuarter(shiftYear(carH.last.p))}`
                : undefined,
            },
          ]}
          trend={{
            values: nplH.series.slice(-12).map((s) => s.v),
            labels: nplH.series.slice(-12).map((s) => formatQuarter(s.p)),
            format: (v) => `Nợ xấu ${formatPercent(v)}`,
            label: "Trung vị nợ xấu các ngân hàng 12 quý gần nhất",
          }}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
        <PillarCard
          tone="macro"
          icon={<IconScale size={16} />}
          title="Vĩ mô"
          scope={cpi ? `CPI so cùng kỳ · ${formatMonth(cpi.month)}` : "CPI so cùng kỳ"}
          swapKey={channel}
          href="/methodology"
          linkLabel="Nguồn"
          metrics={[
            {
              label: "Lạm phát",
              value: inflation.isLoading ? "…" : formatPercent(cpi?.yoyPercent),
              delta: {
                value: cpi && cpiPrev !== null ? cpi.yoyPercent - cpiPrev : null,
                unit: " điểm %",
                direction: "neutral",
                title: "So với tháng trước",
              },
              hint: "CPI, TCTK",
            },
            {
              label: "Lãi thực tham chiếu",
              value: real === null ? "—" : `${real > 0 ? "+" : ""}${formatPercent(real)}`,
              hint: `Trung vị ${term}T ${channelText} trừ CPI`,
            },
          ]}
          trend={{
            values: cpiSeries.map((p) => p.yoyPercent),
            labels: cpiSeries.map((p) => formatMonth(p.month)),
            format: (v) => `Lạm phát ${formatPercent(v)}`,
            label: "Lạm phát so cùng kỳ 12 tháng gần nhất",
          }}
        />
      </Grid>
    </Grid>
  );
}

/** Chuỗi trung vị ngành theo quý từ endpoint so sánh, quý mới nhất và mức thay đổi so với cùng quý năm trước. */
function industryMedian(data: IndicatorComparison | undefined) {
  const series = (data?.periods ?? []).flatMap((p, i) => (data!.median[i] === null ? [] : [{ p, v: data!.median[i] as number }]));
  const last = series.length > 0 ? series[series.length - 1] : undefined;
  const yearAgo = last ? series.find((s) => s.p === shiftYear(last.p)) : undefined;
  return { series, last, yoy: last && yearAgo ? last.v - yearAgo.v : null };
}

/** "2026-Q2" → "2025-Q2". */
function shiftYear(period: string): string {
  return period.replace(/^(\d{4})/, (y) => String(Number(y) - 1));
}

function medianOf(values: number[]): number | null {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
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
  // Từ lg thẻ đứng cạnh cột Top gửi + lãi vay (cao hơn): biểu đồ cao thêm để lấp thẻ thay vì để trống phần dưới.
  const wide = useMediaQuery(useTheme().breakpoints.up("lg"));
  const chartHeight = wide ? 420 : 300;
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
        <LoadingBlock height={chartHeight} />
      ) : view.points.length === 0 ? (
        <EmptyState title="Chưa có số liệu cho kỳ hạn này" />
      ) : (
        <Box sx={{ opacity: trend.isPlaceholderData ? 0.5 : 1, transition: "opacity 150ms" }}>
          <RangeBandChart
            height={chartHeight}
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
