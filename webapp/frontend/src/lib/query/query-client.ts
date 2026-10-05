import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/http/api-error";

/**
 * Dữ liệu chỉ đổi mỗi ngày (lãi suất) hoặc mỗi quý (BCTC), nên để staleTime dài
 * và không tự tải lại khi người dùng quay lại tab.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
        // Lỗi 4xx là lỗi nghiệp vụ (không tìm thấy, chưa đăng nhập) — thử lại không giúp gì.
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status >= 400 && error.status < 500) && failureCount < 2,
      },
    },
  });
}
