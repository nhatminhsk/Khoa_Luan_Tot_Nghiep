"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Button, Chip, Grid, Stack } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { FormProvider, useForm } from "react-hook-form";
import { RHFMoneyField, RHFSelect, RHFToggle, UnappliedHint } from "@/components/form/RHFFields";
import type { SavingsAdviceRequest } from "@/types/api";
import { formatVndCompact } from "@/utils/format";
import { CHANNEL_LABEL, SAVINGS_TERMS } from "@/utils/labels";
import { DEFAULT_WEIGHTS, normalizedWeights, savingsSchema, type SavingsFormValues } from "./savings-params";

const QUICK_AMOUNTS = [50_000_000, 100_000_000, 500_000_000, 1_000_000_000];

interface SavingsFormProps {
  initial: SavingsAdviceRequest;
  onSubmit: (values: SavingsAdviceRequest) => void;
  submitting: boolean;
}

export function SavingsForm({ initial, onSubmit, submitting }: SavingsFormProps) {
  const methods = useForm<SavingsFormValues>({
    resolver: zodResolver(savingsSchema),
    // Trọng số không còn chọn tay: xếp hạng lấy trọng số an toàn theo phần tiền vượt hạn mức bảo hiểm tiền gửi. weights giữ
    // trong giá trị form để link cũ và nhu cầu đã lưu vẫn mở được.
    defaultValues: { ...initial, weights: normalizedWeights(initial.weights ?? DEFAULT_WEIGHTS) },
  });

  return (
    <FormProvider {...methods}>
      {/* Thanh lọc ngang: lg một hàng số tiền | kỳ hạn | kênh | xem kết quả (4/2/4/2); iPad hai hàng; điện thoại xếp dọc. */}
      <Box component="form" noValidate onSubmit={methods.handleSubmit((values) => onSubmit(values))}>
        <Grid container spacing={2} sx={{ alignItems: "flex-start" }}>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
            <RHFMoneyField<SavingsFormValues> name="amount" label="Số tiền gửi" />
            <Stack direction="row" spacing={0.75} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>
              {QUICK_AMOUNTS.map((value) => (
                <Chip
                  key={value}
                  label={formatVndCompact(value)}
                  size="small"
                  variant="outlined"
                  clickable
                  onClick={() => methods.setValue("amount", value, { shouldValidate: true, shouldDirty: true })}
                />
              ))}
            </Stack>
          </Grid>

          <Grid size={{ xs: 5, sm: 3, lg: 2 }}>
            <RHFSelect<SavingsFormValues, number>
              name="termMonths"
              label="Kỳ hạn"
              options={SAVINGS_TERMS.map((t) => ({ value: t, label: `${t} tháng` }))}
            />
          </Grid>

          <Grid size={{ xs: 7, sm: 3, lg: 4 }}>
            <RHFToggle<SavingsFormValues, "ONLINE" | "COUNTER">
              name="channel"
              label="Kênh gửi"
              inline
              options={(["ONLINE", "COUNTER"] as const).map((c) => ({ value: c, label: CHANNEL_LABEL[c] }))}
              helperText="Trực tuyến thường lãi cao hơn."
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 12, lg: 2 }}>
            <Button type="submit" variant="contained" size="large" fullWidth startIcon={<IconSearch size={18} />} loading={submitting} sx={{ minHeight: 56 }}>
              Xem kết quả
            </Button>
            <UnappliedHint show={methods.formState.isDirty} />
          </Grid>
        </Grid>
      </Box>
    </FormProvider>
  );
}
