import type { Metadata } from "next";
import { OverviewView } from "@/features/overview/OverviewView";

export const metadata: Metadata = { title: "Tổng quan thị trường" };

export default function OverviewPage() {
  return <OverviewView />;
}
