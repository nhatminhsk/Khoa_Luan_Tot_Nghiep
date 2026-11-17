"use client";

import { Box, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import { IconArrowDownRight, IconArrowUpRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { BankAvatar } from "@/components/common/BankLabel";
import { PeriodToggle } from "@/components/common/PeriodToggle";
import { SectionCard } from "@/components/common/SectionCard";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import type { RateChange } from "@/types/api";
import { formatDate, formatDelta, formatPercent } from "@/utils/format";
import { CHANNEL_LABEL } from "@/utils/labels";

export const CHANGE_WINDOWS = [
  { value: "30", label: "30 ngày", title: "30 ngày gần nhất" },
  { value: "90", label: "90 ngày", title: "90 ngày gần nhất" },
];
const COLLAPSED_GROUPS = 4;

interface Group {
  key: string;
  date: string;
  ticker: string;
  shortName: string;
  channel: RateChange["channel"];
  items: RateChange[];
}

/**
 * Dòng "Biến động gần đây": các lần ngân hàng đổi lãi suất, gom theo ngày × ngân hàng × kênh.
 * Không cố định 7 ngày: nguồn có thể đứng yên nhiều tuần, nên chọn 30/90 ngày và luôn nói rõ lần đổi gần nhất là khi nào.
 */
export function RecentChangesCard() {
  const [days, setDays] = useState("30");
  const [expanded, setExpanded] = useState(false);
  const query = useQuery({
    queryKey: queryKeys.rateChanges(Number(days)),
    queryFn: () => marketRepository.rateChanges(Number(days)),
    placeholderData: (previous) => previous,
  });

  const changes = query.data?.changes ?? [];
  const groups = groupChanges(changes);
  const shown = expanded ? groups : groups.slice(0, COLLAPSED_GROUPS);
  const ups = changes.filter((c) => c.change > 0).length;
  const banks = new Set(changes.map((c) => c.ticker)).size;

  return (
    <SectionCard
      title="Biến động gần đây"
      subtitle="Ngân hàng vừa đổi lãi suất niêm yết"
      info="Mỗi thay đổi so với lần có số liệu liền trước của cùng ngân hàng, kỳ hạn và kênh. Ngày không có số liệu không tạo ra thay đổi giả."
    >
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !query.data ? (
        <LoadingBlock height={360} />
      ) : (
        <Box sx={{ opacity: query.isPlaceholderData ? 0.5 : 1, transition: "opacity 150ms" }}>
          <Box sx={{ mb: 1.5 }}>
            <PeriodToggle
              value={days}
              options={CHANGE_WINDOWS}
              onChange={(v) => {
                setDays(v);
                setExpanded(false);
              }}
              ariaLabel="Khoảng thời gian"
            />
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {changes.length === 0 ? (
              <>Không ngân hàng nào đổi lãi suất trong {days} ngày tính tới {formatDate(query.data.latestDate)}.</>
            ) : (
              <>
                <Box component="strong" sx={{ color: "text.primary" }}>
                  {changes.length} thay đổi
                </Box>{" "}
                ở {banks} ngân hàng ({ups} tăng, {changes.length - ups} giảm). Lần gần nhất: {formatDate(changes[0].date)}.
              </>
            )}
          </Typography>
          <Stack spacing={0} component="ol" sx={{ listStyle: "none", m: 0, p: 0 }}>
            {shown.map((g) => (
              <GroupRow key={g.key} group={g} />
            ))}
          </Stack>
          {groups.length > COLLAPSED_GROUPS && (
            <Button size="small" onClick={() => setExpanded((v) => !v)} sx={{ mt: 1 }}>
              {expanded ? "Thu gọn" : `Xem thêm ${groups.length - COLLAPSED_GROUPS} mục`}
            </Button>
          )}
        </Box>
      )}
    </SectionCard>
  );
}

function GroupRow({ group }: { group: Group }) {
  return (
    <Stack
      component="li"
      direction="row"
      spacing={1.25}
      sx={{ py: 1.25, borderTop: 1, borderColor: "divider", "&:first-of-type": { borderTop: 0, pt: 0.25 } }}
    >
      <BankAvatar ticker={group.ticker} size={30} />
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "baseline" }}>
          <Typography variant="body2" sx={{ fontWeight: 600, minWidth: 0 }} noWrap>
            <MuiLink component={Link} href={`/banks/${group.ticker}`} underline="hover" color="inherit">
              {group.shortName}
            </MuiLink>{" "}
            <Box component="span" sx={{ color: "text.secondary", fontWeight: 400 }}>
              · {CHANNEL_LABEL[group.channel].toLowerCase()}
            </Box>
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
            {formatDate(group.date)}
          </Typography>
        </Stack>
        <Stack direction="row" sx={{ flexWrap: "wrap", columnGap: 1.25, rowGap: 0.25, mt: 0.25 }}>
          {group.items.map((c) => (
            <TermDelta key={c.termMonths} change={c} />
          ))}
        </Stack>
      </Box>
    </Stack>
  );
}

/** "12T ↗ +0,30" — mũi tên và dấu mang hướng, màu chỉ là phụ. */
function TermDelta({ change }: { change: RateChange }) {
  const up = change.change > 0;
  const Arrow = up ? IconArrowUpRight : IconArrowDownRight;
  return (
    <Box
      component="span"
      title={`${change.termMonths} tháng: ${formatPercent(change.previousRate)} → ${formatPercent(change.rate)} (so với ${formatDate(change.previousDate)})`}
      sx={{ display: "inline-flex", alignItems: "center", gap: 0.25, fontSize: "0.75rem", fontVariantNumeric: "tabular-nums" }}
    >
      <Box component="span" sx={{ color: "text.secondary" }}>
        {change.termMonths}T
      </Box>
      <Box component="span" sx={{ display: "inline-flex", alignItems: "center", color: up ? "success.main" : "error.main", fontWeight: 600 }}>
        <Arrow size={13} stroke={2.2} aria-hidden />
        {formatDelta(change.change)}
      </Box>
    </Box>
  );
}

function groupChanges(changes: RateChange[]): Group[] {
  const groups = new Map<string, Group>();
  for (const c of changes) {
    const key = `${c.date}|${c.ticker}|${c.channel}`;
    let g = groups.get(key);
    if (!g) {
      g = { key, date: c.date, ticker: c.ticker, shortName: c.shortName, channel: c.channel, items: [] };
      groups.set(key, g);
    }
    g.items.push(c);
  }
  // API đã sắp ngày mới nhất trước; trong một nhóm xếp kỳ hạn tăng dần.
  return [...groups.values()].map((g) => ({ ...g, items: [...g.items].sort((a, b) => a.termMonths - b.termMonths) }));
}
