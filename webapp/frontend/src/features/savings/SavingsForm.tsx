"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Button, Chip, FormHelperText, Slider, Stack, Typography } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { useId } from "react";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { RHFMoneyField, RHFSelect, RHFToggle } from "@/components/form/RHFFields";
import type { SavingsAdviceRequest } from "@/types/api";
import { formatVndCompact } from "@/utils/format";
import { CHANNEL_LABEL, SAVINGS_TERMS } from "@/utils/labels";
import { DEFAULT_WEIGHTS, normalizedWeights, rebalanceWeights, savingsSchema, type SavingsFormValues } from "./savings-params";

const QUICK_AMOUNTS = [50_000_000, 100_000_000, 500_000_000, 1_000_000_000];

const WEIGHT_FIELDS = [
  { key: "rate", label: "Lãi suất cao", hint: "Nhận nhiều tiền lãi hơn" },
  { key: "safety", label: "Ngân hàng an toàn", hint: "Vốn, nợ xấu, thanh khoản tốt" },
  { key: "app", label: "Ứng dụng dễ dùng", hint: "Điểm đánh giá ứng dụng" },
] as const;

interface SavingsFormProps {
  initial: SavingsAdviceRequest;
  onSubmit: (values: SavingsAdviceRequest) => void;
  submitting: boolean;
}

export function SavingsForm({ initial, onSubmit, submitting }: SavingsFormProps) {
  const methods = useForm<SavingsFormValues>({
    resolver: zodResolver(savingsSchema),
    defaultValues: { ...initial, weights: normalizedWeights(initial.weights ?? DEFAULT_WEIGHTS) },
  });
  const weights = useWatch({ control: methods.control, name: "weights" });
  // Ba thanh liên kết, tổng luôn 100%: kéo một thanh thì hai thanh kia chia phần còn lại theo tỉ lệ đang có.
  const changeWeight = (key: (typeof WEIGHT_FIELDS)[number]["key"], value: number) =>
    methods.setValue("weights", rebalanceWeights(weights, key, value), { shouldDirty: true });
  // id duy nhất cho nhãn của thanh trượt (không viết cứng, tránh trùng id khi form xuất hiện hai lần).
  const idPrefix = useId();

  return (
    <FormProvider {...methods}>
      <Stack component="form" spacing={2.5} noValidate onSubmit={methods.handleSubmit((values) => onSubmit(values))}>
        <Box>
          <RHFMoneyField<SavingsFormValues> name="amount" label="Số tiền gửi" />
          <Stack direction="row" spacing={0.75} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>
            {QUICK_AMOUNTS.map((value) => (
              <Chip
                key={value}
                label={formatVndCompact(value)}
                size="small"
                variant="outlined"
                clickable
                onClick={() => methods.setValue("amount", value, { shouldValidate: true })}
              />
            ))}
          </Stack>
        </Box>

        <RHFSelect<SavingsFormValues, number>
          name="termMonths"
          label="Kỳ hạn"
          options={SAVINGS_TERMS.map((t) => ({ value: t, label: `${t} tháng` }))}
        />

        <RHFToggle<SavingsFormValues, "ONLINE" | "COUNTER">
          name="channel"
          label="Kênh gửi"
          options={(["ONLINE", "COUNTER"] as const).map((c) => ({ value: c, label: CHANNEL_LABEL[c] }))}
          helperText="Gửi trực tuyến thường có lãi cao hơn tại quầy."
        />

        <Box>
          <Typography variant="subtitle2" component="h3">
            Bạn ưu tiên điều gì?
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Dùng để tính xếp hạng tổng hợp theo nhu cầu của bạn. Ba mức luôn cộng lại 100%: tăng một mức thì hai mức kia
            giảm theo.
          </Typography>
          <Stack spacing={1.5} sx={{ mt: 1.5 }}>
            {WEIGHT_FIELDS.map((field) => (
              <Box key={field.key}>
                <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "baseline" }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }} id={`${idPrefix}-${field.key}`}>
                    {field.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {weights[field.key]}%
                  </Typography>
                </Stack>
                <Slider
                  value={weights[field.key]}
                  onChange={(_, value) => changeWeight(field.key, value as number)}
                  min={0}
                  max={100}
                  step={1}
                  shiftStep={10}
                  aria-labelledby={`${idPrefix}-${field.key}`}
                  getAriaValueText={(value) => `${value}% mức ưu tiên`}
                  size="small"
                />
                <Typography variant="caption" color="text.secondary">
                  {field.hint}
                </Typography>
              </Box>
            ))}
            {methods.formState.errors.weights?.message && (
              <FormHelperText error>{methods.formState.errors.weights.message}</FormHelperText>
            )}
          </Stack>
        </Box>

        <Button type="submit" variant="contained" size="large" startIcon={<IconSearch size={18} />} loading={submitting}>
          Xem kết quả
        </Button>
      </Stack>
    </FormProvider>
  );
}
