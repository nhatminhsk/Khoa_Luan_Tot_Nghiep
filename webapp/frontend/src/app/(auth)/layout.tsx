import { Box, Card, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/layout/BrandMark";

/** Layout tối giản cho đăng nhập / đăng ký: không menu, chỉ một thẻ ở giữa. */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ minHeight: "100dvh", display: "grid", placeItems: "center", bgcolor: "background.default", px: 2, py: 4 }}>
      <Stack spacing={3} sx={{ width: "100%", maxWidth: 420 }}>
        <Box sx={{ alignSelf: "center" }}>
          <BrandMark />
        </Box>
        <Card sx={{ p: { xs: 2.5, sm: 3.5 } }}>{children}</Card>
        <Typography variant="caption" color="text.secondary" align="center">
          Tài khoản chỉ lưu nhu cầu, danh sách theo dõi và cài đặt thông báo. Hệ thống không lưu thu nhập, số dư hay thông tin
          tài khoản ngân hàng của bạn.
        </Typography>
      </Stack>
    </Box>
  );
}
