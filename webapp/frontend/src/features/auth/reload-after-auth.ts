/**
 * Chuyển trang bằng tải lại cả trang sau khi phiên đổi (đăng nhập, đăng ký, đăng xuất).
 *
 * Vì sao không dùng router.replace/push: Next.js 16 lưu kết quả prefetch theo đường dẫn, kể cả lệnh chuyển hướng của
 * proxy.ts. Lúc chưa đăng nhập, link "Theo dõi" được prefetch thành "/watchlist → /login?next=/watchlist" và giữ khoảng
 * 5 phút; router.refresh() chỉ xóa dữ liệu trang, không xóa phần chuyển hướng này. Đăng nhập xong mà chuyển trang trong
 * SPA thì bấm "Theo dõi" (hay chính router.replace("/watchlist")) vẫn bị đưa về trang đăng nhập, bấm đăng nhập lại bao
 * nhiêu lần cũng đứng yên. Tải lại cả trang xóa sạch bộ nhớ đó.
 *
 * Toast (ví dụ "Xin chào…") mất khi tải lại, nên gửi qua sessionStorage; NotifierProvider hiện nó sau khi trang mới mở.
 */
export const FLASH_KEY = "ba_flash";

export function reloadTo(path: string, flash?: string, mode: "replace" | "assign" = "replace"): void {
  if (flash) {
    try {
      sessionStorage.setItem(FLASH_KEY, flash);
    } catch {
      // Trình duyệt chặn bộ nhớ (chế độ riêng tư): chỉ mất lời chào, vẫn chuyển trang.
    }
  }
  if (mode === "assign") window.location.assign(path);
  else window.location.replace(path);
}

/** Đọc rồi xóa lời nhắn để lại trước khi tải lại trang (gọi một lần lúc trang mở). */
export function takeFlash(): string | null {
  try {
    const message = sessionStorage.getItem(FLASH_KEY);
    if (message) sessionStorage.removeItem(FLASH_KEY);
    return message;
  } catch {
    return null;
  }
}
