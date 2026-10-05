"use client";

import { Badge, IconButton, Tooltip } from "@mui/material";
import { IconBell } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";

/** Chuông thông báo: số chưa đọc, tự làm mới mỗi 5 phút. */
export function NotificationBell() {
  const { data } = useQuery({
    queryKey: queryKeys.unreadCount,
    queryFn: meRepository.unreadCount,
    refetchInterval: 5 * 60 * 1000,
  });
  const unread = data?.unread ?? 0;
  const label = unread > 0 ? `Thông báo: ${unread} chưa đọc` : "Thông báo";

  return (
    <Tooltip title={label}>
      <IconButton component={Link} href="/watchlist#thong-bao" aria-label={label} sx={{ width: 44, height: 44 }}>
        <Badge badgeContent={unread} color="error" max={99}>
          <IconBell size={20} stroke={1.7} />
        </Badge>
      </IconButton>
    </Tooltip>
  );
}
