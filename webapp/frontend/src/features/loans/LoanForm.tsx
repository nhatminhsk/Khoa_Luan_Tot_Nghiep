"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Button, Chip, Grid, Stack } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import type { z } from "zod";
import { RHFMoneyField, RHFSelect, RHFToggle } from "@/components/form/RHFFields";
import type { LoanAdviceRequest, LoanPurpose, RepaymentMethod } from "@/types/api";
import { formatTerm, formatVndCompact } from "@/utils/format";
import { LOAN_PURPOSE_LABEL, REPAYMENT_HINT, REPAYMENT_LABEL } from "@/utils/labels";
import { LOAN_TERMS, loanSchema } from "./loan-params";

type LoanFormValues = z.infer<typeof loanSchema>;
const QUICK_AMOUNTS = [200_000_000, 500_000_000, 1_000_000_000, 3_000_000_000];

interface LoanFormProps {
  initial: LoanAdviceRequest;
  onSubmit: (values: LoanAdviceRequest) => void;
  submitting: boolean;
}

export function LoanForm({ initial, onSubmit, submitting }: LoanFormProps) {
  const methods = useForm<LoanFormValues>({ resolver: zodResolver(loanSchema), defaultValues: initial });
  const repayment = useWatch({ control: methods.control, name: "repayment" });

  return (
    <FormProvider {...methods}>
      {/* Cột hẹp bên trái (lg+): xếp dọc. Dưới lg form trải ngang (iPad): mục đích | số tiền, thời hạn | cách trả. */}
      <Box component="form" noValidate onSubmit={methods.handleSubmit((values) => onSubmit(values))}>
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, sm: 6, lg: 12 }}>
            <RHFSelect<LoanFormValues, LoanPurpose>
              name="purpose"
              label="Mục đích vay"
              options={(Object.keys(LOAN_PURPOSE_LABEL) as LoanPurpose[]).map((p) => ({ value: p, label: LOAN_PURPOSE_LABEL[p] }))}
              helperText="Dùng để gợi ý chương trình tín dụng ưu đãi phù hợp."
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 12 }}>
            <RHFMoneyField<LoanFormValues> name="amount" label="Số tiền vay" />
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
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 12 }}>
            <RHFSelect<LoanFormValues, number>
              name="termMonths"
              label="Thời hạn vay"
              options={LOAN_TERMS.map((t) => ({ value: t, label: formatTerm(t) }))}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 12 }}>
            <RHFToggle<LoanFormValues, RepaymentMethod>
              name="repayment"
              label="Cách trả nợ"
              options={(Object.keys(REPAYMENT_LABEL) as RepaymentMethod[]).map((r) => ({ value: r, label: REPAYMENT_LABEL[r] }))}
              helperText={REPAYMENT_HINT[repayment]}
            />
          </Grid>
          <Grid size={12}>
            <Button type="submit" variant="contained" size="large" fullWidth startIcon={<IconSearch size={18} />} loading={submitting}>
              Xem kết quả
            </Button>
          </Grid>
        </Grid>
      </Box>
    </FormProvider>
  );
}
