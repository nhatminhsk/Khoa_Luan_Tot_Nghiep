"use client";

import { Alert, Snackbar, type AlertColor } from "@mui/material";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { takeFlash } from "@/features/auth/reload-after-auth";

interface Toast {
  id: number;
  message: string;
  severity: AlertColor;
}

type Notify = (message: string, severity?: AlertColor) => void;

const NotifierContext = createContext<Notify | null>(null);

/** Thông báo ngắn (toast) sau một thao tác: lưu, xóa, lỗi mạng... Mỗi lúc hiện một toast. */
export function NotifierProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<Toast | null>(null);

  const notify = useCallback<Notify>((message, severity = "success") => {
    setToast({ id: Date.now(), message, severity });
  }, []);

  // Lời nhắn để lại trước khi tải lại cả trang (sau đăng nhập/đăng xuất, xem reload-after-auth.ts). Đọc trong effect vì
  // sessionStorage chỉ có ở trình duyệt; hẹn sang lượt sau để không đặt state ngay trong thân effect, và chỉ xóa lời nhắn
  // khi đã hiện (Strict Mode chạy effect hai lần, lần đầu bị hủy).
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const message = takeFlash();
      if (message) notify(message);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [notify]);

  const close = () => setToast(null);

  return (
    <NotifierContext.Provider value={useMemo(() => notify, [notify])}>
      {children}
      <Snackbar
        key={toast?.id}
        open={toast !== null}
        onClose={(_, reason) => reason !== "clickaway" && close()}
        autoHideDuration={toast?.severity === "error" ? 8000 : 4000}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {toast ? (
          <Alert onClose={close} severity={toast.severity} variant="filled" sx={{ minWidth: 280 }}>
            {toast.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </NotifierContext.Provider>
  );
}

export function useNotify(): Notify {
  const notify = useContext(NotifierContext);
  if (!notify) throw new Error("useNotify phải nằm trong NotifierProvider");
  return notify;
}
