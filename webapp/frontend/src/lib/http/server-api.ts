import "server-only";
import type { ApiEnvelope, Bank } from "@/types/api";

/**
 * Gọi backend từ phía máy chủ Next.js (Server Component, generateMetadata) — đi thẳng tới API_URL,
 * không qua rewrite. Chỉ dùng cho dữ liệu công khai.
 */
const API_URL = process.env.API_URL ?? "http://localhost:8080";

/** Ngân hàng theo mã; null nếu không tồn tại (404); undefined nếu không gọi được backend. */
export async function fetchBank(ticker: string): Promise<Bank | null | undefined> {
  try {
    const response = await fetch(`${API_URL}/api/v1/banks/${encodeURIComponent(ticker)}`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(5000),
    });
    if (response.status === 404) return null;
    if (!response.ok) return undefined;
    const envelope = (await response.json()) as ApiEnvelope<Bank>;
    return envelope.data ?? undefined;
  } catch {
    return undefined;
  }
}
