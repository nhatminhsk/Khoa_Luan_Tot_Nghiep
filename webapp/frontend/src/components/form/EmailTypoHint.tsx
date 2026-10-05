"use client";

import { Alert, Button } from "@mui/material";
import { suggestEmail } from "@/utils/email-typo";

/** "Có phải bạn muốn nhập an@gmail.com?" — hiện dưới ô email khi tên miền giống một nhà cung cấp phổ biến bị gõ nhầm. */
export function EmailTypoHint({ email, onApply }: { email: string | undefined; onApply: (suggestion: string) => void }) {
  const suggestion = email ? suggestEmail(email) : null;
  if (!suggestion) return null;
  return (
    <Alert
      severity="warning"
      role="status"
      sx={{ py: 0.25, "& .MuiAlert-action": { alignItems: "center", pt: 0 } }}
      action={
        <Button color="inherit" size="small" onClick={() => onApply(suggestion)} sx={{ minHeight: 36 }}>
          Sửa
        </Button>
      }
    >
      Có phải bạn muốn nhập <strong>{suggestion}</strong>?
    </Alert>
  );
}
