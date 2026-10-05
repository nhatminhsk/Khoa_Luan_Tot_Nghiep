/** Chỉ chấp nhận đường dẫn nội bộ ("/..."), chặn chuyển hướng ra trang ngoài qua ?next=//evil.com. */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return "/";
  if (next.startsWith("/login") || next.startsWith("/register")) return "/";
  return next;
}
