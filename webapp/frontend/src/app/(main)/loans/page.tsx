import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/common/States";
import { LoansView } from "@/features/loans/LoansView";

export const metadata: Metadata = { title: "Chọn ngân hàng vay" };

export default function LoansPage() {
  return (
    <Suspense fallback={<LoadingBlock height={480} />}>
      <LoansView />
    </Suspense>
  );
}
