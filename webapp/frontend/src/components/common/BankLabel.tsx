"use client";

import { Avatar, Box, Link as MuiLink, Stack, Typography } from "@mui/material";
import Link from "next/link";

/** Logo chữ trung tính (không dùng màu định danh của biểu đồ để khỏi nhầm với chú giải). */
export function BankAvatar({ ticker, size = 32 }: { ticker: string; size?: number }) {
  return (
    <Avatar
      variant="rounded"
      sx={{
        width: size,
        height: size,
        fontSize: size * 0.34,
        fontWeight: 700,
        bgcolor: "action.selected",
        color: "text.primary",
        letterSpacing: "0.02em",
      }}
      aria-hidden
    >
      {ticker}
    </Avatar>
  );
}

interface BankLabelProps {
  ticker: string;
  shortName: string;
  /** Mặc định có link tới hồ sơ ngân hàng. */
  link?: boolean;
  secondary?: string;
}

export function BankLabel({ ticker, shortName, link = true, secondary }: BankLabelProps) {
  const name = (
    <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }} component="span">
      {shortName}
    </Typography>
  );
  return (
    <Stack direction="row" spacing={{ xs: 0, sm: 1.25 }} sx={{ alignItems: "center", minWidth: 0 }}>
      {/* Điện thoại: bỏ logo chữ (mã đã có ở dòng dưới) để bảng vừa màn hình. */}
      <Box sx={{ display: { xs: "none", sm: "flex" } }}>
        <BankAvatar ticker={ticker} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        {link ? (
          <MuiLink component={Link} href={`/banks/${ticker}`} underline="hover" color="inherit">
            {name}
          </MuiLink>
        ) : (
          name
        )}
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.3 }}>
          {secondary ?? ticker}
        </Typography>
      </Box>
    </Stack>
  );
}
