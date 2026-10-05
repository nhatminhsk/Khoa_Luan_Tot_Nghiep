"use client";

import { Box, List, ListItemButton, ListItemIcon, ListItemText, ListSubheader, Stack, Typography } from "@mui/material";
import { IconInfoCircle, IconLock } from "@tabler/icons-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, isActive } from "@/config/navigation";
import { useAuth } from "@/hooks/use-auth";
import { BrandMark } from "./BrandMark";

/** Menu bên trái, dựng từ NAV_GROUPS. Mục cần đăng nhập hiện ổ khóa khi chưa đăng nhập; mục quản trị ẩn với người dùng thường. */
export function SideNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { isAuthenticated, isAdmin, isLoading } = useAuth();

  return (
    <Stack sx={{ height: "100%" }}>
      <Box sx={{ px: 2.5, pt: 2.25, pb: 1.5 }}>
        <BrandMark />
      </Box>
      <Box component="nav" aria-label="Điều hướng chính" sx={{ flex: 1, overflowY: "auto", py: 0.5 }}>
        {NAV_GROUPS.map((group) => {
          const items = group.items.filter((item) => !item.adminOnly || isAdmin);
          if (items.length === 0) return null;
          return (
            <List
              key={group.id}
              dense
              disablePadding
              subheader={
                <ListSubheader
                  disableSticky
                  sx={{
                    bgcolor: "transparent",
                    lineHeight: "28px",
                    mt: 1.25,
                    px: 1.5,
                    fontSize: "0.6875rem",
                    fontWeight: 600,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "text.disabled",
                  }}
                >
                  {group.title}
                </ListSubheader>
              }
              sx={{ px: 1.5 }}
            >
              {items.map((item) => {
                const active = isActive(item, pathname);
                // Chỉ hiện ổ khóa khi đã biết chắc chưa đăng nhập (tránh nháy lúc đang kiểm tra phiên).
                const locked = item.requiresAuth && !isLoading && !isAuthenticated;
                const ItemIcon = item.icon;
                return (
                  <ListItemButton
                    key={item.href}
                    component={Link}
                    href={item.href}
                    selected={active}
                    aria-current={active ? "page" : undefined}
                    onClick={onNavigate}
                    sx={{
                      position: "relative",
                      borderRadius: 2.5,
                      minHeight: 42,
                      mb: 0.25,
                      px: 1.5,
                      color: "text.secondary",
                      "&:hover": { color: "text.primary" },
                      "&.Mui-selected, &.Mui-selected:hover": {
                        bgcolor: (t) => (t.vars ? `rgba(${t.vars.palette.primary.mainChannel} / 0.12)` : "action.selected"),
                        color: "primary.main",
                        "& .MuiListItemIcon-root": { color: "primary.main" },
                      },
                      // Vạch nhấn bên trái mục đang mở.
                      "&.Mui-selected::before": {
                        content: '""',
                        position: "absolute",
                        left: -12,
                        top: 10,
                        bottom: 10,
                        width: 3,
                        borderRadius: 3,
                        bgcolor: "primary.main",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 34, color: "inherit" }}>
                      <ItemIcon size={20} stroke={1.7} aria-hidden />
                    </ListItemIcon>
                    <ListItemText
                      primary={item.label}
                      slotProps={{ primary: { sx: { fontWeight: active ? 600 : 500, fontSize: "0.875rem" } } }}
                    />
                    {locked && <IconLock size={16} stroke={1.7} aria-label="Cần đăng nhập" />}
                  </ListItemButton>
                );
              })}
            </List>
          );
        })}
      </Box>
      <Stack
        direction="row"
        spacing={1}
        sx={{ m: 1.5, p: 1.5, borderRadius: 3, bgcolor: "action.hover", color: "text.secondary", alignItems: "flex-start" }}
      >
        <IconInfoCircle size={16} stroke={1.7} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden />
        <Typography variant="caption" sx={{ lineHeight: 1.45 }}>
          Phạm vi: 22 ngân hàng thương mại niêm yết, số liệu từ 2019.
        </Typography>
      </Stack>
    </Stack>
  );
}
