"use client";

import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import { QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { createQueryClient } from "@/lib/query/query-client";
import { theme } from "@/theme/theme";
import { NotifierProvider } from "./NotifierProvider";

/** Các provider phía trình duyệt: theme (sáng/tối), cache dữ liệu, thông báo toast. */
export function AppProviders({ children }: { children: ReactNode }) {
  // Mỗi phiên trình duyệt một QueryClient; tạo trong useState để không bị tạo lại khi render.
  const [queryClient] = useState(createQueryClient);

  return (
    <ThemeProvider theme={theme} defaultMode="system" disableTransitionOnChange>
      <CssBaseline enableColorScheme />
      <QueryClientProvider client={queryClient}>
        <NotifierProvider>{children}</NotifierProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
