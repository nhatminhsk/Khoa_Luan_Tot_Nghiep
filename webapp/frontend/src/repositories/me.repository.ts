import { apiClient } from "@/lib/http/api-client";
import type {
  AppNotification,
  EmailVerificationStatus,
  NotificationSettings,
  NotificationSettingsUpdate,
  PageResponse,
  SavedNeed,
  SavedNeedRequest,
  User,
  WatchItem,
} from "@/types/api";

/** Dữ liệu riêng của người đang đăng nhập — /api/v1/me/**. */
export const meRepository = {
  needs: () => apiClient.get<SavedNeed[]>("/me/needs"),
  createNeed: (need: SavedNeedRequest) => apiClient.post<SavedNeed>("/me/needs", need),
  updateNeed: (id: number, need: SavedNeedRequest) => apiClient.put<SavedNeed>(`/me/needs/${id}`, need),
  deleteNeed: (id: number) => apiClient.delete<void>(`/me/needs/${id}`),

  watchlist: () => apiClient.get<WatchItem[]>("/me/watchlist"),
  watch: (ticker: string, rateThreshold?: number) =>
    apiClient.post<WatchItem>("/me/watchlist", { ticker, rateThreshold }),
  updateWatch: (ticker: string, rateThreshold: number) =>
    apiClient.patch<WatchItem>(`/me/watchlist/${encodeURIComponent(ticker)}`, { rateThreshold }),
  unwatch: (ticker: string) => apiClient.delete<void>(`/me/watchlist/${encodeURIComponent(ticker)}`),

  notifications: (page = 0, size = 20) =>
    apiClient.get<PageResponse<AppNotification>>("/me/notifications", { page, size }),
  unreadCount: () => apiClient.get<{ unread: number }>("/me/notifications/unread-count"),
  markRead: (id: number) => apiClient.post<void>(`/me/notifications/${id}/read`),
  markAllRead: () => apiClient.post<void>("/me/notifications/read-all"),

  notificationSettings: () => apiClient.get<NotificationSettings>("/me/notification-settings"),
  updateNotificationSettings: (settings: NotificationSettingsUpdate) =>
    apiClient.put<NotificationSettings>("/me/notification-settings", settings),

  /** Đổi email đăng nhập (cần mật khẩu hiện tại); email mới phải xác minh lại. */
  changeEmail: (input: { newEmail: string; currentPassword: string }) => apiClient.put<User>("/me/email", input),
  /** Đổi mật khẩu: phiên ở thiết bị khác bị thu hồi, trình duyệt này nhận cookie phiên mới. */
  changePassword: (input: { currentPassword: string; newPassword: string }) => apiClient.put<User>("/me/password", input),

  emailVerification: () => apiClient.get<EmailVerificationStatus>("/me/email-verification"),
  /** Gửi (lại) email xác minh (link + mã 6 số) tới email đăng ký. */
  sendEmailVerification: () => apiClient.post<EmailVerificationStatus>("/me/email-verification"),
  /** Nhập mã 6 số trong email — dùng khi đọc thư trên thiết bị khác, link không mở được. */
  confirmEmailCode: (code: string) => apiClient.post<EmailVerificationStatus>("/me/email-verification/confirm", { code }),
};
