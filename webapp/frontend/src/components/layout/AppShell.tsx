"use client";

import { AppBar, Box, Drawer, IconButton, Stack, Toolbar } from "@mui/material";
import { IconMenu2 } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/hooks/use-auth";
import { BankSearch } from "./BankSearch";
import { DataStatusChip } from "./DataStatusChip";
import { NotificationBell } from "./NotificationBell";
import { SideNav } from "./SideNav";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";

const DRAWER_WIDTH = 252;

/**
 * Khung trang chính kiểu dashboard: menu trái cố định (trượt ra trên điện thoại),
 * thanh trên trong suốt mờ (tìm ngân hàng, trạng thái dữ liệu, sáng/tối, thông báo, tài khoản)
 * và vùng nội dung rộng để xếp lưới thẻ.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isAuthenticated } = useAuth();

  return (
    <Box sx={{ display: "flex", minHeight: "100dvh", bgcolor: "background.default" }}>
      <Box component="aside" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { width: DRAWER_WIDTH } }}
        >
          <SideNav onNavigate={() => setMobileOpen(false)} />
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": {
              width: DRAWER_WIDTH,
              boxSizing: "border-box",
              borderRightColor: "divider",
              bgcolor: "background.paper",
            },
          }}
        >
          <SideNav />
        </Drawer>
      </Box>

      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <AppBar
          position="sticky"
          color="inherit"
          elevation={0}
          sx={{
            borderBottom: 1,
            borderColor: "divider",
            bgcolor: (t) => (t.vars ? `rgba(${t.vars.palette.background.defaultChannel} / 0.82)` : "background.default"),
            backdropFilter: "saturate(160%) blur(10px)",
          }}
        >
          <Toolbar sx={{ gap: 1, minHeight: { xs: 60, sm: 64 }, px: { xs: 2, sm: 3 } }}>
            <IconButton
              aria-label="Mở menu"
              onClick={() => setMobileOpen(true)}
              sx={{ display: { md: "none" }, width: 44, height: 44 }}
            >
              <IconMenu2 size={22} />
            </IconButton>
            <Box sx={{ flex: 1, minWidth: 0, display: "flex" }}>
              <BankSearch />
            </Box>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <DataStatusChip />
              <ThemeToggle />
              {isAuthenticated && <NotificationBell />}
              <UserMenu />
            </Stack>
          </Toolbar>
        </AppBar>
        <Box
          component="main"
          id="noi-dung"
          sx={{ flex: 1, width: "100%", maxWidth: 1480, mx: "auto", px: { xs: 2, sm: 3 }, py: { xs: 2.5, sm: 3 } }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
