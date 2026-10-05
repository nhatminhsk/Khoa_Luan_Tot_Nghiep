import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/common/States";
import { SavingsView } from "@/features/savings/SavingsView";

export const metadata: Metadata = { title: "Chọn ngân hàng gửi tiết kiệm" };

export default function SavingsPage() {
  // SavingsView đọc tiêu chí từ URL (useSearchParams) nên cần Suspense.
  return (
    <Suspense fallback={<LoadingBlock height={480} />}>
      <SavingsView />
    </Suspense>
  );
}
