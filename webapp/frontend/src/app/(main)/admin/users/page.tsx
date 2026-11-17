import type { Metadata } from "next";
import { AdminUsersView } from "@/features/admin/AdminUsersView";

export const metadata: Metadata = { title: "Quản lý người dùng" };

export default function AdminUsersPage() {
  return <AdminUsersView />;
}
