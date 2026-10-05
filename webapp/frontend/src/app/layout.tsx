import InitColorSchemeScript from "@mui/material/InitColorSchemeScript";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v16-appRouter";
import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import { AppProviders } from "@/components/providers/AppProviders";
import { siteConfig } from "@/config/site";
import "./globals.css";

// Be Vietnam Pro: thiết kế cho tiếng Việt, dấu rõ ở cỡ chữ nhỏ; tự host qua next/font (không gọi Google lúc chạy).
const sans = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: { default: `${siteConfig.name} · ${siteConfig.tagline}`, template: `%s · ${siteConfig.name}` },
  description: siteConfig.description,
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f1f4f9" },
    { media: "(prefers-color-scheme: dark)", color: "#080c15" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: InitColorSchemeScript gắn class sáng/tối lên <html> trước khi React chạy.
    <html lang="vi" className={sans.variable} suppressHydrationWarning>
      <body>
        <InitColorSchemeScript attribute="class" defaultMode="system" />
        <AppRouterCacheProvider options={{ enableCssLayer: true }}>
          <AppProviders>{children}</AppProviders>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
