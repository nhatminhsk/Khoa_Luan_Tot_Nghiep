import { Box, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: ReactNode;
  /** Nút thao tác bên phải tiêu đề. */
  actions?: ReactNode;
  /** Dòng nhỏ phía trên tiêu đề (ví dụ mã ngân hàng, ngày dữ liệu). */
  eyebrow?: ReactNode;
}

/** Đầu trang kiểu dashboard: dòng nhỏ + tiêu đề + một dòng mô tả, thao tác bên phải. */
export function PageHeader({ title, description, actions, eyebrow }: PageHeaderProps) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={2}
      sx={{ alignItems: { xs: "flex-start", sm: "flex-end" }, justifyContent: "space-between", mb: 2.5 }}
    >
      <Box sx={{ minWidth: 0 }}>
        {eyebrow && (
          <Typography variant="overline" color="text.secondary" component="div" sx={{ lineHeight: 1.8 }}>
            {eyebrow}
          </Typography>
        )}
        <Typography variant="h1">{title}</Typography>
        {description && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 820 }}>
            {description}
          </Typography>
        )}
      </Box>
      {actions && (
        <Stack direction="row" spacing={1} sx={{ flexShrink: 0, alignItems: "center" }}>
          {actions}
        </Stack>
      )}
    </Stack>
  );
}
