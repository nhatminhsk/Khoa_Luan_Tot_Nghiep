"use client";

import { Avatar, Box, Button, Divider, IconButton, ListItemIcon, Menu, MenuItem, Skeleton, Typography } from "@mui/material";
import { IconBell, IconDatabaseCog, IconLogin, IconLogout } from "@tabler/icons-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useNotify } from "@/components/providers/NotifierProvider";
import { useAuth } from "@/hooks/use-auth";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : name.slice(0, 2)).toUpperCase();
}

export function UserMenu() {
  const { user, isLoading, isAdmin, logout } = useAuth();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const pathname = usePathname();
  const router = useRouter();
  const notify = useNotify();

  if (isLoading) return <Skeleton variant="circular" width={36} height={36} />;

  if (!user) {
    const href = `/login?next=${encodeURIComponent(pathname)}`;
    return (
      <>
        <Button
          component={Link}
          href={href}
          variant="contained"
          startIcon={<IconLogin size={18} />}
          sx={{ display: { xs: "none", sm: "inline-flex" } }}
        >
          Đăng nhập
        </Button>
        {/* Điện thoại: chỉ để biểu tượng, nhường chỗ cho ô tìm ngân hàng. */}
        <IconButton
          component={Link}
          href={href}
          aria-label="Đăng nhập"
          sx={{
            display: { xs: "inline-flex", sm: "none" },
            width: 40,
            height: 40,
            color: "primary.contrastText",
            bgcolor: "primary.main",
            "&:hover": { bgcolor: "primary.dark" },
          }}
        >
          <IconLogin size={20} />
        </IconButton>
      </>
    );
  }

  const close = () => setAnchor(null);

  return (
    <>
      <IconButton aria-label={`Tài khoản ${user.displayName}`} onClick={(e) => setAnchor(e.currentTarget)} sx={{ p: 0.5 }}>
        <Avatar sx={{ width: 36, height: 36, bgcolor: "primary.main", fontSize: "0.875rem", fontWeight: 600 }}>
          {initials(user.displayName)}
        </Avatar>
      </IconButton>
      <Menu anchorEl={anchor} open={anchor !== null} onClose={close} slotProps={{ paper: { sx: { minWidth: 240 } } }}>
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="subtitle2">{user.displayName}</Typography>
          <Typography variant="caption" color="text.secondary">
            {user.email}
          </Typography>
        </Box>
        <Divider />
        <MenuItem component={Link} href="/watchlist" onClick={close}>
          <ListItemIcon>
            <IconBell size={18} aria-hidden />
          </ListItemIcon>
          Theo dõi và thông báo
        </MenuItem>
        {isAdmin && (
          <MenuItem component={Link} href="/admin" onClick={close}>
            <ListItemIcon>
              <IconDatabaseCog size={18} aria-hidden />
            </ListItemIcon>
            Quản trị dữ liệu
          </MenuItem>
        )}
        <Divider />
        <MenuItem
          onClick={() => {
            close();
            logout.mutate(undefined, {
              onSuccess: () => {
                notify("Đã đăng xuất");
                router.push("/");
              },
            });
          }}
        >
          <ListItemIcon>
            <IconLogout size={18} aria-hidden />
          </ListItemIcon>
          Đăng xuất
        </MenuItem>
      </Menu>
    </>
  );
}
