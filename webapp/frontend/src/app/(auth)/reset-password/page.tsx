import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetPasswordForm } from "@/features/auth/ResetPasswordForm";

export const metadata: Metadata = {
  title: "Đặt mật khẩu mới",
  // URL chứa token đặt lại mật khẩu: không để lọt ra ngoài qua header Referer.
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function ResetPasswordPage() {
  // ResetPasswordForm đọc ?token= bằng useSearchParams nên phải nằm trong Suspense.
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
