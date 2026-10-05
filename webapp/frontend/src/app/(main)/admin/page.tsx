import type { Metadata } from "next";
import { AdminView } from "@/features/admin/AdminView";

export const metadata: Metadata = { title: "Quản trị dữ liệu" };

export default function AdminPage() {
  return <AdminView />;
}
