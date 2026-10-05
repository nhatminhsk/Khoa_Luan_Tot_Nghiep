"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Button, Chip, Stack } from "@mui/material";
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
      <Stack component="form" spacing={2.5} noValidate onSubmit={methods.handleSubmit((values) => onSubmit(values))}>
        <RHFSelect<LoanFormValues, LoanPurpose>
          name="purpose"
          label="Mục đích vay"
          options={(Object.keys(LOAN_PURPOSE_LABEL) as LoanPurpose[]).map((p) => ({ value: p, label: LOAN_PURPOSE_LABEL[p] }))}
          helperText="Dùng để gợi ý chương trình tín dụng ưu đãi phù hợp."
        />
        <Box>
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
        </Box>
        <RHFSelect<LoanFormValues, number>
          name="termMonths"
          label="Thời hạn vay"
          options={LOAN_TERMS.map((t) => ({ value: t, label: formatTerm(t) }))}
        />
        <RHFToggle<LoanFormValues, RepaymentMethod>
          name="repayment"
          label="Cách trả nợ"
          options={(Object.keys(REPAYMENT_LABEL) as RepaymentMethod[]).map((r) => ({ value: r, label: REPAYMENT_LABEL[r] }))}
          helperText={REPAYMENT_HINT[repayment]}
        />
        <Button type="submit" variant="contained" size="large" startIcon={<IconSearch size={18} />} loading={submitting}>
          Xem kết quả
        </Button>
      </Stack>
    </FormProvider>
  );
}
