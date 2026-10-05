import type { ApiEnvelope } from "@/types/api";
import { ApiError } from "./api-error";

/**
 * Client gọi backend. Mọi request đi qua đường dẫn tương đối /api/v1 trên cùng origin;
 * next.config.ts chuyển tiếp sang Spring Boot. Cookie phiên được trình duyệt tự gửi kèm.
 *
 * Mỗi hàm trả thẳng `data` của ApiEnvelope, hoặc ném ApiError — component không phải tự bóc vỏ.
 */
export const API_BASE = "/api/v1";

type Query = Record<string, string | number | boolean | string[] | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.append(key, String(value));
  }
  const qs = params.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function request<T>(method: string, path: string, options: { query?: Query; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Không kết nối được máy chủ. Kiểm tra backend đã chạy chưa.");
  }

  let envelope: ApiEnvelope<T> | null = null;
  try {
    envelope = (await response.json()) as ApiEnvelope<T>;
  } catch {
    // Phản hồi không phải JSON (ví dụ backend chưa chạy, proxy trả trang lỗi HTML).
  }

  if (!response.ok || !envelope?.success) {
    throw new ApiError(
      response.status,
      envelope?.errorCode ?? "UNKNOWN_ERROR",
      envelope?.message ?? `Máy chủ trả lỗi ${response.status}`,
      envelope?.fieldErrors ?? {},
    );
  }
  // Backend bỏ trường "data" khi giá trị là null (JsonInclude.NON_NULL) — đổi về null, không để undefined
  // (TanStack Query không nhận undefined làm dữ liệu của query).
  return (envelope.data === undefined ? null : envelope.data) as T;
}

export const apiClient = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, { query }),
  post: <T>(path: string, body?: unknown, query?: Query) => request<T>("POST", path, { body, query }),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
