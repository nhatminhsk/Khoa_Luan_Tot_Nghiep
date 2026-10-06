"use client";

import { Autocomplete, InputAdornment, TextField } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import { useBanks } from "@/hooks/use-banks";

/** Ô tìm nhanh ngân hàng theo mã hoặc tên; chọn xong mở hồ sơ ngân hàng. */
export function BankSearch() {
  const router = useRouter();
  const { banks, isLoading } = useBanks();

  return (
    <Autocomplete
      size="small"
      options={banks}
      loading={isLoading}
      value={null}
      blurOnSelect
      getOptionLabel={(bank) => `${bank.ticker} · ${bank.shortName}`}
      filterOptions={(options, { inputValue }) => {
        const q = inputValue.trim().toLowerCase();
        return q
          ? options.filter((b) =>
              [b.ticker, b.shortName, b.fullName].some((field) => field.toLowerCase().includes(q)),
            )
          : options;
      }}
      onChange={(_, bank) => bank && router.push(`/banks/${bank.ticker}`)}
      sx={(theme) => ({
        width: { xs: "100%", sm: 320 },
        // Điện thoại: bỏ mũi tên mở danh sách (gõ hoặc chạm là mở) để chữ gợi ý không bị cắt.
        [theme.breakpoints.down("sm")]: {
          "& .MuiAutocomplete-endAdornment": { display: "none" },
          "&.MuiAutocomplete-hasPopupIcon .MuiOutlinedInput-root, &.MuiAutocomplete-hasClearIcon .MuiOutlinedInput-root": { pr: 1 },
        },
      })}
      renderInput={(params) => (
        <TextField
          {...params}
          placeholder="Tìm ngân hàng (mã hoặc tên)"
          slotProps={{
            ...params.slotProps,
            htmlInput: { ...params.slotProps.htmlInput, "aria-label": "Tìm ngân hàng" },
            input: {
              ...params.slotProps.input,
              startAdornment: (
                <InputAdornment position="start">
                  <IconSearch size={18} aria-hidden />
                </InputAdornment>
              ),
            },
          }}
        />
      )}
    />
  );
}
