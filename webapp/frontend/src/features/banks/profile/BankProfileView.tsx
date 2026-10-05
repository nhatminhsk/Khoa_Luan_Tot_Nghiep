"use client";

import { Box, Button, Chip, Stack, Tab, Tabs, Typography } from "@mui/material";
import { IconArrowsLeftRight, IconBuildingBank } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BankAvatar } from "@/components/common/BankLabel";
import { Disclaimer } from "@/components/common/Disclaimer";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { WatchButton } from "@/features/watchlist/WatchButton";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import type { BankOwnership } from "@/types/api";
import { formatDate, formatPercent } from "@/utils/format";
import { AppPanel } from "./AppPanel";
import { ForecastPanel } from "./ForecastPanel";
import { IndicatorsPanel } from "./IndicatorsPanel";
import { ProgramsPanel } from "./ProgramsPanel";
import { RatesPanel } from "./RatesPanel";

const TABS = [
  { value: "indicators", label: "Chỉ tiêu tài chính" },
  { value: "rates", label: "Lãi suất" },
  { value: "forecast", label: "Dự báo" },
  { value: "app", label: "Ứng dụng" },
  { value: "programs", label: "Chương trình tín dụng" },
] as const;
type TabValue = (typeof TABS)[number]["value"];

export function BankProfileView({ ticker }: { ticker: string }) {
  const bank = useQuery({ queryKey: queryKeys.bank(ticker), queryFn: () => bankRepository.get(ticker) });
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const tabParam = searchParams.get("tab");
  const tab: TabValue = TABS.some((t) => t.value === tabParam) ? (tabParam as TabValue) : "indicators";

  if (bank.isError) return <ErrorState error={bank.error} onRetry={() => bank.refetch()} />;
  if (!bank.data) return <LoadingBlock height={160} />;

  const changeTab = (value: TabValue) =>
    router.replace(value === "indicators" ? pathname : `${pathname}?tab=${value}`, { scroll: false });

  return (
    <>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ alignItems: { xs: "flex-start", sm: "center" }, justifyContent: "space-between", mb: 2 }}
      >
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", minWidth: 0 }}>
          <BankAvatar ticker={bank.data.ticker} size={56} />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h1">{bank.data.shortName}</Typography>
            <Typography color="text.secondary">{bank.data.fullName}</Typography>
            <Stack direction="row" spacing={0.75} sx={{ mt: 0.75, flexWrap: "wrap", rowGap: 0.75 }} useFlexGap>
              <Chip size="small" label={`Mã ${bank.data.ticker}`} />
              {bank.data.appName && <Chip size="small" variant="outlined" label={`Ứng dụng: ${bank.data.appName}`} />}
              {bank.data.ownership && <OwnershipChips ownership={bank.data.ownership} />}
            </Stack>
          </Box>
        </Stack>
        <Stack direction="row" spacing={1}>
          <WatchButton ticker={bank.data.ticker} shortName={bank.data.shortName} />
          <Button
            component={Link}
            href={`/compare?tickers=${bank.data.ticker}`}
            variant="outlined"
            startIcon={<IconArrowsLeftRight size={18} />}
          >
            So sánh
          </Button>
        </Stack>
      </Stack>

      <Tabs
        value={tab}
        onChange={(_, value: TabValue) => changeTab(value)}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{ borderBottom: 1, borderColor: "divider", mb: 2.5 }}
      >
        {TABS.map((t) => (
          <Tab key={t.value} value={t.value} label={t.label} />
        ))}
      </Tabs>

      {tab === "indicators" && <IndicatorsPanel ticker={ticker} />}
      {tab === "rates" && <RatesPanel ticker={ticker} />}
      {tab === "forecast" && <ForecastPanel ticker={ticker} />}
      {tab === "app" && <AppPanel ticker={ticker} />}
      {tab === "programs" && <ProgramsPanel ticker={ticker} />}

      <Disclaimer />
    </>
  );
}

/**
 * Sở hữu nhà nước và nước ngoài. Với người gửi tiền, ngân hàng nhà nước chi phối (trên 50%) thường được xem là có
 * hậu thuẫn mạnh hơn; đây là thông tin tham khảo, không thay cho các chỉ tiêu an toàn.
 */
function OwnershipChips({ ownership }: { ownership: BankOwnership }) {
  const title = `Theo dữ liệu ngày ${formatDate(ownership.asOfDate)}`;
  const state = ownership.statePercent;
  return (
    <>
      {state !== null && (
        <Chip
          size="small"
          variant="outlined"
          color={state >= 50 ? "primary" : "default"}
          icon={<IconBuildingBank size={14} aria-hidden />}
          title={title}
          label={
            state >= 50
              ? `Nhà nước chi phối · ${formatShare(state)}`
              : state > 0
                ? `Có vốn nhà nước · ${formatShare(state)}`
                : "Không có vốn nhà nước"
          }
        />
      )}
      {ownership.foreignPercent !== null && (
        <Chip size="small" variant="outlined" title={title} label={`Nước ngoài sở hữu ${formatShare(ownership.foreignPercent)}`} />
      )}
    </>
  );
}

/** Tỷ lệ sở hữu 1 chữ số thập phân; tỷ lệ dương rất nhỏ (ví dụ 0,004%) ghi "dưới 0,1%" thay vì "0,0%". */
function formatShare(percent: number): string {
  return percent > 0 && percent < 0.1 ? "dưới 0,1%" : formatPercent(percent, 1);
}
