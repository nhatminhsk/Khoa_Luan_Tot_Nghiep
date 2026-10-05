import { Box, Typography } from "@mui/material";
import { IconArrowDownRight, IconArrowUpRight, IconMinus } from "@tabler/icons-react";
import { formatDelta } from "@/utils/format";

/**
 * Thay đổi lãi suất so với ngày trước. Hướng thể hiện bằng mũi tên + dấu, màu chỉ là phụ
 * (người mù màu vẫn đọc được). Với người gửi tiền, lãi tăng là tin tốt nên dùng màu "success".
 */
export function RateDelta({
  value,
  unit = "điểm %",
  showZero = false,
}: {
  value: number | null | undefined;
  unit?: string;
  /** Mặc định ẩn khi không đổi để bảng nhiều dòng không bị rối; chỉ hiện khi có thay đổi thật. */
  showZero?: boolean;
}) {
  if (value === null || value === undefined || (value === 0 && !showZero)) return null;
  const up = value > 0;
  const down = value < 0;
  const Icon = up ? IconArrowUpRight : down ? IconArrowDownRight : IconMinus;
  const label = up ? `tăng ${formatDelta(value)} ${unit}` : down ? `giảm ${formatDelta(-value)} ${unit}` : "không đổi";

  return (
    <Box
      component="span"
      aria-label={label}
      title={label}
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.25,
        color: up ? "success.main" : down ? "error.main" : "text.secondary",
        whiteSpace: "nowrap",
      }}
    >
      <Icon size={14} stroke={2} aria-hidden />
      <Typography component="span" variant="caption" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
        {value === 0 ? "0" : formatDelta(value)}
      </Typography>
    </Box>
  );
}
