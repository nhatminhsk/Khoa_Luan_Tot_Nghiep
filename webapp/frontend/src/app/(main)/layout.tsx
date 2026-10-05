import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";

/** Layout của mọi trang chính: menu trái + thanh trên; nội dung trang con hiện ở {children}. */
export default function MainGroupLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
