"use client";

import { Box, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import { IconArrowRight, IconBell, IconLogin } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { BankAvatar } from "@/components/common/BankLabel";
import { RateDelta } from "@/components/common/RateDelta";
import { SectionCard } from "@/components/common/SectionCard";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { useAuth } from "@/hooks/use-auth";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";
import { formatNumber, formatPercent } from "@/utils/format";

const MAX_ROWS = 7;

/**
 * Khung "Ngân hàng bạn theo dõi" trên trang Tổng quan: lãi 12 tháng trực tuyến hiện tại và thay đổi so với hôm trước.
 * Chưa đăng nhập thì hiện lời mời đăng nhập (trang này xem được không cần tài khoản).
 */
export function WatchlistWidget() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <SectionCard
      title="Ngân hàng bạn theo dõi"
      subtitle="Lãi 12 tháng trực tuyến · so với hôm trước"
      action={
        isAuthenticated ? (
          <Button component={Link} href="/watchlist" size="small" endIcon={<IconArrowRight size={16} />} sx={{ minHeight: 32 }}>
            Quản lý
          </Button>
        ) : undefined
      }
      sx={{ height: "100%" }}
    >
      {isLoading ? <LoadingBlock height={260} /> : isAuthenticated ? <WatchList /> : <SignInPrompt />}
    </SectionCard>
  );
}

function WatchList() {
  const watchlist = useQuery({ queryKey: queryKeys.watchlist, queryFn: meRepository.watchlist });

  if (watchlist.isError) return <ErrorState error={watchlist.error} onRetry={() => watchlist.refetch()} />;
  if (!watchlist.data) return <LoadingBlock height={260} />;
  if (watchlist.data.length === 0) {
    return (
      <Prompt
        text="Chưa theo dõi ngân hàng nào. Thêm ngân hàng để nhận báo khi lãi suất thay đổi."
        action={
          <Button component={Link} href="/watchlist" variant="contained" size="small" startIcon={<IconBell size={16} />}>
            Thêm ngân hàng
          </Button>
        }
      />
    );
  }

  const items = [...watchlist.data].sort((a, b) => (b.rate12mOnline ?? -1) - (a.rate12mOnline ?? -1));
  const shown = items.slice(0, MAX_ROWS);

  return (
    <Stack spacing={0.5}>
      {shown.map((item) => (
        <Stack
          key={item.ticker}
          direction="row"
          spacing={1.25}
          sx={{ alignItems: "center", py: 0.75, borderBottom: 1, borderColor: "divider", "&:last-of-type": { borderBottom: 0 } }}
        >
          <BankAvatar ticker={item.ticker} size={30} />
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <MuiLink
              component={Link}
              href={`/banks/${item.ticker}`}
              underline="hover"
              color="text.primary"
              variant="body2"
              sx={{ fontWeight: 600, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
            >
              {item.shortName}
            </MuiLink>
            <Typography variant="caption" color="text.secondary">
              Báo khi đổi ≥ {formatNumber(item.rateThreshold)} điểm
            </Typography>
          </Box>
          <Box sx={{ textAlign: "right" }}>
            <Typography variant="body2" sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
              {formatPercent(item.rate12mOnline)}
            </Typography>
            <RateDelta value={item.change12mOnline} showZero />
          </Box>
        </Stack>
      ))}
      {items.length > MAX_ROWS && (
        <Typography variant="caption" color="text.secondary" sx={{ pt: 0.5 }}>
          và {items.length - MAX_ROWS} ngân hàng khác ·{" "}
          <MuiLink component={Link} href="/watchlist" color="inherit">
            xem tất cả
          </MuiLink>
        </Typography>
      )}
    </Stack>
  );
}

function SignInPrompt() {
  return (
    <Prompt
      text="Đăng nhập để theo dõi ngân hàng và nhận thông báo khi lãi suất thay đổi hoặc có xếp hạng quý mới."
      action={
        <Button component={Link} href="/login?next=/" variant="contained" size="small" startIcon={<IconLogin size={16} />}>
          Đăng nhập
        </Button>
      }
    />
  );
}

function Prompt({ text, action }: { text: string; action: React.ReactNode }) {
  return (
    <Stack spacing={1.5} sx={{ alignItems: "center", textAlign: "center", py: 4, px: 1 }}>
      <Box
        aria-hidden
        sx={{
          width: 44,
          height: 44,
          borderRadius: 3,
          display: "grid",
          placeItems: "center",
          color: "primary.main",
          bgcolor: (t) => (t.vars ? `rgba(${t.vars.palette.primary.mainChannel} / 0.14)` : "action.selected"),
        }}
      >
        <IconBell size={22} stroke={1.7} />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 300 }}>
        {text}
      </Typography>
      {action}
    </Stack>
  );
}
