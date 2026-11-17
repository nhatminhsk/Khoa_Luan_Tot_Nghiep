"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormProvider, useForm } from "react-hook-form";
import { z } from "zod";
import { RHFTextField } from "@/components/form/RHFFields";
import { ApiError, errorMessage } from "@/lib/http/api-error";
import { authRepository } from "@/repositories/auth.repository";
import { newPasswordSchema } from "./password-rules";

const schema = z
  .object({
    newPassword: newPasswordSchema,
    confirmPassword: z.string(),
  })
  .refine((v) => v.newPassword === v.confirmPassword, { path: ["confirmPassword"], message: "Mật khẩu nhập lại không khớp" });
type ResetPasswordValues = z.infer<typeof schema>;

/** Trang mở từ link trong thư "Đặt lại mật khẩu". Đặt xong thì đăng nhập lại; mọi phiên cũ đã bị thu hồi. */
export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const methods = useForm<ResetPasswordValues>({
    resolver: zodResolver(schema),
    defaultValues: { newPassword: "", confirmPassword: "" },
  });
  const reset = useMutation({
    mutationFn: ({ newPassword }: ResetPasswordValues) => authRepository.confirmPasswordReset(token, newPassword),
  });
  const linkInvalid = !token || (reset.error instanceof ApiError && reset.error.code === "PASSWORD_RESET_INVALID");

  return (
    <FormProvider {...methods}>
      <Stack
        component="form"
        spacing={2.25}
        noValidate
        onSubmit={methods.handleSubmit((values) => reset.mutate(values))}
      >
        <Typography variant="h2" component="h1">
          Đặt mật khẩu mới
        </Typography>
        {reset.isSuccess ? (
          <>
            <Alert severity="success">Đã đặt mật khẩu mới. Các thiết bị đang đăng nhập đã bị đăng xuất.</Alert>
            <Button component={Link} href="/login" variant="contained" size="large">
              Đăng nhập
            </Button>
          </>
        ) : linkInvalid ? (
          <>
            <Alert severity="error">
              {token ? errorMessage(reset.error) : "Link thiếu mã. Hãy mở lại đúng link trong email."} Link có hạn 30 phút và
              chỉ dùng được một lần.
            </Alert>
            <Button component={Link} href="/forgot-password" variant="contained" size="large">
              Gửi link mới
            </Button>
          </>
        ) : (
          <>
            {reset.isError && <Alert severity="error">{errorMessage(reset.error)}</Alert>}
            <RHFTextField<ResetPasswordValues>
              name="newPassword"
              label="Mật khẩu mới"
              type="password"
              autoComplete="new-password"
              helperText="8–72 ký tự, có cả chữ và số"
              autoFocus
            />
            <RHFTextField<ResetPasswordValues>
              name="confirmPassword"
              label="Nhập lại mật khẩu mới"
              type="password"
              autoComplete="new-password"
            />
            <Button type="submit" variant="contained" size="large" loading={reset.isPending}>
              Đặt mật khẩu mới
            </Button>
          </>
        )}
        <Typography variant="body2" align="center">
          <MuiLink component={Link} href="/login" color="text.secondary">
            Quay lại đăng nhập
          </MuiLink>
        </Typography>
      </Stack>
    </FormProvider>
  );
}
