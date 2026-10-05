"use client";

import { Box, Stack, Tooltip, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { formatDate, formatQuarter } from "@/utils/format";

/**
 * Chấm trạng thái ở thanh trên: dữ liệu lãi suất mới tới ngày nào, số liệu tài chính tới quý nào.
 * Dùng chung cache với trang Tổng quan nên không gọi thêm API khi đã có.
 */
export function DataStatusChip() {
  const { data } = useQuery({ queryKey: queryKeys.overview, queryFn: marketRepository.overview, staleTime: 5 * 60_000 });
  if (!data?.rateDate) return null;

  return (
    <Tooltip title={`Lãi suất cập nhật hằng ngày sau 15:30. Số liệu tài chính mới nhất: ${formatQuarter(data.latestQuarter)}.`}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          display: { xs: "none", lg: "flex" },
          alignItems: "center",
          px: 1.5,
          height: 34,
          borderRadius: 999,
          border: 1,
          borderColor: "divider",
          color: "text.secondary",
          whiteSpace: "nowrap",
        }}
      >
        <Box
          aria-hidden
          sx={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            bgcolor: "success.main",
            boxShadow: (t) => (t.vars ? `0 0 0 3px rgba(${t.vars.palette.success.mainChannel} / 0.2)` : "none"),
          }}
        />
        <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
          Dữ liệu ngày {formatDate(data.rateDate)} · BCTC {formatQuarter(data.latestQuarter)}
        </Typography>
      </Stack>
    </Tooltip>
  );
}
