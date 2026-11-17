import { apiClient } from "@/lib/http/api-client";
import { ApiError } from "@/lib/http/api-error";
import type { User } from "@/types/api";

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput extends LoginInput {
  displayName: string;
}

/** Token nằm trong cookie httpOnly do backend đặt; phía trình duyệt không bao giờ đọc hay lưu token. */
export const authRepository = {
  /** Người dùng hiện tại, hoặc null nếu chưa đăng nhập (endpoint /auth/session trả 200 cho khách, không sinh 401). */
  me: async (): Promise<User | null> => {
    try {
      return await apiClient.get<User | null>("/auth/session");
    } catch (error) {
      // Cookie hết hạn, phiên bị thu hồi (401) hoặc tài khoản bị khóa (403 ACCOUNT_LOCKED): backend đã xóa cookie —
      // coi như chưa đăng nhập.
      if (error instanceof ApiError && (error.isUnauthorized || error.code === "ACCOUNT_LOCKED")) return null;
      throw error;
    }
  },
  login: (input: LoginInput) => apiClient.post<User>("/auth/login", input),
  register: (input: RegisterInput) => apiClient.post<User>("/auth/register", input),
  logout: () => apiClient.post<void>("/auth/logout"),
  /** Đăng xuất mọi thiết bị: thu hồi mọi phiên của tài khoản (kể cả phiên hiện tại). */
  revokeAllSessions: () => apiClient.post<void>("/me/sessions/revoke-all"),
  /** Bấm link xác minh trong email; không cần đăng nhập (token tự chứng minh người dùng). */
  verifyEmail: (token: string) => apiClient.post<User>("/auth/verify-email", { token }),
  /** Quên mật khẩu: backend trả cùng một kết quả dù email có tài khoản hay không. */
  requestPasswordReset: (email: string) => apiClient.post<void>("/auth/password-reset", { email }),
  /** Đặt mật khẩu mới bằng token trong link email; không tự đăng nhập. */
  confirmPasswordReset: (token: string, newPassword: string) =>
    apiClient.post<void>("/auth/password-reset/confirm", { token, newPassword }),
};
