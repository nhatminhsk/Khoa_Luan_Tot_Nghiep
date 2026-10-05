"use client";

import { alpha, createTheme } from "@mui/material/styles";

/**
 * Hệ thống thiết kế: dashboard fintech, ưu tiên tin cậy và dễ đọc số.
 * - Bố cục kiểu dashboard: nền trang tối hơn, mọi khối nằm trong thẻ bo 14px, viền mảnh, tiêu đề thẻ gọn.
 * - Màu chủ đạo xanh dương (tin cậy); màu trạng thái (tăng/giảm, tốt/xấu) luôn đi kèm icon hoặc dấu +/−.
 * - Hai chế độ sáng/tối là hai bảng màu riêng, đều đạt tương phản chữ ≥ 4.5:1 trên nền thẻ.
 * - Biến CSS (cssVariables) để đổi chế độ không bị nháy khi tải trang.
 */
const DARK_BORDER = "rgba(148, 163, 184, 0.14)";
const LIGHT_BORDER = "#e3e8ef";

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: "class" },
  colorSchemes: {
    light: {
      palette: {
        primary: { main: "#1d4ed8", light: "#3b82f6", dark: "#1e40af", contrastText: "#ffffff" },
        secondary: { main: "#0f766e", contrastText: "#ffffff" },
        success: { main: "#15803d" },
        error: { main: "#b91c1c" },
        warning: { main: "#b45309" },
        info: { main: "#0369a1" },
        background: { default: "#f1f4f9", paper: "#ffffff" },
        text: { primary: "#0f172a", secondary: "#475569", disabled: "#94a3b8" },
        divider: LIGHT_BORDER,
      },
    },
    dark: {
      palette: {
        primary: { main: "#60a5fa", light: "#93c5fd", dark: "#3b82f6", contrastText: "#0b1120" },
        secondary: { main: "#2dd4bf", contrastText: "#0b1120" },
        success: { main: "#4ade80" },
        error: { main: "#f87171" },
        warning: { main: "#fbbf24" },
        info: { main: "#38bdf8" },
        background: { default: "#080c15", paper: "#101623" },
        text: { primary: "#f1f5f9", secondary: "#a9b4c6", disabled: "#64748b" },
        divider: DARK_BORDER,
      },
    },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "var(--font-sans), system-ui, -apple-system, 'Segoe UI', sans-serif",
    h1: { fontSize: "1.5rem", fontWeight: 700, lineHeight: 1.25, letterSpacing: "-0.01em" },
    h2: { fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.3 },
    h3: { fontSize: "1rem", fontWeight: 600, lineHeight: 1.4 },
    h4: { fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.4 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600, fontSize: "0.8125rem" },
    button: { textTransform: "none", fontWeight: 600 },
    overline: { fontWeight: 600, fontSize: "0.6875rem", letterSpacing: "0.08em", lineHeight: 1.6 },
  },
  components: {
    MuiButtonBase: {
      styleOverrides: {
        root: ({ theme }) => ({
          "&.Mui-focusVisible": {
            outline: `2px solid ${(theme.vars ?? theme).palette.primary.main}`,
            outlineOffset: 2,
          },
        }),
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 10, minHeight: 40 } },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
      styleOverrides: {
        // Thẻ dashboard: bo 14px, viền mảnh; nền tối có lớp sáng rất nhẹ ở trên để thẻ tách khỏi nền trang.
        root: ({ theme }) => ({
          borderRadius: 14,
          borderColor: LIGHT_BORDER,
          boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
          ...theme.applyStyles("dark", {
            borderColor: DARK_BORDER,
            boxShadow: "none",
            backgroundImage: "linear-gradient(180deg, rgba(255,255,255,0.025) 0%, rgba(255,255,255,0) 100%)",
          }),
        }),
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderBottomColor: (theme.vars ?? theme).palette.divider,
        }),
        head: ({ theme }) => ({
          fontWeight: 600,
          fontSize: "0.75rem",
          color: (theme.vars ?? theme).palette.text.secondary,
          whiteSpace: "nowrap",
          backgroundColor: alpha("#94a3b8", 0.06),
        }),
        // Số trong bảng thẳng cột theo hàng đơn vị.
        body: { fontVariantNumeric: "tabular-nums" },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: { "&:last-child > td": { borderBottom: 0 } },
      },
    },
    // Nhóm nút chọn kiểu "pill" của dashboard (7N / 30N, Trực tuyến / Tại quầy): nền chìm, mục đang chọn nổi lên.
    MuiToggleButtonGroup: {
      styleOverrides: {
        root: ({ theme }) => ({
          padding: 3,
          gap: 2,
          borderRadius: 10,
          backgroundColor: alpha("#94a3b8", 0.1),
          ...theme.applyStyles("dark", { backgroundColor: alpha("#94a3b8", 0.08) }),
        }),
        grouped: {
          border: 0,
          borderRadius: "8px !important",
          margin: 0,
        },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          border: 0,
          borderRadius: 8,
          fontWeight: 600,
          fontSize: "0.8125rem",
          lineHeight: 1.3,
          color: (theme.vars ?? theme).palette.text.secondary,
          "&.Mui-selected, &.Mui-selected:hover": {
            backgroundColor: (theme.vars ?? theme).palette.background.paper,
            color: (theme.vars ?? theme).palette.text.primary,
            boxShadow: "0 1px 2px rgba(15, 23, 42, 0.12)",
          },
          ...theme.applyStyles("dark", {
            "&.Mui-selected, &.Mui-selected:hover": {
              backgroundColor: alpha("#94a3b8", 0.2),
              color: (theme.vars ?? theme).palette.text.primary,
              boxShadow: "none",
            },
          }),
        }),
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { height: 3, borderRadius: 3 },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { fontWeight: 600, minHeight: 44 },
      },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 500, borderRadius: 8 } },
    },
    MuiAlert: {
      styleOverrides: { root: { alignItems: "flex-start", borderRadius: 12 } },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 10 },
      },
    },
  },
});
