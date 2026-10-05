import type { Metadata } from "next";
import { Suspense } from "react";
import { RegisterForm } from "@/features/auth/RegisterForm";

export const metadata: Metadata = { title: "Tạo tài khoản" };

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
