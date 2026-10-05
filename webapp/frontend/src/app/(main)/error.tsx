"use client";

import { Alert, AlertTitle, Button, Stack } from "@mui/material";
import { IconRefresh } from "@tabler/icons-react";
import { useEffect } from "react";

/** Lỗi không lường trước khi render một trang chính; menu và thanh trên vẫn dùng được. */
export default function MainError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Stack spacing={2} sx={{ maxWidth: 640 }}>
      <Alert severity="error">
        <AlertTitle>Trang gặp lỗi khi hiển thị</AlertTitle>
        Bạn có thể thử lại. Nếu lỗi lặp lại, hãy kiểm tra backend đã chạy chưa.
      </Alert>
      <Button variant="contained" startIcon={<IconRefresh size={18} />} onClick={() => retry()} sx={{ alignSelf: "flex-start" }}>
        Thử lại
      </Button>
    </Stack>
  );
}
