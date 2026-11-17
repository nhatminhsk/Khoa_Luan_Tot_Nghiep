import { apiClient } from "@/lib/http/api-client";
import type {
  AdminAuditEntry,
  AdminUser,
  AdminUserPage,
  EmailDispatchResult,
  EmailQueueSummary,
  ImportRun,
  ImportSummary,
  PageResponse,
  Role,
  UpdateUserInput,
  UserStatus,
} from "@/types/api";

export interface AdminUserQuery {
  q?: string;
  role?: Role;
  status?: UserStatus;
  page: number;
  size: number;
}

/** Chỉ vai trò ADMIN gọi được (backend kiểm tra quyền). */
export const adminRepository = {
  importRuns: () => apiClient.get<ImportRun[]>("/admin/imports"),
  runImport: (force: boolean) => apiClient.post<ImportSummary>("/admin/imports", undefined, { force }),
  emailQueue: () => apiClient.get<EmailQueueSummary>("/admin/email-queue"),
  /** Gửi ngay các email đã tới lượt, không chờ lịch quét mỗi phút. */
  dispatchEmails: () => apiClient.post<EmailDispatchResult>("/admin/email-queue/dispatch"),
  /** Quản lý người dùng (quyền USER_MANAGE). */
  users: ({ q, role, status, page, size }: AdminUserQuery) =>
    apiClient.get<AdminUserPage>("/admin/users", { q: q || undefined, role, status, page, size }),
  updateUser: (id: number, input: UpdateUserInput) => apiClient.patch<AdminUser>(`/admin/users/${id}`, input),
  revokeUserSessions: (id: number) => apiClient.post<void>(`/admin/users/${id}/revoke-sessions`),
  /** Nhật ký thao tác quản trị, mới nhất trước (quyền USER_MANAGE). */
  audit: (page: number, size: number) => apiClient.get<PageResponse<AdminAuditEntry>>("/admin/audit", { page, size }),
};
