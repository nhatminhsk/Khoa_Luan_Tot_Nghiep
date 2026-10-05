"use client";

// Client component: truyền component={Link} (một hàm) cho Button chỉ hợp lệ ở phía client.
import { Button, Stack, Typography } from "@mui/material";
import Link from "next/link";

export default function NotFound() {
  return (
    <Stack
      spacing={2}
      sx={{ alignItems: "center", justifyContent: "center", minHeight: "100dvh", px: 2, textAlign: "center" }}
    >
      <Typography variant="overline" color="text.secondary">
        Lỗi 404
      </Typography>
      <Typography variant="h1">Không tìm thấy trang</Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 460 }}>
        Đường dẫn không tồn tại hoặc ngân hàng không thuộc phạm vi 22 ngân hàng của hệ thống.
      </Typography>
      <Button component={Link} href="/" variant="contained">
        Về trang tổng quan
      </Button>
    </Stack>
  );
}
