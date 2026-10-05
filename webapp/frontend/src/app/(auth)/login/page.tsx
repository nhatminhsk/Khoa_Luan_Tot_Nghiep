import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/features/auth/LoginForm";

export const metadata: Metadata = { title: "Đăng nhập" };

export default function LoginPage() {
  // LoginForm đọc ?next= bằng useSearchParams nên phải nằm trong Suspense.
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
