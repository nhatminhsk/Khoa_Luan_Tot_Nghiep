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
      // Cookie hết hạn: backend trả 401 và xóa cookie — coi như chưa đăng nhập.
      if (error instanceof ApiError && error.isUnauthorized) return null;
      throw error;
    }
  },
  login: (input: LoginInput) => apiClient.post<User>("/auth/login", input),
  register: (input: RegisterInput) => apiClient.post<User>("/auth/register", input),
  logout: () => apiClient.post<void>("/auth/logout"),
  /** Bấm link xác minh trong email; không cần đăng nhập (token tự chứng minh người dùng). */
  verifyEmail: (token: string) => apiClient.post<User>("/auth/verify-email", { token }),
};
