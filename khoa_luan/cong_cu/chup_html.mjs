// Chụp từng tệp HTML trong khoa_luan/anh_code/html thành ảnh PNG (khung #o), độ phân giải gấp 2.
// Chạy: node khoa_luan/cong_cu/chup_html.mjs [tên1 tên2 ...]
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const VAO = resolve("khoa_luan/anh_code/html");
const RA = resolve("figures/khoa_luan/code");
const chon = process.argv.slice(2);
const tep = readdirSync(VAO).filter((f) => f.endsWith(".html") && (!chon.length || chon.includes(f.replace(".html", ""))));
mkdirSync(RA, { recursive: true });
const PORT = 9700 + Math.floor(Math.random() * 100);
const tam = mkdtempSync(join(tmpdir(), "chup-"));
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
  await goi("Emulation.setDeviceMetricsOverride", { width: 840, height: 1200, deviceScaleFactor: 2, mobile: false });
  for (const f of tep) {
    await goi("Page.navigate", { url: pathToFileURL(join(VAO, f)).href });
    await ngu(400);
    const r = await tinh(`(()=>{const b=document.getElementById('o').getBoundingClientRect();return [b.x,b.y,b.width,b.height]})()`);
    await goi("Emulation.setDeviceMetricsOverride", { width: 840, height: Math.ceil(r[3]) + 20, deviceScaleFactor: 2, mobile: false });
    await ngu(150);
    const shot = await goi("Page.captureScreenshot", { format: "png", clip: { x: r[0], y: r[1], width: r[2], height: r[3], scale: 1 } });
    writeFileSync(join(RA, f.replace(".html", ".png")), Buffer.from(shot.result.data, "base64"));
    console.log("ghi", f.replace(".html", ".png"), Math.round(r[3]));
  }
} finally {
  try { ws?.close(); } catch {}
  edge.kill();
  await ngu(300);
  try { rmSync(tam, { recursive: true, force: true }); } catch {}
}
