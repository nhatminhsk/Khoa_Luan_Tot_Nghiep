"use client";

import { Alert, AlertTitle, Box, Button, Collapse, Skeleton, Stack, Typography, type SxProps, type Theme } from "@mui/material";
import { IconHourglassHigh, IconInbox, IconRefresh } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import { errorMessage } from "@/lib/http/api-error";

/** Khung chờ giữ đúng chiều cao nội dung để trang không nhảy khi dữ liệu về. */
export function LoadingBlock({ height = 240, label = "Đang tải dữ liệu" }: { height?: number; label?: string }) {
  return (
    <Box role="status" aria-label={label}>
      <Skeleton variant="rounded" height={height} />
    </Box>
  );
}

/** Dòng nhỏ khi đang tải kết quả mới mà vẫn hiện tạm kết quả cũ (mờ đi): nói rõ số đang thấy chưa theo tiêu chí mới. */
export function UpdatingNote({ sx }: { sx?: SxProps<Theme> }) {
  return (
    <Typography variant="caption" color="text.secondary" role="status" sx={{ display: "block", ...sx }}>
      Đang cập nhật kết quả theo tiêu chí mới…
    </Typography>
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

interface PendingResultProps {
  title: string;
  description: ReactNode;
  compact?: boolean;
  /** Giải thích dài, ẩn sau nút "Xem thêm" để khối chờ chỉ chiếm một dòng phía trên kết quả thật. */
  details?: ReactNode;
}

/**
 * Chỗ dành cho kết quả thuật toán xếp hạng khi chưa có kết quả.
 * Đây là trạng thái bình thường của hệ thống lúc này, không phải lỗi.
 */
export function PendingResult({ title, description, compact, details }: PendingResultProps) {
  const [open, setOpen] = useState(false);
  const dense = Boolean(details);
  return (
    <Stack
      direction="row"
      spacing={dense ? 1.25 : 1.75}
      sx={{
        p: dense ? { xs: 1.5, sm: 1.75 } : compact ? 2 : 2.5,
        borderRadius: 2,
        bgcolor: "action.hover",
        border: 1,
        borderColor: "divider",
      }}
    >
      <Box sx={{ color: "primary.main", pt: dense ? 0.125 : 0.25 }}>
        <IconHourglassHigh size={dense ? 20 : 22} stroke={1.7} aria-hidden />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant={dense ? "subtitle2" : "subtitle1"} component="p">
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: dense ? 0.25 : 0.5, maxWidth: 680 }}>
          {description}
        </Typography>
        {details && (
          <>
            <Collapse in={open}>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, maxWidth: 680 }}>
                {details}
              </Typography>
            </Collapse>
            <Button size="small" onClick={() => setOpen((v) => !v)} aria-expanded={open} sx={{ mt: 0.5, ml: -1, minHeight: 32 }}>
              {open ? "Thu gọn" : "Xem thêm"}
            </Button>
          </>
        )}
      </Box>
    </Stack>
  );
}
