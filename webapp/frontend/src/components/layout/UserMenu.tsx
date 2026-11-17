"use client";

import { Avatar, Box, Button, Divider, IconButton, ListItemIcon, Menu, MenuItem, Skeleton, Typography } from "@mui/material";
import { IconBell, IconDatabaseCog, IconDevicesOff, IconKey, IconLogin, IconLogout, IconUsers } from "@tabler/icons-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { ChangePasswordDialog } from "@/features/account/ChangePasswordDialog";
import { reloadTo } from "@/features/auth/reload-after-auth";
import { useAuth } from "@/hooks/use-auth";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : name.slice(0, 2)).toUpperCase();
}

export function UserMenu() {
  const { user, isLoading, can, logout, logoutEverywhere } = useAuth();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [changingPassword, setChangingPassword] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  if (isLoading) return <Skeleton variant="circular" width={36} height={36} />;

  if (!user) {
    const href = `/login?next=${encodeURIComponent(pathname)}`;
    // Trước đây `next` chỉ có pathname nên đăng nhập xong mất tiêu chí trên URL (ví dụ /savings?amount=…&term=… về mặc định,
    // hồ sơ ngân hàng về tab đầu). Đọc location lúc bấm thay vì useSearchParams để thanh trên không phải nằm trong Suspense.
    const goLogin = (e: React.MouseEvent) => {
      e.preventDefault();
      router.push(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
    };
    return (
      <>
        <Button
          component={Link}
          href={href}
          onClick={goLogin}
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
          onClick={goLogin}
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
        {can("DATA_MANAGE") && (
          <MenuItem component={Link} href="/admin" onClick={close}>
            <ListItemIcon>
              <IconDatabaseCog size={18} aria-hidden />
            </ListItemIcon>
            Quản trị dữ liệu
          </MenuItem>
        )}
        {can("USER_MANAGE") && (
          <MenuItem component={Link} href="/admin/users" onClick={close}>
            <ListItemIcon>
              <IconUsers size={18} aria-hidden />
            </ListItemIcon>
            Quản lý người dùng
          </MenuItem>
        )}
        <MenuItem
          onClick={() => {
            close();
            setChangingPassword(true);
          }}
        >
          <ListItemIcon>
            <IconKey size={18} aria-hidden />
          </ListItemIcon>
          Đổi mật khẩu
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            close();
            // Tải lại cả trang: trang cần đăng nhập đã prefetch lúc còn phiên không được dùng lại (reload-after-auth.ts).
            logout.mutate(undefined, {
              onSuccess: () => reloadTo("/", "Đã đăng xuất trên trình duyệt này", "assign"),
            });
          }}
        >
          <ListItemIcon>
            <IconLogout size={18} aria-hidden />
          </ListItemIcon>
          {/* Chỉ xóa cookie trên trình duyệt này; thu hồi mọi phiên là mục bên dưới. */}
          Đăng xuất trên trình duyệt này
        </MenuItem>
        <MenuItem
          onClick={() => {
            close();
            logoutEverywhere.mutate(undefined, {
              onSuccess: () => reloadTo("/", "Đã đăng xuất trên mọi thiết bị", "assign"),
            });
          }}
        >
          <ListItemIcon>
            <IconDevicesOff size={18} aria-hidden />
          </ListItemIcon>
          Đăng xuất mọi thiết bị
        </MenuItem>
      </Menu>
      <ChangePasswordDialog open={changingPassword} onClose={() => setChangingPassword(false)} />
    </>
  );
}
