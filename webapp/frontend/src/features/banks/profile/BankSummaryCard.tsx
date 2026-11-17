"use client";

import { Box, Chip, Grid, Stack, Typography } from "@mui/material";
import { IconArrowDownRight, IconArrowUpRight } from "@tabler/icons-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { BankIndicators } from "@/types/api";
import { type Highlight, summarizeBank } from "@/utils/bank-summary";
import { formatQuarter } from "@/utils/format";

/**
 * Tóm tắt nhanh đầu hồ sơ: câu mô tả tự sinh từ số liệu và điểm mạnh/điểm yếu theo thứ hạng từng chỉ tiêu.
 * Không phải điểm tổng hợp: xếp hạng tổng hợp ở trang Gửi tiết kiệm / Vay.
 */
export function BankSummaryCard({ data }: { data: BankIndicators }) {
  const summary = summarizeBank(data);

  return (
    <SectionCard
      title="Tóm tắt nhanh"
      subtitle="Tự động tạo từ số liệu BCTC. Điểm mạnh/yếu là chỉ tiêu nằm trong 3 hạng đầu/cuối của các ngân hàng có số, không phải đánh giá tổng hợp."
    >
      <Stack spacing={2}>
        {summary.sentences.length > 0 && (
          <Stack spacing={0.75}>
            {summary.sentences.map((s) => (
              <Typography key={s} variant="body2">
                {s}
              </Typography>
            ))}
          </Stack>
        )}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <HighlightList
              title="Điểm mạnh"
              icon={<IconArrowUpRight size={16} aria-hidden />}
              color="success"
              items={summary.strengths}
              empty="Không có chỉ tiêu nào trong 3 hạng đầu."
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <HighlightList
              title="Điểm yếu"
              icon={<IconArrowDownRight size={16} aria-hidden />}
              color="error"
              items={summary.weaknesses}
              empty="Không có chỉ tiêu nào trong 3 hạng cuối."
            />
          </Grid>
        </Grid>
      </Stack>
    </SectionCard>
  );
}

function HighlightList({
  title,
  icon,
  color,
  items,
  empty,
}: {
  title: string;
  icon: React.ReactNode;
  color: "success" | "error";
  items: Highlight[];
  empty: string;
}) {
  return (
    <Box>
      <Stack direction="row" spacing={0.75} sx={{ alignItems: "center", mb: 1, color: `${color}.main` }}>
        {icon}
        <Typography variant="subtitle2" component="h3" sx={{ color: "text.primary" }}>
          {title}
        </Typography>
      </Stack>
      {items.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {empty}
        </Typography>
      ) : (
        <Stack direction="row" useFlexGap sx={{ flexWrap: "wrap", gap: 1 }}>
          {items.map((h) => (
            <Chip
              key={h.code}
              variant="outlined"
              color={color}
              label={`${h.label} · hạng ${h.rank}/${h.bankCount}`}
              title={`Số liệu ${formatQuarter(h.period)}`}
            />
          ))}
        </Stack>
      )}
    </Box>
  );
}
