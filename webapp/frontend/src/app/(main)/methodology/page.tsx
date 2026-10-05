import type { Metadata } from "next";
import { MethodologyView } from "@/features/methodology/MethodologyView";

export const metadata: Metadata = { title: "Phương pháp và dữ liệu" };

export default function MethodologyPage() {
  return <MethodologyView />;
}
