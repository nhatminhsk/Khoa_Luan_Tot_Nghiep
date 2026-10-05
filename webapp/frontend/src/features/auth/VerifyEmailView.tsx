"use client";

import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { IconCircleCheck } from "@tabler/icons-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { authRepository } from "@/repositories/auth.repository";

/**
 * Trang mở từ link trong email xác minh. Không cần đăng nhập: token trong link tự chứng minh người dùng.
 * Gọi xác minh một lần khi mở trang; gọi lại (tải lại trang, bấm link lần hai) vẫn thành công.
 */
export function VerifyEmailView() {
  const token = useSearchParams().get("token") ?? "";
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const verification = useQuery({
    queryKey: ["verify-email", token],
    queryFn: () => authRepository.verifyEmail(token),
    enabled: token.length > 0,
    retry: false,
    staleTime: Infinity,
  });

  const verified = verification.data;
  useEffect(() => {
    if (!verified) return;
    // Cùng trình duyệt với phiên đăng nhập: cập nhật trạng thái đã xác minh ở mọi trang đang mở.
    queryClient.invalidateQueries({ queryKey: queryKeys.me });
    queryClient.invalidateQueries({ queryKey: queryKeys.notificationSettings });
    queryClient.invalidateQueries({ queryKey: queryKeys.emailVerification });
  }, [verified, queryClient]);

  const nextHref = user ? "/watchlist#cai-dat-thong-bao" : "/login?next=%2Fwatchlist";

  return (
    <Stack spacing={2.25}>
      <Typography variant="h2" component="h1">
        Xác minh email
      </Typography>
      {!token ? (
        <Alert severity="error">Link xác minh thiếu mã. Hãy mở lại đúng link trong email, hoặc gửi link mới ở trang Theo dõi.</Alert>
      ) : verification.isPending ? (
        <Stack direction="row" spacing={1.5} role="status" sx={{ alignItems: "center", py: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="body2">Đang xác minh…</Typography>
        </Stack>
      ) : verification.isError ? (
        <>
          <Alert severity="error">{errorMessage(verification.error)}</Alert>
          <Typography variant="body2" color="text.secondary">
            Link có hạn 24 giờ. Đăng nhập rồi bấm “Gửi lại mã” trong phần Cài đặt thông báo để nhận email mới; có thể
            nhập mã 6 số trong thư thay cho bấm link.
          </Typography>
          <Button component={Link} href={nextHref} variant="contained" size="large">
            {user ? "Mở cài đặt thông báo" : "Đăng nhập"}
          </Button>
        </>
      ) : (
        <>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "flex-start" }}>
            <Box sx={{ color: "success.main", pt: 0.25 }}>
              <IconCircleCheck size={24} aria-hidden />
            </Box>
            <Typography variant="body1">
              Đã xác minh <strong>{verified?.email}</strong>.
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">
            Để nhận thông báo qua email, chọn “Trong ứng dụng và email” ở phần Cài đặt thông báo của trang Theo dõi.
          </Typography>
          <Button component={Link} href={nextHref} variant="contained" size="large">
            {user ? "Mở cài đặt thông báo" : "Đăng nhập để chọn nhận email"}
          </Button>
        </>
      )}
    </Stack>
  );
}
