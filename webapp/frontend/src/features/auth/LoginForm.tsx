"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, IconButton, InputAdornment, Link as MuiLink, Stack, Typography } from "@mui/material";
import { IconEye, IconEyeOff } from "@tabler/icons-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { EmailTypoHint } from "@/components/form/EmailTypoHint";
import { RHFTextField } from "@/components/form/RHFFields";
import { useAuth } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/http/api-error";
import { reloadTo } from "./reload-after-auth";
import { safeNext } from "./safe-next";

const schema = z.object({
  email: z.string().trim().min(1, "Nhập email").email("Email không hợp lệ"),
  password: z.string().min(1, "Nhập mật khẩu"),
});
type LoginValues = z.infer<typeof schema>;

export function LoginForm() {
  const next = safeNext(useSearchParams().get("next"));
  const { login, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const methods = useForm<LoginValues>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
  const email = useWatch({ control: methods.control, name: "email" });

  // Đã có phiên (bấm Back về trang này, mở lại link đăng nhập cũ, hoặc link "Theo dõi" còn nhớ lệnh chuyển hướng từ lúc
  // chưa đăng nhập): tải lại tới trang đích. Không dùng router.replace — xem reload-after-auth.ts.
  useEffect(() => {
    if (isAuthenticated && !login.isSuccess) reloadTo(next);
  }, [isAuthenticated, login.isSuccess, next]);

  const onSubmit = methods.handleSubmit((values) =>
    login.mutate(values, {
      onSuccess: (user) => reloadTo(next, `Xin chào, ${user.displayName}`),
    }),
  );

  return (
    <FormProvider {...methods}>
      <Stack component="form" spacing={2.25} onSubmit={onSubmit} noValidate>
        <div>
          <Typography variant="h2" component="h1">
            Đăng nhập
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Để lưu nhu cầu, theo dõi ngân hàng và nhận thông báo khi lãi suất đổi.
          </Typography>
        </div>
        {login.isError && <Alert severity="error">{errorMessage(login.error)}</Alert>}
        {/* Đăng nhập sai mà email trông như gõ nhầm tên miền thì gợi ý sửa. */}
        {login.isError && (
          <EmailTypoHint email={email} onApply={(s) => methods.setValue("email", s, { shouldValidate: true })} />
        )}
        <RHFTextField<LoginValues> name="email" label="Email" type="email" autoComplete="email" autoFocus />
        <RHFTextField<LoginValues>
          name="password"
          label="Mật khẩu"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          slotProps={{
            input: {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                    onClick={() => setShowPassword((v) => !v)}
                    edge="end"
                  >
                    {showPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
        />
        <MuiLink component={Link} href="/forgot-password" variant="body2" sx={{ alignSelf: "flex-end", mt: -1 }}>
          Quên mật khẩu?
        </MuiLink>
        <Button type="submit" variant="contained" size="large" loading={login.isPending}>
          Đăng nhập
        </Button>
        <Typography variant="body2" align="center">
          Chưa có tài khoản?{" "}
          <MuiLink component={Link} href={`/register?next=${encodeURIComponent(next)}`}>
            Đăng ký
          </MuiLink>
        </Typography>
        <Typography variant="body2" align="center">
          <MuiLink component={Link} href="/" color="text.secondary">
            Tiếp tục xem mà không đăng nhập
          </MuiLink>
        </Typography>
      </Stack>
    </FormProvider>
  );
}
