import type { NextConfig } from "next";

/** Địa chỉ backend Spring Boot, chỉ dùng ở phía máy chủ Next.js. */
const API_URL = process.env.API_URL ?? "http://localhost:8080";

const isDev = process.env.NODE_ENV === "development";

/**
 * Content-Security-Policy không dùng nonce (trang vẫn render tĩnh được). 'unsafe-inline' cần cho script khởi tạo
 * của Next.js và style do MUI/Emotion chèn; 'unsafe-eval' chỉ bật khi dev (React dựng lại stack lỗi).
 * Mọi tài nguyên (font, icon, API) đều cùng origin nên chặn được script, khung, form trỏ ra ngoài.
 */
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), browsing-topics=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Ảnh Docker build với NEXT_OUTPUT=standalone: chỉ chép file cần chạy (.next/standalone/server.js), không cần
  // node_modules đầy đủ. Chạy trên máy (npm run dev / next start) vẫn như cũ.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  // Trình duyệt gọi /api/... trên cùng origin với trang; Next.js chuyển tiếp sang backend.
  // Nhờ vậy cookie phiên (httpOnly, SameSite=Lax) hoạt động mà không cần mở CORS.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
  // HSTS đặt ở reverse proxy khi triển khai HTTPS, không đặt ở đây vì chạy thử trên http://localhost.
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  // Tree-shake bộ icon và MUI để giảm kích thước bundle.
  experimental: {
    optimizePackageImports: ["@tabler/icons-react", "@mui/material", "@mui/x-charts"],
  },
};

export default nextConfig;
