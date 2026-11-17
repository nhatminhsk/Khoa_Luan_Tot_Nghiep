"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { EmailTypoHint } from "@/components/form/EmailTypoHint";
import { RHFTextField } from "@/components/form/RHFFields";
import { useAuth } from "@/hooks/use-auth";
import { ApiError, errorMessage } from "@/lib/http/api-error";
import { newPasswordSchema } from "./password-rules";
import { reloadTo } from "./reload-after-auth";
import { safeNext } from "./safe-next";

// Cùng quy tắc với RegisterRequest bên backend; backend vẫn kiểm tra lại.
const schema = z
  .object({
    displayName: z.string().trim().min(1, "Nhập tên hiển thị").max(80, "Tên tối đa 80 ký tự"),
    email: z.string().trim().min(1, "Nhập email").email("Email không hợp lệ").max(160),
    password: newPasswordSchema,
    confirmPassword: z.string(),
  })
  .refine((v) => v.password === v.confirmPassword, { path: ["confirmPassword"], message: "Mật khẩu nhập lại không khớp" });
type RegisterValues = z.infer<typeof schema>;

export function RegisterForm() {
  const next = safeNext(useSearchParams().get("next"));
  const { register, isAuthenticated } = useAuth();

  // Đã đăng nhập thì không đăng ký thêm tài khoản từ phiên này: tải lại tới trang đích (xem reload-after-auth.ts).
  useEffect(() => {
    if (isAuthenticated && !register.isSuccess) reloadTo(next);
  }, [isAuthenticated, register.isSuccess, next]);
  const methods = useForm<RegisterValues>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: "", email: "", password: "", confirmPassword: "" },
  });
  const email = useWatch({ control: methods.control, name: "email" });
  const touchedEmail = methods.formState.touchedFields.email;

  const onSubmit = methods.handleSubmit(({ displayName, email, password }) =>
    register.mutate(
      { displayName, email, password },
      {
        onSuccess: () => reloadTo(next, "Đã tạo tài khoản"),
        onError: (error) => {
          // Lỗi theo từng trường từ backend hiện ngay dưới ô tương ứng.
          if (error instanceof ApiError) {
            for (const [field, message] of Object.entries(error.fieldErrors)) {
              if (field in methods.getValues()) methods.setError(field as keyof RegisterValues, { message });
            }
          }
        },
      },
    ),
  );

  return (
    <FormProvider {...methods}>
      <Stack component="form" spacing={2.25} onSubmit={onSubmit} noValidate>
        <div>
          <Typography variant="h2" component="h1">
            Tạo tài khoản
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Miễn phí. Xem xếp hạng và hồ sơ ngân hàng không cần tài khoản.
          </Typography>
        </div>
        {register.isError && <Alert severity="error">{errorMessage(register.error)}</Alert>}
        <RHFTextField<RegisterValues> name="displayName" label="Tên hiển thị" autoComplete="nickname" autoFocus />
        <Stack spacing={1}>
          <RHFTextField<RegisterValues>
            name="email"
            label="Email"
            type="email"
            autoComplete="email"
            helperText="Dùng để đăng nhập và nhận thông báo; cần xác minh trước khi nhận qua email."
          />
          {/* Chỉ gợi ý sau khi rời ô (hoặc đã bấm tạo), tránh nhấp nháy khi đang gõ dở "@gmail.c". */}
          {(touchedEmail || methods.formState.isSubmitted) && (
            <EmailTypoHint email={email} onApply={(s) => methods.setValue("email", s, { shouldValidate: true })} />
          )}
        </Stack>
        <RHFTextField<RegisterValues>
          name="password"
          label="Mật khẩu"
          type="password"
          autoComplete="new-password"
          helperText="Ít nhất 8 ký tự, gồm cả chữ và số"
        />
        <RHFTextField<RegisterValues> name="confirmPassword" label="Nhập lại mật khẩu" type="password" autoComplete="new-password" />
        <Button type="submit" variant="contained" size="large" loading={register.isPending}>
          Tạo tài khoản
        </Button>
        <Typography variant="body2" align="center">
          Đã có tài khoản?{" "}
          <MuiLink component={Link} href={`/login?next=${encodeURIComponent(next)}`}>
            Đăng nhập
          </MuiLink>
        </Typography>
      </Stack>
    </FormProvider>
  );
}
