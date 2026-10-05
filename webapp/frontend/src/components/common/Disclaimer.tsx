import { Alert } from "@mui/material";
import { IconInfoCircle } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { siteConfig } from "@/config/site";

export function Disclaimer({ children }: { children?: ReactNode }) {
  return (
    <Alert severity="info" variant="outlined" icon={<IconInfoCircle size={20} />} sx={{ mt: 3 }}>
      {children ?? siteConfig.disclaimer}
    </Alert>
  );
}
