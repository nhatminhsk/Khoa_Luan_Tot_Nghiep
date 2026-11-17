"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { z } from "zod";
import { RHFTextField } from "@/components/form/RHFFields";
import { useNotify } from "@/components/providers/NotifierProvider";
import { newPasswordSchema } from "@/features/auth/password-rules";
import { ApiError, errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";

const schema = z
  .object({
    currentPassword: z.string().min(1, "Nhập mật khẩu hiện tại"),
    newPassword: newPasswordSchema,
    confirmPassword: z.string(),
  })
  .refine((v) => v.newPassword === v.confirmPassword, { path: ["confirmPassword"], message: "Mật khẩu nhập lại không khớp" });
type ChangePasswordValues = z.infer<typeof schema>;

/** Đổi mật khẩu. Các thiết bị khác bị đăng xuất; trình duyệt này vẫn đăng nhập (backend cấp cookie phiên mới). */
export function ChangePasswordDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const methods = useForm<ChangePasswordValues>({
    resolver: zodResolver(schema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
  });
  const titleId = useId();

  const change = useMutation({
    mutationFn: ({ currentPassword, newPassword }: ChangePasswordValues) =>
      meRepository.changePassword({ currentPassword, newPassword }),
    onSuccess: (user) => {
      queryClient.setQueryData(queryKeys.me, user);
      notify("Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất.");
      close();
    },
    onError: (error) => {
      if (!(error instanceof ApiError)) return;
      if (error.code === "WRONG_PASSWORD") methods.setError("currentPassword", { message: error.message });
      else if (error.code === "BAD_REQUEST") methods.setError("newPassword", { message: error.message });
      for (const [field, message] of Object.entries(error.fieldErrors)) {
        if (field === "currentPassword" || field === "newPassword") methods.setError(field, { message });
      }
    },
  });

  const close = () => {
    methods.reset();
    change.reset();
    onClose();
  };

  const fieldHandled =
    change.error instanceof ApiError &&
    (["WRONG_PASSWORD", "BAD_REQUEST"].includes(change.error.code) || Object.keys(change.error.fieldErrors).length > 0);

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs" aria-labelledby={titleId}>
      <FormProvider {...methods}>
        <form noValidate onSubmit={methods.handleSubmit((values) => change.mutate(values))}>
          <DialogTitle id={titleId}>Đổi mật khẩu</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 0.5 }}>
              <Typography variant="body2" color="text.secondary">
                Đổi xong, các thiết bị khác đang đăng nhập tài khoản này sẽ bị đăng xuất; trình duyệt này vẫn giữ đăng nhập.
              </Typography>
              {change.isError && !fieldHandled && <Alert severity="error">{errorMessage(change.error)}</Alert>}
              <RHFTextField<ChangePasswordValues>
                name="currentPassword"
                label="Mật khẩu hiện tại"
                type="password"
                autoComplete="current-password"
                autoFocus
              />
              <RHFTextField<ChangePasswordValues>
                name="newPassword"
                label="Mật khẩu mới"
                type="password"
                autoComplete="new-password"
                helperText="8–72 ký tự, có cả chữ và số"
              />
              <RHFTextField<ChangePasswordValues>
                name="confirmPassword"
                label="Nhập lại mật khẩu mới"
                type="password"
                autoComplete="new-password"
              />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={close} disabled={change.isPending}>
              Hủy
            </Button>
            <Button type="submit" variant="contained" loading={change.isPending}>
              Đổi mật khẩu
            </Button>
          </DialogActions>
        </form>
      </FormProvider>
    </Dialog>
  );
}
