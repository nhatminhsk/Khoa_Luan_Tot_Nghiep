"use client";

import { ToggleButton, ToggleButtonGroup } from "@mui/material";

/** Nút chọn khoảng thời gian cho biểu đồ (1T, 3T, ..., Tất cả). Nhãn viết tắt có tên đầy đủ ở aria-label/title. */
export function PeriodToggle<T extends string>({
  value,
  options,
  onChange,
  ariaLabel = "Khoảng thời gian",
}: {
  value: T;
  options: { value: T; label: string; title: string }[];
  onChange: (value: T) => void;
  ariaLabel?: string;
}) {
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={value}
      onChange={(_, v: T | null) => v !== null && onChange(v)}
      aria-label={ariaLabel}
      sx={{ flexWrap: "wrap" }}
    >
      {options.map((o) => (
        <ToggleButton key={o.value} value={o.value} aria-label={o.title} title={o.title} sx={{ px: 1.5 }}>
          {o.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
