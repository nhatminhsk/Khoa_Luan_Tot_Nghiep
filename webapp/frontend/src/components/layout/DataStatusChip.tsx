"use client";

import { Box, Stack, Tooltip, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { formatDate, formatQuarter } from "@/utils/format";
import { daysSince } from "@/utils/today";

/** Lãi suất cũ hơn chừng này ngày (lỡ crawl, nguồn đứng yên) thì chấm chuyển màu cảnh báo. */
const STALE_DAYS = 2;

/**
 * Chấm trạng thái ở thanh trên: dữ liệu lãi suất mới tới ngày nào, số liệu tài chính tới quý nào.
 * Chấm xanh chỉ khi lãi suất có số trong STALE_DAYS ngày gần đây (theo giờ Việt Nam; crawl chạy hằng ngày sau 15:30, cho phép
 * lỡ một ngày); cũ hơn thì vàng — không để chấm xanh khi dữ liệu đã cũ.
 * Dùng chung cache với trang Tổng quan nên không gọi thêm API khi đã có.
 */
export function DataStatusChip() {
  const { data } = useQuery({ queryKey: queryKeys.overview, queryFn: marketRepository.overview, staleTime: 5 * 60_000 });
  if (!data?.rateDate) return null;
  const ageDays = daysSince(data.rateDate);
  const stale = ageDays > STALE_DAYS;

  return (
    <Tooltip
      title={`${stale ? `Chưa có số lãi suất mới sau ngày ${formatDate(data.rateDate)}. ` : ""}Lãi suất cập nhật hằng ngày sau 15:30. Số liệu tài chính mới nhất: ${formatQuarter(data.latestQuarter)}.`}
    >
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
            bgcolor: stale ? "warning.main" : "success.main",
            boxShadow: (t) => {
              if (!t.vars) return "none";
              const channel = stale ? t.vars.palette.warning.mainChannel : t.vars.palette.success.mainChannel;
              return `0 0 0 3px rgba(${channel} / 0.2)`;
            },
          }}
        />
        <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
          Dữ liệu ngày {formatDate(data.rateDate)} · BCTC {formatQuarter(data.latestQuarter)}
        </Typography>
      </Stack>
    </Tooltip>
  );
}
