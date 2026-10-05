"use client";

import { Alert, AlertTitle, Box, Button, Skeleton, Stack, Typography } from "@mui/material";
import { IconHourglassHigh, IconInbox, IconRefresh } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { errorMessage } from "@/lib/http/api-error";

/** Khung chờ giữ đúng chiều cao nội dung để trang không nhảy khi dữ liệu về. */
export function LoadingBlock({ height = 240, label = "Đang tải dữ liệu" }: { height?: number; label?: string }) {
  return (
    <Box role="status" aria-label={label}>
      <Skeleton variant="rounded" height={height} />
    </Box>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Alert
      severity="error"
      action={
        onRetry && (
          <Button color="inherit" size="small" startIcon={<IconRefresh size={16} />} onClick={onRetry}>
            Thử lại
          </Button>
        )
      }
    >
      <AlertTitle>Không tải được dữ liệu</AlertTitle>
      {errorMessage(error)}
    </Alert>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) {
  return (
    <Stack spacing={1} sx={{ alignItems: "center", py: 5, px: 2, textAlign: "center" }}>
      <Box sx={{ color: "text.secondary" }}>
        <IconInbox size={32} stroke={1.5} aria-hidden />
      </Box>
      <Typography variant="subtitle1">{title}</Typography>
      {description && (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 460 }}>
          {description}
        </Typography>
      )}
      {action}
    </Stack>
  );
}

/**
 * Chỗ dành cho kết quả thuật toán (xếp hạng, dự báo, khía cạnh review) khi pipeline chưa ghi kết quả.
 * Đây là trạng thái bình thường của hệ thống lúc này, không phải lỗi.
 */
export function PendingResult({ title, description, compact }: { title: string; description: ReactNode; compact?: boolean }) {
  return (
    <Stack
      direction="row"
      spacing={1.75}
      sx={{
        p: compact ? 2 : 2.5,
        borderRadius: 2,
        bgcolor: "action.hover",
        border: 1,
        borderColor: "divider",
      }}
    >
      <Box sx={{ color: "primary.main", pt: 0.25 }}>
        <IconHourglassHigh size={22} stroke={1.7} aria-hidden />
      </Box>
      <Box>
        <Typography variant="subtitle1">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 680 }}>
          {description}
        </Typography>
      </Box>
    </Stack>
  );
}
