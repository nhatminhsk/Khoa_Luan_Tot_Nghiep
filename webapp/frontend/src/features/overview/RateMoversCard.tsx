"use client";

import { Box, Button, Link as MuiLink, Stack, Tooltip, Typography, type SxProps, type Theme } from "@mui/material";
import { IconArrowDownRight, IconArrowUpRight, IconMinus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { BankAvatar } from "@/components/common/BankLabel";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { Channel } from "@/types/api";
import { formatDate, formatDelta, formatPercent } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";
import { CHANGE_WINDOWS } from "./RecentChangesCard";

const TERMS = ["6", "12", "24"] as const;
/** Mặc định chỉ hiện chừng này ngân hàng tăng mạnh nhất và chừng này giảm mạnh nhất; số đếm vẫn tính cả danh sách. */
const COLLAPSED_EACH = 3;

interface Mover {
  ticker: string;
  shortName: string;
  from: number;
  to: number;
  change: number;
  firstDate: string;
  lastDate: string;
  times: number;
}

/**
 * Ngân hàng tăng/giảm lãi nhiều nhất trong 30/90 ngày ở một kỳ hạn: thanh phân kỳ quanh mốc 0
 * (tăng sang phải, giảm sang trái), số có dấu ở đầu thanh. Mức thay đổi ròng = tổng các lần đổi trong khoảng.
 */
export function RateMoversCard({ compact = false }: { compact?: boolean }) {
  const [days, setDays] = useState("30");
  const [term, setTerm] = useState<(typeof TERMS)[number]>("12");
  const [channel, setChannel] = useState<Channel>("ONLINE");
  const [expanded, setExpanded] = useState(false);
  const changes = useQuery({
    queryKey: queryKeys.rateChanges(Number(days)),
    queryFn: () => marketRepository.rateChanges(Number(days)),
    placeholderData: (previous) => previous,
  });
  const table = useQuery({ queryKey: queryKeys.depositTable(channel), queryFn: () => marketRepository.depositTable(channel) });

  const movers = useMemo<Mover[]>(() => {
    const byBank = new Map<string, Mover>();
    // API trả mới nhất trước; duyệt ngược để lần đổi đầu tiên trong khoảng đứng trước.
    for (const c of [...(changes.data?.changes ?? [])].reverse()) {
      if (String(c.termMonths) !== term || c.channel !== channel) continue;
      const m = byBank.get(c.ticker);
      if (!m) {
        byBank.set(c.ticker, {
          ticker: c.ticker,
          shortName: c.shortName,
          from: c.previousRate,
          to: c.rate,
          change: c.change,
          firstDate: c.date,
          lastDate: c.date,
          times: 1,
        });
      } else {
        m.to = c.rate;
        m.change = Math.round((m.change + c.change) * 100) / 100;
        m.lastDate = c.date;
        m.times += 1;
      }
    }
    return [...byBank.values()].filter((m) => m.change !== 0).sort((a, b) => b.change - a.change);
  }, [changes.data, term, channel]);

  const quoting = (table.data?.rows ?? []).filter((r) => r.cells[term]).length;
  const ups = movers.filter((m) => m.change > 0).length;
  const downs = movers.length - ups;
  // Thang thanh tính trên cả danh sách, nên mở rộng hay thu gọn thì độ dài thanh không đổi.
  const maxAbs = Math.max(...movers.map((m) => Math.abs(m.change)), 0.01);
  // movers sắp giảm dần: tăng mạnh nhất ở đầu, giảm mạnh nhất ở cuối.
  const visible = expanded
    ? movers
    : [...movers.filter((m) => m.change > 0).slice(0, COLLAPSED_EACH), ...movers.filter((m) => m.change < 0).slice(-COLLAPSED_EACH)];

  return (
    <SectionCard
      title="Tăng/giảm lãi nhiều nhất"
      subtitle={`Kỳ hạn ${term} tháng · ${CHANNEL_LABEL[channel].toLowerCase()} · ${days} ngày gần nhất`}
      info="Mức thay đổi ròng trong khoảng thời gian = lãi hiện tại trừ lãi trước lần đổi đầu tiên trong khoảng. Rê chuột lên thanh để xem mức cũ, mức mới và số lần đổi."
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap", rowGap: 1 }}>
        <PeriodToggle
          value={term}
          options={TERMS.map((t) => ({ value: t, label: `${t}T`, title: `${t} tháng` }))}
          onChange={setTerm}
          ariaLabel="Kỳ hạn"
        />
        <PeriodToggle
          value={channel}
          options={(["ONLINE", "COUNTER"] as Channel[]).map((c) => ({ value: c, label: CHANNEL_LABEL[c], title: CHANNEL_LABEL[c] }))}
          onChange={setChannel}
          ariaLabel="Kênh gửi"
        />
        <Box sx={{ flex: 1 }} />
        <PeriodToggle value={days} options={CHANGE_WINDOWS} onChange={setDays} ariaLabel="Khoảng thời gian" />
      </Stack>

      {changes.isError ? (
        <ErrorState error={changes.error} onRetry={() => changes.refetch()} />
      ) : !changes.data ? (
        <LoadingBlock height={300} />
      ) : (
        <Box sx={{ opacity: changes.isPlaceholderData ? 0.5 : 1, transition: "opacity 150ms" }}>
          <Stack direction="row" spacing={2.5} sx={{ mb: 1.5, flexWrap: "wrap", rowGap: 0.5 }}>
            <Count icon={<IconArrowUpRight size={16} />} color="success.main" label={`${ups} tăng`} />
            <Count icon={<IconArrowDownRight size={16} />} color="error.main" label={`${downs} giảm`} />
            <Count
              icon={<IconMinus size={16} />}
              color="text.secondary"
              label={`${Math.max(quoting - movers.length, 0)} giữ nguyên`}
            />
          </Stack>
          {movers.length === 0 ? (
            <EmptyState
              title="Không ngân hàng nào đổi lãi kỳ hạn này"
              description={`Trong ${days} ngày tính tới ${formatDate(changes.data.latestDate)}. Thử khoảng 90 ngày hoặc kỳ hạn khác.`}
            />
          ) : (
            <>
              <Stack spacing={1} role="list" aria-label="Mức thay đổi lãi suất theo ngân hàng">
                {visible.map((m) => (
                  <MoverRow key={m.ticker} mover={m} maxAbs={maxAbs} compact={compact} />
                ))}
              </Stack>
              {movers.length > visible.length || expanded ? (
                <Button size="small" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded} sx={{ mt: 1, ml: -1 }}>
                  {expanded ? "Thu gọn" : `Xem tất cả ${movers.length} ngân hàng`}
                </Button>
              ) : null}
            </>
          )}
        </Box>
      )}
    </SectionCard>
  );
}

function Count({ icon, color, label }: { icon: React.ReactNode; color: string; label: string }) {
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", color }}>
      {icon}
      <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>
        {label}
      </Typography>
    </Stack>
  );
}

/** Một hàng: tên ngân hàng | nửa trái (giảm) · mốc 0 · nửa phải (tăng). Số in ngoài đầu thanh. */
function MoverRow({ mover, maxAbs, compact }: { mover: Mover; maxAbs: number; compact: boolean }) {
  const up = mover.change > 0;
  const pct = (Math.abs(mover.change) / maxAbs) * 100;
  const label = `${formatDelta(mover.change)} điểm`;
  const tip = `${mover.shortName}: ${formatPercent(mover.from)} → ${formatPercent(mover.to)} · đổi ${mover.times} lần (${
    mover.firstDate === mover.lastDate ? formatDate(mover.lastDate) : `${formatDate(mover.firstDate)} – ${formatDate(mover.lastDate)}`
  })`;

  return (
    <Tooltip title={tip} placement="top">
      {/* Điện thoại: tên ngân hàng một dòng riêng phía trên thanh (cạnh nhau thì tên bị cắt và thanh còn rất ngắn). */}
      <Stack
        role="listitem"
        direction={compact ? "column" : { xs: "column", sm: "row" }}
        spacing={compact ? 0.25 : { xs: 0.25, sm: 1.5 }}
        sx={{ alignItems: compact ? "stretch" : { xs: "stretch", sm: "center" }, minHeight: 30 }}
        aria-label={`${tip}, ${label}`}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", width: compact ? "auto" : { xs: "auto", sm: 150 }, flexShrink: 0, minWidth: 0 }}>
          <BankAvatar ticker={mover.ticker} size={26} />
          <MuiLink
            component={Link}
            href={`/banks/${mover.ticker}`}
            underline="hover"
            color="text.primary"
            variant="body2"
            sx={{ fontWeight: 600 }}
            noWrap
          >
            {mover.shortName}
          </MuiLink>
        </Stack>
        <Box sx={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1px 1fr", alignItems: "center", minWidth: 0, minHeight: 26 }}>
          {/* Mỗi nửa là một "đường ray" chừa 52px cho số; thanh dài theo tỉ lệ trên ray, số đặt ngay đầu thanh. */}
          <Box sx={{ position: "relative", height: 16, ml: "52px" }}>
            {!up && (
              <>
                <Box sx={{ position: "absolute", right: 0, top: 0, bottom: 0, width: `${pct}%`, bgcolor: "error.main", borderRadius: "4px 0 0 4px" }} />
                <DeltaText value={mover.change} sx={{ right: `calc(${pct}% + 6px)` }} />
              </>
            )}
          </Box>
          <Box sx={{ height: 26, bgcolor: "divider" }} aria-hidden />
          <Box sx={{ position: "relative", height: 16, mr: "52px" }}>
            {up && (
              <>
                <Box sx={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${pct}%`, bgcolor: "success.main", borderRadius: "0 4px 4px 0" }} />
                <DeltaText value={mover.change} sx={{ left: `calc(${pct}% + 6px)` }} />
              </>
            )}
          </Box>
        </Box>
      </Stack>
    </Tooltip>
  );
}

function DeltaText({ value, sx }: { value: number; sx: SxProps<Theme> }) {
  return (
    <Typography
      variant="caption"
      sx={[
        { position: "absolute", top: "50%", transform: "translateY(-50%)", fontWeight: 700, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {formatDelta(value)}
    </Typography>
  );
}
