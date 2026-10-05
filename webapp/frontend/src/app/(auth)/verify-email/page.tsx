import type { Metadata } from "next";
import { Suspense } from "react";
import { VerifyEmailView } from "@/features/auth/VerifyEmailView";

export const metadata: Metadata = {
  title: "Xác minh email",
  // URL chứa token xác minh: không để lọt ra ngoài qua header Referer.
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function VerifyEmailPage() {
  // VerifyEmailView đọc ?token= bằng useSearchParams nên phải nằm trong Suspense.
  return (
    <Suspense>
      <VerifyEmailView />
    </Suspense>
  );
}
