// Kiểm thử giao diện trên nhiều kích thước màn hình và hai trình duyệt (Edge, Chrome) bằng giao thức DevTools.
// Mỗi (trình duyệt × kích thước × trang): tải trang, chờ hết khung chờ, rồi ghi: có tràn ngang không, số lỗi console,
// số yêu cầu mạng lỗi (>= 400), tiêu đề trang có hiện không. Chụp ảnh ở thư mục ket_qua/anh/.
// Chạy (web ở GOC): node webapp/kiem_thu/kiem_thu_giao_dien.mjs [http://localhost:3000] [nhãn tệp kết quả]
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const GOC = process.argv[2] || "http://localhost:3000";
const NHAN = process.argv[3] || "giao_dien";
const DIR = dirname(fileURLToPath(import.meta.url));
const RA = join(DIR, "ket_qua");
const ANH = join(RA, "anh");
mkdirSync(ANH, { recursive: true });
const TRINH_DUYET = {
  Edge: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  Chrome: "C:/Program Files/Google/Chrome/Application/chrome.exe",
};
const CO = [
  { ten: "dien_thoai", w: 375, h: 812, mobile: true },
  { ten: "may_tinh_bang", w: 768, h: 1024, mobile: true },
  { ten: "laptop", w: 1366, h: 768, mobile: false },
  { ten: "man_hinh_lon", w: 1920, h: 1080, mobile: false },
];
const TRANG = [
  { ten: "tong_quan", url: "/" },
  { ten: "gui_tiet_kiem", url: "/savings?amount=500000000&term=12&channel=ONLINE" },
  { ten: "vay", url: "/loans?purpose=HOME_PURCHASE&amount=1000000000&term=240&repayment=DECLINING_BALANCE" },
  { ten: "danh_sach_nh", url: "/banks" },
  { ten: "ho_so_nh", url: "/banks/VCB" },
  { ten: "so_sanh", url: "/compare?tickers=VCB,BID,CTG,TCB&indicator=npl" },
  { ten: "phuong_phap", url: "/methodology" },
  { ten: "dang_nhap", url: "/login" },
];
const ngu = (ms) => new Promise((r) => setTimeout(r, ms));
const ket = [];

async function chay(ten, exe) {
  const PORT = 9700 + Math.floor(Math.random() * 200);
  const tam = mkdtempSync(join(tmpdir(), "kt-"));
  const p = spawn(exe, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${join(tam, "u")}`, "--no-first-run", "--no-default-browser-check", "--ignore-certificate-errors", "about:blank"], { stdio: "ignore" });
  let ws;
  try {
    let targets = [];
    for (let i = 0; i < 60; i++) {
      try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); if (targets.length) break; } catch {}
      await ngu(250);
    }
    const ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
    ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
    await new Promise((r) => ws.addEventListener("open", r, { once: true }));
    let id = 0;
    const cho = new Map();
    let loiConsole = [], loiMang = [], hong = [];
    const urls = new Map();
    ws.addEventListener("message", (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && cho.has(m.id)) { cho.get(m.id)(m); cho.delete(m.id); return; }
      if (m.method === "Runtime.exceptionThrown") loiConsole.push(m.params.exceptionDetails?.text || "exception");
      if (m.method === "Log.entryAdded" && m.params.entry.level === "error") loiConsole.push(m.params.entry.text);
      if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error")
        loiConsole.push((m.params.args || []).map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 160));
      if (m.method === "Network.responseReceived" && m.params.response.status >= 400)
        loiMang.push(`${m.params.response.status} ${m.params.response.url}`);
      if (m.method === "Network.requestWillBeSent") urls.set(m.params.requestId, m.params.request.url);
      if (m.method === "Network.loadingFailed" && !m.params.canceled)
        hong.push(`${m.params.errorText} ${urls.get(m.params.requestId) || ""}`.slice(0, 160));
    });
    const goi = (method, params = {}) => new Promise((r) => { const k = ++id; cho.set(k, r); ws.send(JSON.stringify({ id: k, method, params })); });
    const tinh = async (e) => (await goi("Runtime.evaluate", { expression: e, returnByValue: true })).result?.result?.value;
    await goi("Runtime.enable"); await goi("Log.enable"); await goi("Network.enable");
    for (const c of CO) {
      await goi("Emulation.setDeviceMetricsOverride", { width: c.w, height: c.h, deviceScaleFactor: 1, mobile: c.mobile });
      await goi("Emulation.setTouchEmulationEnabled", { enabled: c.mobile });
      for (const t of TRANG) {
        loiConsole = []; loiMang = []; hong = [];
        const t0 = Date.now();
        await goi("Page.navigate", { url: GOC + t.url });
        for (let i = 0; i < 80; i++) {
          await ngu(400);
          const xong = await tinh(`document.readyState==='complete' && !document.querySelector('.MuiSkeleton-root, .MuiCircularProgress-root, .MuiLinearProgress-root')`);
          if (xong && i > 4) break;
        }
        const taiXong = (Date.now() - t0) / 1000;
        await ngu(800);
        const r = await tinh(`(() => {
          const de = document.documentElement;
          const tran = Math.max(de.scrollWidth, document.body.scrollWidth) - de.clientWidth;
          const h = document.querySelector('h1, h2, h3, h4, h5, h6, [role=heading]');
          const loiTrang = !!document.querySelector('[data-error-boundary], .MuiAlert-standardError, .MuiAlert-filledError');
          return { tran, tieuDe: h ? h.textContent.trim().slice(0, 60) : '', loiTrang };
        })()`);
        const anh = `${NHAN}_${ten}_${c.ten}_${t.ten}.png`;
        if (t.ten === "tong_quan" || t.ten === "gui_tiet_kiem") {
          const s = await goi("Page.captureScreenshot", { format: "png" });
          writeFileSync(join(ANH, anh), Buffer.from(s.result.data, "base64"));
        }
        ket.push({ trinh_duyet: `${ten} ${ver.Browser.split("/")[1]}`, kich_thuoc: `${c.w}x${c.h}`, trang: t.url.split("?")[0],
          tran_ngang_px: r.tran, co_tieu_de: r.tieuDe ? 1 : 0, tieu_de: r.tieuDe, khoi_loi: r.loiTrang ? 1 : 0,
          loi_console: loiConsole.filter((x) => !/favicon|DevTools|Download the React/i.test(x)).length,
          loi_mang: loiMang.filter((x) => !/favicon/.test(x)).length, chi_tiet_loi: [...loiConsole, ...loiMang].slice(0, 2).join(" | "), tai_nguyen_hong: hong.length,
          url_hong: hong.slice(0, 3).join(" | "),
          tai_xong_s: taiXong });
        const k = ket[ket.length - 1];
        console.log(`${ten} ${c.w}x${c.h} ${t.ten}: tràn ${k.tran_ngang_px}px, console ${k.loi_console}, mạng ${k.loi_mang}, ${k.tai_xong_s}s`);
      }
    }
  } finally {
    try { ws?.close(); } catch {}
    p.kill();
    await ngu(400);
    try { rmSync(tam, { recursive: true, force: true }); } catch {}
  }
}

const CHON = (process.env.TRINH_DUYET || "").split(",").filter(Boolean);
for (const [ten, exe] of Object.entries(TRINH_DUYET)) if (!CHON.length || CHON.includes(ten)) await chay(ten, exe);
const cot = Object.keys(ket[0]);
const csv = [cot.join(","), ...ket.map((r) => cot.map((c) => `"${String(r[c]).replaceAll('"', "'")}"`).join(","))].join("\n");
writeFileSync(join(RA, `${NHAN}.csv`), "\ufeff" + csv);
console.log("ghi", join(RA, `${NHAN}.csv`), ket.length, "dòng");
