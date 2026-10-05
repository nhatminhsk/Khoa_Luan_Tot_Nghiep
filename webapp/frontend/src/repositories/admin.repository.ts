import { apiClient } from "@/lib/http/api-client";
import type { EmailDispatchResult, EmailQueueSummary, ImportRun, ImportSummary } from "@/types/api";

/** Chỉ vai trò ADMIN gọi được (backend kiểm tra quyền). */
export const adminRepository = {
  importRuns: () => apiClient.get<ImportRun[]>("/admin/imports"),
  runImport: (force: boolean) => apiClient.post<ImportSummary>("/admin/imports", undefined, { force }),
  emailQueue: () => apiClient.get<EmailQueueSummary>("/admin/email-queue"),
  /** Gửi ngay các email đã tới lượt, không chờ lịch quét mỗi phút. */
  dispatchEmails: () => apiClient.post<EmailDispatchResult>("/admin/email-queue/dispatch"),
};
