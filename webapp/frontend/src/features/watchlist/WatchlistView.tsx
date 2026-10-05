"use client";

import {
  Autocomplete,
  Box,
  Button,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { visuallyHidden } from "@mui/utils";
import { IconExternalLink, IconPlus, IconTrash } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { BankLabel } from "@/components/common/BankLabel";
import { PageHeader } from "@/components/common/PageHeader";
import { RateDelta } from "@/components/common/RateDelta";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { useNotify } from "@/components/providers/NotifierProvider";
import { toLoanQuery } from "@/features/loans/loan-params";
import { toSavingsQuery } from "@/features/savings/savings-params";
import { useAuth } from "@/hooks/use-auth";
import { useBanks } from "@/hooks/use-banks";
import { errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";
import type { Bank, SavedNeed } from "@/types/api";
import { formatDateTime, formatNumber, formatPercent, formatTerm, formatVnd } from "@/utils/format";
import { CHANNEL_LABEL, LOAN_PURPOSE_LABEL } from "@/utils/labels";
import { NotificationSettingsCard } from "./NotificationSettingsCard";

const THRESHOLDS = [0.05, 0.1, 0.2, 0.3, 0.5, 1];

export function WatchlistView() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <LoadingBlock height={400} />;
  if (!user) {
    // proxy.ts đã chuyển hướng khi thiếu cookie; nhánh này cho trường hợp cookie hết hạn.
    return (
      <SectionCard>
        <EmptyState
          title="Bạn cần đăng nhập"
          description="Đăng nhập để theo dõi ngân hàng, nhận thông báo và mở lại nhu cầu đã lưu."
          action={
            <Button component={Link} href="/login?next=/watchlist" variant="contained">
              Đăng nhập
            </Button>
          }
        />
      </SectionCard>
    );
  }

  return (
    <>
      <PageHeader
        title="Theo dõi và thông báo"
        description={`Xin chào ${user.displayName}. Hệ thống so lãi suất mỗi ngày sau lần cập nhật 15:30 và báo khi ngân hàng bạn theo dõi thay đổi từ ngưỡng đã đặt.`}
      />
      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Stack spacing={2.5}>
            <WatchItemsCard />
            <SavedNeedsCard />
          </Stack>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Stack spacing={2.5}>
            <NotificationsCard />
            <NotificationSettingsCard />
          </Stack>
        </Grid>
      </Grid>
    </>
  );
}

function WatchItemsCard() {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const { banks } = useBanks();
  const watchlist = useQuery({ queryKey: queryKeys.watchlist, queryFn: meRepository.watchlist });
  const [adding, setAdding] = useState<Bank | null>(null);
  const [threshold, setThreshold] = useState(0.1);

  const refresh = () => queryClient.invalidateQueries({ queryKey: queryKeys.watchlist });
  const add = useMutation({
    mutationFn: () => meRepository.watch(adding!.ticker, threshold),
    onSuccess: () => {
      notify(`Đã thêm ${adding?.shortName} vào danh sách theo dõi`);
      setAdding(null);
      refresh();
    },
    onError: (e) => notify(errorMessage(e), "error"),
  });
  const update = useMutation({
    mutationFn: ({ ticker, value }: { ticker: string; value: number }) => meRepository.updateWatch(ticker, value),
    onSuccess: refresh,
    onError: (e) => notify(errorMessage(e), "error"),
  });
  const remove = useMutation({
    mutationFn: (ticker: string) => meRepository.unwatch(ticker),
    onSuccess: () => {
      notify("Đã bỏ theo dõi");
      refresh();
    },
    onError: (e) => notify(errorMessage(e), "error"),
  });

  const watched = new Set((watchlist.data ?? []).map((w) => w.ticker));

  return (
    <SectionCard title="Ngân hàng đang theo dõi" subtitle="Ngưỡng báo: mức thay đổi lãi suất (điểm %) ở bất kỳ kỳ hạn nào." flush>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ px: 2.5, pb: 2 }}>
        <Autocomplete
          sx={{ flex: 1 }}
          size="small"
          options={banks.filter((b) => !watched.has(b.ticker))}
          value={adding}
          onChange={(_, bank) => setAdding(bank)}
          getOptionLabel={(b) => `${b.ticker} · ${b.shortName}`}
          renderInput={(params) => <TextField {...params} label="Thêm ngân hàng" />}
        />
        <TextField select size="small" label="Ngưỡng báo" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} sx={{ minWidth: 140 }}>
          {THRESHOLDS.map((t) => (
            <MenuItem key={t} value={t}>
              ≥ {formatNumber(t)} điểm %
            </MenuItem>
          ))}
        </TextField>
        <Button variant="contained" startIcon={<IconPlus size={18} />} disabled={!adding} loading={add.isPending} onClick={() => add.mutate()}>
          Thêm
        </Button>
      </Stack>
      {watchlist.isError ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <ErrorState error={watchlist.error} onRetry={() => watchlist.refetch()} />
        </Box>
      ) : !watchlist.data ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <LoadingBlock height={160} />
        </Box>
      ) : watchlist.data.length === 0 ? (
        <EmptyState title="Chưa theo dõi ngân hàng nào" description="Thêm ngân hàng ở trên, hoặc bấm “Theo dõi” trong hồ sơ ngân hàng." />
      ) : (
        <TableContainer>
          <Table size="small" aria-label="Danh sách ngân hàng đang theo dõi">
            <TableHead>
              <TableRow>
                <TableCell>Ngân hàng</TableCell>
                <TableCell align="right">Lãi 12T trực tuyến</TableCell>
                <TableCell>Ngưỡng báo</TableCell>
                <TableCell align="right">
                  <Box component="span" sx={visuallyHidden}>
                    Thao tác
                  </Box>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {watchlist.data.map((item) => (
                <TableRow key={item.ticker} hover>
                  <TableCell>
                    <BankLabel ticker={item.ticker} shortName={item.shortName} />
                  </TableCell>
                  <TableCell align="right">
                    {formatPercent(item.rate12mOnline)} <RateDelta value={item.change12mOnline} />
                  </TableCell>
                  <TableCell>
                    <TextField
                      select
                      size="small"
                      value={item.rateThreshold}
                      onChange={(e) => update.mutate({ ticker: item.ticker, value: Number(e.target.value) })}
                      slotProps={{ htmlInput: { "aria-label": `Ngưỡng báo của ${item.shortName}` } }}
                      sx={{ minWidth: 130 }}
                    >
                      {[...new Set([...THRESHOLDS, item.rateThreshold])].sort((a, b) => a - b).map((t) => (
                        <MenuItem key={t} value={t}>
                          ≥ {formatNumber(t)} điểm %
                        </MenuItem>
                      ))}
                    </TextField>
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Bỏ theo dõi">
                      <IconButton aria-label={`Bỏ theo dõi ${item.shortName}`} onClick={() => remove.mutate(item.ticker)}>
                        <IconTrash size={18} />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </SectionCard>
  );
}

function NotificationsCard() {
  const queryClient = useQueryClient();
  const notifications = useQuery({ queryKey: queryKeys.notifications, queryFn: () => meRepository.notifications(0, 20) });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.notifications });
    queryClient.invalidateQueries({ queryKey: queryKeys.unreadCount });
  };
  const markRead = useMutation({ mutationFn: (id: number) => meRepository.markRead(id), onSuccess: refresh });
  const markAll = useMutation({ mutationFn: meRepository.markAllRead, onSuccess: refresh });
  const items = notifications.data?.items ?? [];
  const unread = items.filter((n) => !n.read).length;

  return (
    <SectionCard
      id="thong-bao"
      title="Thông báo"
      subtitle={unread > 0 ? `${unread} thông báo chưa đọc` : "Không có thông báo mới"}
      action={
        unread > 0 && (
          <Button size="small" onClick={() => markAll.mutate()} loading={markAll.isPending}>
            Đánh dấu đã đọc
          </Button>
        )
      }
      flush
    >
      {notifications.isError ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <ErrorState error={notifications.error} onRetry={() => notifications.refetch()} />
        </Box>
      ) : !notifications.data ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <LoadingBlock height={160} />
        </Box>
      ) : items.length === 0 ? (
        <EmptyState
          title="Chưa có thông báo"
          description="Bạn sẽ nhận thông báo khi lãi suất ngân hàng đang theo dõi thay đổi, hoặc khi có xếp hạng quý mới."
        />
      ) : (
        <List disablePadding>
          {items.map((n, i) => (
            <Box key={n.id}>
              {i > 0 && <Divider component="li" />}
              <ListItem
                sx={{ px: 2.5, alignItems: "flex-start", bgcolor: n.read ? undefined : "action.hover" }}
                secondaryAction={
                  !n.read && (
                    <Button size="small" onClick={() => markRead.mutate(n.id)}>
                      Đã đọc
                    </Button>
                  )
                }
              >
                <ListItemText
                  primary={n.title}
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="text.secondary" sx={{ display: "block" }}>
                        {n.body}
                      </Typography>
                      <Typography component="span" variant="caption" color="text.secondary">
                        {formatDateTime(n.createdAt)}
                        {n.emailedAt && " · đã gửi email"}
                      </Typography>
                    </>
                  }
                  slotProps={{ primary: { sx: { fontWeight: n.read ? 500 : 700, pr: 8 } } }}
                />
              </ListItem>
            </Box>
          ))}
        </List>
      )}
    </SectionCard>
  );
}

function SavedNeedsCard() {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const needs = useQuery({ queryKey: queryKeys.needs, queryFn: meRepository.needs });
  const remove = useMutation({
    mutationFn: (id: number) => meRepository.deleteNeed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.needs });
      notify("Đã xóa nhu cầu");
    },
    onError: (e) => notify(errorMessage(e), "error"),
  });

  return (
    <SectionCard title="Nhu cầu đã lưu" subtitle="Mở lại trang gửi tiết kiệm / vay với đúng tiêu chí đã lưu." flush>
      {!needs.data ? (
        <Box sx={{ px: 2.5, pb: 2.5 }}>
          <LoadingBlock height={120} />
        </Box>
      ) : needs.data.length === 0 ? (
        <EmptyState title="Chưa lưu nhu cầu nào" description="Ở trang Gửi tiết kiệm hoặc Vay, bấm “Lưu nhu cầu”." />
      ) : (
        <List disablePadding>
          {needs.data.map((need, i) => (
            <Box key={need.id}>
              {i > 0 && <Divider component="li" />}
              <ListItem
                sx={{ px: 2.5 }}
                secondaryAction={
                  <Stack direction="row" spacing={0.5}>
                    <Tooltip title="Mở">
                      <IconButton component={Link} href={needHref(need)} aria-label={`Mở ${need.label}`}>
                        <IconExternalLink size={18} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Xóa">
                      <IconButton aria-label={`Xóa ${need.label}`} onClick={() => remove.mutate(need.id)}>
                        <IconTrash size={18} />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                }
              >
                <ListItemText
                  primary={need.label}
                  secondary={describeNeed(need)}
                  slotProps={{ primary: { sx: { fontWeight: 600 } }, secondary: { sx: { pr: 10 } } }}
                />
              </ListItem>
            </Box>
          ))}
        </List>
      )}
    </SectionCard>
  );
}

function needHref(need: SavedNeed): string {
  if (need.purpose === "SAVINGS") {
    return `/savings?${toSavingsQuery({
      amount: need.amount,
      termMonths: need.termMonths,
      channel: need.channel ?? "ONLINE",
      weights: { rate: need.weightRate ?? 50, safety: need.weightSafety ?? 30, app: need.weightApp ?? 20 },
    })}`;
  }
  return `/loans?${toLoanQuery({
    purpose: need.loanPurpose ?? "HOME_PURCHASE",
    amount: need.amount,
    termMonths: need.termMonths,
    repayment: need.repayment ?? "DECLINING_BALANCE",
  })}`;
}

function describeNeed(need: SavedNeed): string {
  if (need.purpose === "SAVINGS") {
    return `Gửi tiết kiệm · ${formatVnd(need.amount)} · ${need.termMonths} tháng · ${
      need.channel ? CHANNEL_LABEL[need.channel].toLowerCase() : ""
    }`;
  }
  return `Vay · ${need.loanPurpose ? LOAN_PURPOSE_LABEL[need.loanPurpose] : ""} · ${formatVnd(need.amount)} · ${formatTerm(
    need.termMonths,
  )}`;
}
