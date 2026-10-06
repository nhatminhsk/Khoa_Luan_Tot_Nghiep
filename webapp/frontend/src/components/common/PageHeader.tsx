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

/**
 * Đầu trang kiểu dashboard: dòng nhỏ + tiêu đề + một dòng mô tả, thao tác bên phải.
 * Hàng tự xuống dòng: khối tiêu đề cần tối thiểu ~420px, không đủ chỗ thì nhóm thao tác chuyển xuống dưới
 * (iPad dọc, điện thoại) thay vì bóp tiêu đề còn vài chữ mỗi dòng.
 */
export function PageHeader({ title, description, actions, eyebrow }: PageHeaderProps) {
  return (
    <Stack
      direction="row"
      useFlexGap
      sx={{ flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", columnGap: 2, rowGap: 1.5, mb: 2.5 }}
    >
      <Box sx={{ minWidth: 0, flex: "1 1 420px" }}>
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
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexShrink: 0, alignItems: "center", flexWrap: "wrap", maxWidth: "100%" }}>
          {actions}
        </Stack>
      )}
    </Stack>
  );
}
