"use client";

import {
  FormControl,
  FormHelperText,
  FormLabel,
  MenuItem,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  type TextFieldProps,
} from "@mui/material";
import { visuallyHidden } from "@mui/utils";
import type { ReactNode } from "react";
import { NumericFormat } from "react-number-format";
import { Controller, useFormContext, type FieldValues, type Path } from "react-hook-form";

/**
 * Ô nhập gắn với react-hook-form. Lỗi hiện ngay dưới ô (không gom lên đầu form),
 * nhãn luôn hiển thị (không dùng placeholder thay nhãn).
 */

type BaseProps<T extends FieldValues> = { name: Path<T>; label: string; helperText?: ReactNode };

export function RHFTextField<T extends FieldValues>({
  name,
  label,
  helperText,
  ...rest
}: BaseProps<T> & Omit<TextFieldProps, "name" | "label">) {
  const { control } = useFormContext<T>();
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <TextField
          {...field}
          {...rest}
          label={label}
          fullWidth
          error={!!fieldState.error}
          helperText={fieldState.error?.message ?? helperText}
        />
      )}
    />
  );
}

/** Ô nhập tiền: tự thêm dấu chấm hàng nghìn, lưu giá trị số nguyên (đồng). */
export function RHFMoneyField<T extends FieldValues>({ name, label, helperText }: BaseProps<T>) {
  const { control } = useFormContext<T>();
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <NumericFormat
          customInput={TextField}
          label={label}
          fullWidth
          value={field.value ?? ""}
          onValueChange={(values) => field.onChange(values.floatValue ?? null)}
          onBlur={field.onBlur}
          inputRef={field.ref}
          name={field.name}
          thousandSeparator="."
          decimalSeparator=","
          decimalScale={0}
          allowNegative={false}
          suffix=" ₫"
          inputMode="numeric"
          error={!!fieldState.error}
          helperText={fieldState.error?.message ?? helperText}
        />
      )}
    />
  );
}

export interface Option<V extends string | number> {
  value: V;
  label: string;
}

export function RHFSelect<T extends FieldValues, V extends string | number>({
  name,
  label,
  helperText,
  options,
}: BaseProps<T> & { options: Option<V>[] }) {
  const { control } = useFormContext<T>();
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <TextField
          {...field}
          select
          fullWidth
          label={label}
          error={!!fieldState.error}
          helperText={fieldState.error?.message ?? helperText}
        >
          {options.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  );
}

/**
 * Chọn một trong vài lựa chọn ngắn (kênh gửi, cách trả nợ).
 * `inline`: dùng trong thanh lọc ngang — nhãn chỉ còn cho trình đọc màn hình, nút cao 56px bằng ô nhập bên cạnh.
 */
export function RHFToggle<T extends FieldValues, V extends string | number>({
  name,
  label,
  helperText,
  options,
  inline = false,
}: BaseProps<T> & { options: Option<V>[]; inline?: boolean }) {
  const { control } = useFormContext<T>();
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <FormControl error={!!fieldState.error} fullWidth>
          <FormLabel sx={inline ? visuallyHidden : { mb: 0.75, fontSize: "0.875rem" }}>{label}</FormLabel>
          <ToggleButtonGroup
            exclusive
            fullWidth
            size="small"
            color="primary"
            value={field.value}
            onChange={(_, value) => value !== null && field.onChange(value)}
            aria-label={label}
          >
            {options.map((option) => (
              <ToggleButton key={option.value} value={option.value} sx={{ minHeight: inline ? 50 : 40, lineHeight: 1.25 }}>
                {option.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          {(fieldState.error?.message ?? helperText) && (
            <FormHelperText>{fieldState.error?.message ?? helperText}</FormHelperText>
          )}
        </FormControl>
      )}
    />
  );
}

/**
 * Dòng nhắc dưới nút gửi khi tiêu chí trên form đã sửa mà chưa bấm: kết quả và nút "Lưu nhu cầu" vẫn theo tiêu chí trên URL.
 */
export function UnappliedHint({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <Typography variant="caption" color="warning.main" role="status" sx={{ display: "block", mt: 1, textAlign: "center" }}>
      Chưa áp dụng — bấm Xem kết quả trước khi lưu nhu cầu.
    </Typography>
  );
}
