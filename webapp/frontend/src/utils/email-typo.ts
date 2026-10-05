/**
 * Gợi ý sửa email gõ nhầm tên miền phổ biến ("an@gamil.com" → "an@gmail.com"). Chỉ gợi ý, không chặn: vẫn có thể
 * có tên miền thật gần giống. Kiểm tra DNS ở máy chủ không thay được bước này, vì tên miền gõ nhầm của các nhà
 * cung cấp lớn thường đã bị người khác đăng ký sẵn (và nhận được thư).
 */

/** Nhà cung cấp email phổ biến ở Việt Nam. Gồm cả tên miền thật gần giống nhau để không gợi ý nhầm (mail.com, ymail.com). */
const KNOWN_DOMAINS = [
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "yahoo.com.vn",
  "ymail.com",
  "outlook.com",
  "outlook.com.vn",
  "hotmail.com",
  "live.com",
  "msn.com",
  "icloud.com",
  "me.com",
  "mail.com",
  "email.com",
  "gmx.com",
  "aol.com",
  "yandex.com",
  "proton.me",
  "protonmail.com",
  "zoho.com",
];

/** Đuôi ".com" gõ nhầm hay gặp; tên miền lạ nhưng đuôi sai thì chỉ sửa đuôi. */
const COM_TYPOS = new Set(["con", "cmo", "ocm", "comm", "cpm", "xom", "vom", "coom", "cim"]);

export function suggestEmail(email: string): string | null {
  const value = email.trim().toLowerCase();
  const at = value.lastIndexOf("@");
  if (at <= 0 || at === value.length - 1) return null;
  const local = value.slice(0, at);
  const domain = value.slice(at + 1);
  if (!domain.includes(".") || KNOWN_DOMAINS.includes(domain)) return null;

  let best: string | null = null;
  let bestDistance = Infinity;
  for (const known of KNOWN_DOMAINS) {
    const d = editDistance(domain, known);
    if (d < bestDistance) {
      best = known;
      bestDistance = d;
    }
  }
  // Tên miền ngắn chỉ cho lệch 1 ký tự, dài hơn cho lệch 2 (đảo chỗ hai ký tự tính là 1).
  if (best && bestDistance <= (best.length >= 9 ? 2 : 1)) return `${local}@${best}`;

  const dot = domain.lastIndexOf(".");
  const tld = domain.slice(dot + 1);
  if (COM_TYPOS.has(tld)) return `${local}@${domain.slice(0, dot)}.com`;
  return null;
}

/** Khoảng cách Damerau–Levenshtein (bản đơn giản: thêm, bớt, thay, đảo chỗ hai ký tự liền nhau). */
export function editDistance(a: string, b: string): number {
  const d: number[][] = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
      }
    }
  }
  return d[a.length][b.length];
}
