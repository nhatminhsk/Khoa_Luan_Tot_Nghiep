"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId } from "react";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { EmailTypoHint } from "@/components/form/EmailTypoHint";
import { RHFTextField } from "@/components/form/RHFFields";
import { useNotify } from "@/components/providers/NotifierProvider";
import { ApiError, errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";

const schema = z.object({
  newEmail: z.string().trim().min(1, "Nhập email mới").email("Email không hợp lệ").max(160),
  currentPassword: z.string().min(1, "Nhập mật khẩu hiện tại"),
});
type ChangeEmailValues = z.infer<typeof schema>;

/**
 * Đổi email đăng nhập, ví dụ khi lỡ gõ nhầm "@gamil.com" lúc đăng ký nên không nhận được link xác minh.
 * Cần mật khẩu hiện tại; email mới phải xác minh lại trước khi nhận thông báo qua email.
 */
export function ChangeEmailDialog({ open, onClose, currentEmail }: { open: boolean; onClose: () => void; currentEmail: string }) {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const methods = useForm<ChangeEmailValues>({
    resolver: zodResolver(schema),
    defaultValues: { newEmail: "", currentPassword: "" },
  });
  const newEmail = useWatch({ control: methods.control, name: "newEmail" });
  const titleId = useId();

  const change = useMutation({
    mutationFn: (values: ChangeEmailValues) => meRepository.changeEmail(values),
    onSuccess: (user) => {
      queryClient.setQueryData(queryKeys.me, user);
      // Cài đặt thông báo và trạng thái xác minh đều đổi theo email mới.
      queryClient.invalidateQueries({ queryKey: ["me"] });
      notify(`Đã đổi email thành ${user.email}. Hãy xác minh địa chỉ mới để nhận thông báo qua email.`);
      close();
    },
    onError: (error) => {
      if (!(error instanceof ApiError)) return;
      if (error.code === "WRONG_PASSWORD") methods.setError("currentPassword", { message: error.message });
      else if (error.code === "EMAIL_TAKEN" || error.code === "BAD_REQUEST") methods.setError("newEmail", { message: error.message });
      for (const [field, message] of Object.entries(error.fieldErrors)) {
        if (field === "newEmail" || field === "currentPassword") methods.setError(field as keyof ChangeEmailValues, { message });
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
    (["WRONG_PASSWORD", "EMAIL_TAKEN", "BAD_REQUEST"].includes(change.error.code) || Object.keys(change.error.fieldErrors).length > 0);

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs" aria-labelledby={titleId}>
      <FormProvider {...methods}>
        <form noValidate onSubmit={methods.handleSubmit((values) => change.mutate(values))}>
          <DialogTitle id={titleId}>Đổi email</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 0.5 }}>
              <Typography variant="body2" color="text.secondary">
                Email hiện tại: <strong>{currentEmail}</strong>. Sau khi đổi, bạn đăng nhập bằng email mới và cần xác minh lại
                trước khi nhận thông báo qua email.
              </Typography>
              {change.isError && !fieldHandled && <Alert severity="error">{errorMessage(change.error)}</Alert>}
              <RHFTextField<ChangeEmailValues> name="newEmail" label="Email mới" type="email" autoComplete="email" autoFocus />
              <EmailTypoHint email={newEmail} onApply={(s) => methods.setValue("newEmail", s, { shouldValidate: true })} />
              <RHFTextField<ChangeEmailValues>
                name="currentPassword"
                label="Mật khẩu hiện tại"
                type="password"
                autoComplete="current-password"
              />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={close} disabled={change.isPending}>
              Hủy
            </Button>
            <Button type="submit" variant="contained" loading={change.isPending}>
              Đổi email
            </Button>
          </DialogActions>
        </form>
      </FormProvider>
    </Dialog>
  );
}
