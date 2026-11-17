"use client";

import { Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from "@mui/material";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useNotify } from "@/components/providers/NotifierProvider";
import { useAuth } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";
import type { SavedNeedRequest } from "@/types/api";

/** Lưu tiêu chí đang xem thành "nhu cầu" để mở lại nhanh ở trang Theo dõi. Chưa đăng nhập thì dẫn tới đăng nhập. */
export function SaveNeedButton({ need, defaultLabel }: { need: Omit<SavedNeedRequest, "label">; defaultLabel: string }) {
  const { isAuthenticated } = useAuth();
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState(defaultLabel);
  const notify = useNotify();
  const queryClient = useQueryClient();

  const save = useMutation({
    mutationFn: () => meRepository.createNeed({ ...need, label: label.trim() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.needs });
      notify("Đã lưu nhu cầu. Mở lại ở trang Theo dõi và thông báo.");
      setOpen(false);
    },
    onError: (error) => notify(errorMessage(error), "error"),
  });

  if (!isAuthenticated) {
    const next = `${pathname}${search ? `?${search}` : ""}`;
    return (
      <Button component={Link} href={`/login?next=${encodeURIComponent(next)}`} variant="outlined" startIcon={<IconDeviceFloppy size={18} />}>
        Đăng nhập để lưu
      </Button>
    );
  }

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<IconDeviceFloppy size={18} />}
        onClick={() => {
          setLabel(defaultLabel);
          setOpen(true);
        }}
      >
        Lưu nhu cầu
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Lưu nhu cầu</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Chỉ lưu tiêu chí tìm kiếm (số tiền, kỳ hạn, kênh), không lưu thông tin tài chính cá nhân.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            label="Tên gợi nhớ"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            slotProps={{ htmlInput: { maxLength: 80 } }}
            error={label.trim().length === 0}
            helperText={label.trim().length === 0 ? "Đặt tên cho nhu cầu" : " "}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setOpen(false)}>Hủy</Button>
          <Button variant="contained" onClick={() => save.mutate()} loading={save.isPending} disabled={label.trim().length === 0}>
            Lưu
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
