"use client";

import { Box, Stack, Typography } from "@mui/material";
import { IconBuildingBank } from "@tabler/icons-react";
import Link from "next/link";
import { siteConfig } from "@/config/site";

export function BrandMark() {
  return (
    <Stack
      component={Link}
      href="/"
      direction="row"
      spacing={1.25}
      sx={{ alignItems: "center", color: "text.primary", textDecoration: "none", minHeight: 44 }}
      aria-label={`${siteConfig.name} — về trang tổng quan`}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: 2,
          bgcolor: "primary.main",
          color: "primary.contrastText",
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        <IconBuildingBank size={20} stroke={1.8} aria-hidden />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="subtitle1" component="span" sx={{ display: "block", lineHeight: 1.2 }}>
          {siteConfig.name}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.3 }}>
          {siteConfig.tagline}
        </Typography>
      </Box>
    </Stack>
  );
}
