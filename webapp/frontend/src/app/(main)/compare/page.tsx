import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/common/States";
import { CompareView } from "@/features/compare/CompareView";

export const metadata: Metadata = { title: "So sánh ngân hàng" };

export default function ComparePage() {
  return (
    <Suspense fallback={<LoadingBlock height={480} />}>
      <CompareView />
    </Suspense>
  );
}
