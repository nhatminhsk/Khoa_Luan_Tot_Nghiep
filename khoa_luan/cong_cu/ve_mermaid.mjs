// Xuất sơ đồ Mermaid (.mmd) ra PNG bằng Microsoft Edge headless qua Chrome DevTools Protocol.
// Chạy: node khoa_luan/cong_cu/ve_mermaid.mjs <vao.mmd> <ra.png> [độ rộng tối đa px, mặc định 1400]
// Cần Edge và mạng (tải mermaid@11.4.1 từ cdn.jsdelivr.net).
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [, , vao, ra, rongArg] = process.argv;
if (!vao || !ra) {
  console.error("Cách dùng: node ve_mermaid.mjs <vao.mmd> <ra.png> [rộng]");
  process.exit(2);
}
const rong = Number(rongArg || 1400);
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const PORT = 9300 + Math.floor(Math.random() * 500);
const tam = mkdtempSync(join(tmpdir(), "mmd-"));
const src = readFileSync(vao, "utf8");
const html = `<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff} #c{display:inline-block;padding:12px}</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script></head>
<body><div id="c"><pre class="mermaid">${src.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</pre></div>
<script>
mermaid.initialize({startOnLoad:false, theme:"neutral", securityLevel:"loose",
  themeVariables:{fontFamily:"Times New Roman", fontSize:"16px"},
  flowchart:{htmlLabels:true, useMaxWidth:false}, er:{useMaxWidth:false}, sequence:{useMaxWidth:false}});
mermaid.run({querySelector:".mermaid"}).then(()=>{window.__xong=true}).catch(e=>{window.__loi=String(e)});
</script></body></html>`;
const trang = join(tam, "p.html");
writeFileSync(trang, html, "utf8");

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
  const page = targets.find((t) => t.type === "page");
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0;
  const cho = new Map();
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && cho.has(m.id)) { cho.get(m.id)(m); cho.delete(m.id); }
  });
  const goi = (method, params = {}) => new Promise((r) => { const k = ++id; cho.set(k, r); ws.send(JSON.stringify({ id: k, method, params })); });
  const tinh = async (expr) => (await goi("Runtime.evaluate", { expression: expr, returnByValue: true })).result?.result?.value;

  await goi("Emulation.setDeviceMetricsOverride", { width: rong, height: 1000, deviceScaleFactor: 2, mobile: false });
  await goi("Page.navigate", { url: pathToFileURL(resolve(trang)).href });
  for (let i = 0; i < 100; i++) {
    if (await tinh("window.__xong===true")) break;
    const loi = await tinh("window.__loi||null");
    if (loi) throw new Error("Mermaid lỗi: " + loi);
    await ngu(200);
  }
  const box = await tinh(`(()=>{const r=document.querySelector('#c').getBoundingClientRect();return {w:Math.ceil(r.width),h:Math.ceil(r.height)}})()`);
  await goi("Emulation.setDeviceMetricsOverride", { width: Math.max(box.w, 50), height: Math.max(box.h, 50), deviceScaleFactor: 2, mobile: false });
  await ngu(300);
  const shot = await goi("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: box.w, height: box.h, scale: 1 } });
  writeFileSync(ra, Buffer.from(shot.result.data, "base64"));
  console.log(`Đã ghi ${ra} (${box.w}×${box.h} px CSS)`);
} finally {
  try { ws?.close(); } catch {}
  edge.kill();
  await ngu(300);
  try { rmSync(tam, { recursive: true, force: true }); } catch {}
}
