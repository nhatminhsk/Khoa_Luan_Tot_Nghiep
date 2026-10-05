import { NextResponse, type NextRequest } from "next/server";

/**
 * Kiểm tra sớm (optimistic): trang cần đăng nhập mà chưa có cookie phiên thì chuyển sang /login.
 * Đây chỉ là để trải nghiệm mượt; quyền thật (token hợp lệ, vai trò ADMIN) luôn do backend kiểm tra.
 */
const SESSION_COOKIE = "ba_session";

export function proxy(request: NextRequest) {
  if (request.cookies.get(SESSION_COOKIE)?.value) {
    return NextResponse.next();
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/watchlist/:path*", "/admin/:path*"],
};
