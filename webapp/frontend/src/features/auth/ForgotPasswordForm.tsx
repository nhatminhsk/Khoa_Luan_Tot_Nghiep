"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { FormProvider, useForm } from "react-hook-form";
import { z } from "zod";
import { RHFTextField } from "@/components/form/RHFFields";
import { errorMessage } from "@/lib/http/api-error";
import { authRepository } from "@/repositories/auth.repository";

const schema = z.object({
  email: z.string().trim().min(1, "Nhập email").email("Email không hợp lệ").max(160),
});
type ForgotPasswordValues = z.infer<typeof schema>;

/**
 * Quên mật khẩu: gửi link đặt lại tới email. Thông báo thành công giống nhau dù email có tài khoản hay không
 * (không cho dò email nào đã đăng ký).
 */
export function ForgotPasswordForm() {
  const methods = useForm<ForgotPasswordValues>({ resolver: zodResolver(schema), defaultValues: { email: "" } });
  const request = useMutation({ mutationFn: ({ email }: ForgotPasswordValues) => authRepository.requestPasswordReset(email) });

  return (
    <FormProvider {...methods}>
      <Stack
        component="form"
        spacing={2.25}
        noValidate
        onSubmit={methods.handleSubmit((values) => request.mutate(values))}
      >
        <div>
          <Typography variant="h2" component="h1">
            Quên mật khẩu
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Nhập email đã đăng ký. Hệ thống gửi một link để bạn đặt mật khẩu mới (link có hiệu lực 30 phút).
          </Typography>
        </div>
        {request.isSuccess ? (
          <Alert severity="success">
            Nếu email này có tài khoản, thư hướng dẫn đã được gửi. Kiểm tra cả hộp thư Spam; mỗi email chỉ gửi lại được sau 1 phút.
          </Alert>
        ) : (
          <>
            {request.isError && <Alert severity="error">{errorMessage(request.error)}</Alert>}
            <RHFTextField<ForgotPasswordValues> name="email" label="Email" type="email" autoComplete="email" autoFocus />
            <Button type="submit" variant="contained" size="large" loading={request.isPending}>
              Gửi link đặt lại mật khẩu
            </Button>
          </>
        )}
        <Typography variant="body2" align="center">
          <MuiLink component={Link} href="/login">
            Quay lại đăng nhập
          </MuiLink>
        </Typography>
      </Stack>
    </FormProvider>
  );
}
