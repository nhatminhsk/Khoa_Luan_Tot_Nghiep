/** Lỗi từ backend (hoặc lỗi mạng), đã chuẩn hóa để giao diện hiển thị thống nhất. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Có lỗi xảy ra, vui lòng thử lại sau";
}
