// Chụp ảnh các trang chính của web app (chế độ sáng) cho chương 4.
// Cần web chạy ở http://localhost:3000 (launch.json: api + web). Chạy: node khoa_luan/cong_cu/chup_giao_dien.mjs
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const GOC = "http://localhost:3000";
const RA = "figures/khoa_luan/giao_dien";
const TRANG = [
  { ten: "tong_quan", url: "/", cao: 1500 },
  { ten: "gui_tiet_kiem", url: "/savings?amount=500000000&term=12&channel=ONLINE", cao: 1700 },
  { ten: "vay", url: "/loans?purpose=HOME_PURCHASE&amount=1000000000&term=240&repayment=DECLINING_BALANCE", cao: 1500 },
  { ten: "danh_sach_nh", url: "/banks", cao: 1100 },
  { ten: "ho_so_nh", url: "/banks/VCB", cao: 1500 },
  { ten: "so_sanh", url: "/compare?tickers=VCB,BID,CTG,TCB&indicator=npl", cao: 1300 },
  { ten: "phuong_phap", url: "/methodology", cao: 1200 },
  { ten: "dang_nhap", url: "/login", cao: 800 },
];
const PORT = 9800 + Math.floor(Math.random() * 100);
const tam = mkdtempSync(join(tmpdir(), "chup-"));
mkdirSync(RA, { recursive: true });
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${join(tam, "u")}`, "--no-first-run", "about:blank"], { stdio: "ignore" });
const ngu = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
try {
  let targets;
  for (let i = 0; i < 50; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); if (targets.length) break; } catch {}
    await ngu(200);
  }
  ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0;
  const cho = new Map();
  ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && cho.has(m.id)) { cho.get(m.id)(m); cho.delete(m.id); } });
  const goi = (method, params = {}) => new Promise((r) => { const k = ++id; cho.set(k, r); ws.send(JSON.stringify({ id: k, method, params })); });
  const tinh = async (e) => (await goi("Runtime.evaluate", { expression: e, returnByValue: true })).result?.result?.value;
  await goi("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
  for (const t of TRANG) {
    await goi("Emulation.setDeviceMetricsOverride", { width: 1440, height: t.cao, deviceScaleFactor: 1.5, mobile: false });
    await goi("Page.navigate", { url: GOC + t.url });
    for (let i = 0; i < 60; i++) {
      await ngu(500);
      const xong = await tinh(`document.readyState==='complete' && !document.querySelector('.MuiSkeleton-root, .MuiCircularProgress-root, .MuiLinearProgress-root')`);
      if (xong && i > 6) break;
    }
    await ngu(1500);
    await tinh(`document.querySelectorAll('nextjs-portal').forEach((e) => e.remove())`);   // nút dev của Next.js
    await ngu(200);
    const shot = await goi("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: 1440, height: t.cao, scale: 1 } });
    writeFileSync(join(RA, `${t.ten}.png`), Buffer.from(shot.result.data, "base64"));
    console.log("ghi", t.ten);
  }
} finally {
  try { ws?.close(); } catch {}
  edge.kill();
  await ngu(300);
  try { rmSync(tam, { recursive: true, force: true }); } catch {}
}
