import {
  IconArrowsLeftRight,
  IconBell,
  IconBook2,
  IconBuildingBank,
  IconDatabaseCog,
  IconHomeDollar,
  IconLayoutDashboard,
  IconPigMoney,
  IconUsers,
  type Icon,
} from "@tabler/icons-react";
import type { Permission } from "@/types/api";

/**
 * Cấu hình menu điều hướng. Sidebar dựng hoàn toàn từ danh sách này:
 * thêm một trang mới = tạo app/(main)/<đường-dẫn>/page.tsx + thêm một mục ở đây.
 */
export interface NavItem {
  href: string;
  label: string;
  icon: Icon;
  /** "exact": chỉ sáng khi đúng đường dẫn (dùng cho "/"); mặc định sáng cả trang con. */
  match?: "exact" | "prefix";
  requiresAuth?: boolean;
  /** Chỉ hiện khi tài khoản có quyền này (menu quản trị). */
  permission?: Permission;
}

export interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "overview",
    title: "Tổng quan",
    items: [{ href: "/", label: "Tổng quan thị trường", icon: IconLayoutDashboard, match: "exact" }],
  },
  {
    id: "tools",
    title: "Chọn ngân hàng",
    items: [
      { href: "/savings", label: "Gửi tiết kiệm", icon: IconPigMoney },
      { href: "/loans", label: "Vay", icon: IconHomeDollar },
    ],
  },
  {
    id: "lookup",
    title: "Tra cứu",
    items: [
      { href: "/banks", label: "Hồ sơ ngân hàng", icon: IconBuildingBank },
      { href: "/compare", label: "So sánh ngân hàng", icon: IconArrowsLeftRight },
    ],
  },
  {
    id: "personal",
    title: "Cá nhân",
    items: [{ href: "/watchlist", label: "Theo dõi và thông báo", icon: IconBell, requiresAuth: true }],
  },
  {
    id: "system",
    title: "Hệ thống",
    items: [
      { href: "/methodology", label: "Phương pháp và dữ liệu", icon: IconBook2 },
      { href: "/admin", label: "Quản trị dữ liệu", icon: IconDatabaseCog, match: "exact", permission: "DATA_MANAGE" },
      { href: "/admin/users", label: "Quản lý người dùng", icon: IconUsers, permission: "USER_MANAGE" },
    ],
  },
];

/** Đường dẫn cần đăng nhập — proxy.ts dùng để chuyển hướng sớm, backend vẫn kiểm tra quyền thật. */
export const PROTECTED_PATHS = ["/watchlist", "/admin"];

export function isActive(item: NavItem, pathname: string): boolean {
  if (item.match === "exact") return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
