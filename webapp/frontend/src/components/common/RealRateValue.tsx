import { Typography, type TypographyProps } from "@mui/material";
import { formatDelta } from "@/utils/format";

/** Lãi suất thực có dấu (+2,31% / −0,40%): xanh khi dương (giữ được sức mua), đỏ khi âm. */
export function RealRateValue({ value, variant = "body2" }: { value: number | null; variant?: TypographyProps["variant"] }) {
  if (value === null) return <>—</>;
  return (
    <Typography
      component="span"
      variant={variant}
      sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums", color: value >= 0 ? "success.main" : "error.main" }}
    >
      {formatDelta(value)}%
    </Typography>
  );
}
