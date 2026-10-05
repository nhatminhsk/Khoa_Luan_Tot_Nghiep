import type { Metadata } from "next";
import { BankListView } from "@/features/banks/BankListView";

export const metadata: Metadata = { title: "Hồ sơ ngân hàng" };

export default function BanksPage() {
  return <BankListView />;
}
