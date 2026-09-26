#!/usr/bin/env node
// Build apps/web, serve the production bundle with `vite preview`, answer every data URL from the
// synthetic fixture (a tiny in-process fixture API, including a real /ui/stream SSE push), then
// screenshot every page at several widths.
//
// Fails (exit 1) on: horizontal page overflow; elements cut off at the viewport edge; the trade
// table's P/L / Status columns outside the visible table at >= 1280px; "NaN"/"undefined" on screen;
// page errors; and (unless --no-features) missing Desk/Founder panels.
//
//   node scripts/ui_snapshots/run.mjs [--out DIR] [--widths 390,1280,1440,1920] [--root WEB_DIR] [--no-features]
//
// Offline: no proxy to :8000, and the browser aborts every non-loopback request.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { build, preview } from "vite";
import { board, dayHistory, exam, founderBook, founderStatus, snapshot, trace } from "./fixture.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
};
const WEB = resolve(arg("root", resolve(HERE, "../..")));
const OUT = resolve(arg("out", resolve(HERE, "out")));
const WIDTHS = arg("widths", "390,1280,1440,1920").split(",").map(Number);
const FEATURES = !args.includes("--no-features");
const READY = ".grid, table.desk-history, .signal-layout, .cleanup-desk, .shell";
const PAGES = [
  { name: "desk", path: "/desk", tradeTable: true },
  { name: "founder", path: "/pm", tradeTable: true },
  { name: "customer", path: "/customer" },
  { name: "cleanup", path: "/cleanup" },
];

// ---------- fixture API ----------
let bumped = false;
let flat = false;
const clients = new Set();
function currentSnap() {
  const s = structuredClone(snapshot());
  if (bumped) s.board.open_trades[0].last_ltp = 139.95;
  if (flat) {
    s.board.open_trades = [];
    s.founder_book.index_status = { NIFTY: "STOP", BANKNIFTY: "STOP", SENSEX: "STOP" };
  }
  return s;
}
function fixtureApi(req, res, next) {
  const url = new URL(req.url, "http://fixture");
  const p = url.pathname;
  const json = (o) => {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify(o));
  };
  if (p === "/ui/stream") {
    res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "keep-alive" });
    res.write(`data: ${JSON.stringify(currentSnap())}\n\n`);
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return undefined;
  }
  if (p === "/__fixture/bump") {
    bumped = true;
    for (const c of clients) c.write(`data: ${JSON.stringify(currentSnap())}\n\n`);
    return json({ ok: true, clients: clients.size });
  }
  if (p === "/__fixture/flat") {
    flat = true;
    return json({ ok: true });
  }
  if (p === "/ui/snapshot") return json(currentSnap());
  if (p === "/paper/trace") return json(trace(url.searchParams.get("trade_id")));
  if (p === "/paper/history") return json(dayHistory(url.searchParams.get("day")));
  if (p === "/paper/ml-books" || p === "/mock/ml_paper_dashboard.json") return json(board);
  if (p === "/paper/sod-exam" || p === "/mock/sod_exam_report.json") return json(exam);
  if (p === "/founder/status") return json(founderStatus);
  if (p === "/paper/founder-book") return json(founderBook);
  if (p === "/paper/human-override") return json({ ok: false, note: "fixture" });
  return next();
}

async function measure(page) {
  return page.evaluate(() => {
    const se = document.scrollingElement;
    const vw = window.innerWidth;
    const cols = {};
    const table = document.querySelector("table.desk-history");
    if (table) {
      const box = (table.closest(".table-scroll") || table).getBoundingClientRect();
      for (const th of table.querySelectorAll("thead th")) {
        const label = th.textContent.trim().toLowerCase();
        const key = label.startsWith("p/l") ? "pnl" : label.startsWith("status") ? "status" : null;
        if (!key) continue;
        const r = th.getBoundingClientRect();
        cols[key] = { right: Math.round(r.right), limit: Math.round(Math.min(vw, box.right)), visible: r.width > 0 && r.height > 0 };
      }
      const row = table.querySelector("tbody tr");
      cols.rowHeight = row ? Math.round(row.getBoundingClientRect().height) : null;
    }
    // overflow-x:hidden on html/body would hide page scroll but still cut content off, so also list
    // elements that poke past the viewport and are not inside a deliberate scroller or clip.
    const roots = new Set([document.documentElement, document.body, document.getElementById("root"), ...document.querySelectorAll(".shell")]);
    const clipped = [];
    for (const el of document.body.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2 || (r.right <= vw + 1 && r.left >= -1)) continue;
      let a = el.parentElement;
      let contained = false;
      while (a && !roots.has(a)) {
        if (getComputedStyle(a).overflowX !== "visible") {
          contained = true;
          break;
        }
        a = a.parentElement;
      }
      if (!contained) clipped.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} right=${Math.round(r.right)}`);
    }
    const text = document.body.innerText;
    const bad = (text.match(/\b(NaN|undefined)\b/g) || []).length;
    const count = (s) => document.querySelectorAll(s).length;
    const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime;
    return {
      scrollWidth: se.scrollWidth,
      clientWidth: se.clientWidth,
      clipped: clipped.slice(0, 8),
      cols,
      bad,
      fcpMs: fcp == null ? null : Math.round(fcp),
      features: {
        alertBar: count(".alert-bar"),
        ragRows: count(".rag"),
        traceNodes: count(".trace-node"),
        charts: count(".chart-box canvas"),
        currentFields: count(".current-trade .kv"),
        accountRows: count(".account-panel .kv"),
        marketCards: count(".market-card"),
        disabledControls: count(".ctrl-btn:disabled"),
      },
    };
  });
}

function featureProblems(name, width, f) {
  if (!FEATURES) return [];
  const need = {
    desk: { alertBar: 1, traceNodes: 7, currentFields: 13, accountRows: 6, marketCards: 1 },
    founder: { alertBar: 1, ragRows: 7, traceNodes: 7, charts: 3, accountRows: 6, disabledControls: 6 },
  }[name];
  if (!need) return [];
  return Object.entries(need)
    .filter(([k, n]) => (f[k] ?? 0) < n)
    .map(([k, n]) => `${k}=${f[k]} (need ${n}) at ${width}px`);
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const outDir = mkdtempSync(join(tmpdir(), "ui-snap-"));
  const plugin = {
    name: "fixture-api",
    configurePreviewServer(server) {
      server.middlewares.use(fixtureApi);
    },
  };
  const common = { root: WEB, configFile: resolve(WEB, "vite.config.js"), logLevel: "error", build: { outDir, emptyOutDir: true } };
  await build(common);
  const server = await preview({
    ...common,
    plugins: [plugin],
    preview: { host: "127.0.0.1", port: 5199, strictPort: false, proxy: {} },
  });
  const base = server.resolvedUrls.local[0].replace(/\/$/, "");
  const browser = await chromium.launch();
  const results = [];
  try {
    for (const width of WIDTHS) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
      await ctx.route("**/*", (route) => {
        const host = new URL(route.request().url()).hostname;
        return host === "127.0.0.1" || host === "localhost" ? route.continue() : route.abort();
      });
      for (const pg of PAGES) {
        const page = await ctx.newPage();
        const errors = [];
        page.on("pageerror", (e) => errors.push(String(e)));
        const t0 = Date.now();
        await page.goto(`${base}${pg.path}`, { waitUntil: "load" });
        await page.waitForSelector(READY, { timeout: 15000 });
        const readyMs = Date.now() - t0;
        await page.waitForTimeout(900);
        const m = await measure(page);
        const overflowOk = m.scrollWidth <= m.clientWidth && m.clipped.length === 0;
        let colsOk = true;
        if (pg.tradeTable && width >= 1280) {
          for (const k of ["pnl", "status"]) {
            const c = m.cols[k];
            if (!c || !c.visible || c.right > c.limit) colsOk = false;
          }
        }
        const missing = featureProblems(pg.name, width, m.features);
        const file = resolve(OUT, `${pg.name}_${width}.png`);
        await page.screenshot({ path: file, fullPage: true });
        const pass = overflowOk && colsOk && !errors.length && !m.bad && !missing.length;
        results.push({ page: pg.name, width, ...m, readyMs, overflowOk, colsOk, missing, errors, pass, file });
        console.log(
          `${pass ? "PASS" : "FAIL"} ${pg.name.padEnd(8)} ${String(width).padStart(4)}px  scrollWidth=${m.scrollWidth} clientWidth=${m.clientWidth}` +
            (pg.tradeTable ? `  P/L=${JSON.stringify(m.cols.pnl)} Status=${JSON.stringify(m.cols.status)} rowH=${m.cols.rowHeight}` : "") +
            `  fcp=${m.fcpMs}ms ready=${readyMs}ms` +
            (m.clipped.length ? `  clipped=${JSON.stringify(m.clipped)}` : "") +
            (m.bad ? `  NaN/undefined=${m.bad}` : "") +
            (missing.length ? `  missing=${JSON.stringify(missing)}` : "") +
            (errors.length ? `  errors=${JSON.stringify(errors)}` : ""),
        );
        await page.close();
      }
      await ctx.close();
    }

    if (FEATURES) {
      // Interaction shots + push-to-DOM refresh time on the Desk (fixture flips the open ticket's LTP).
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await ctx.newPage();
      await page.goto(`${base}/desk`, { waitUntil: "load" });
      await page.waitForSelector(".grid .current-trade .kv");
      await page.locator("table.desk-history tbody tr").nth(1).click();
      await page.locator(".trace-node").nth(2).click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: resolve(OUT, "desk_1440_row_and_trace.png"), fullPage: false, clip: { x: 0, y: 0, width: 1440, height: 900 } });
      const refreshMs = await page.evaluate(async () => {
        const dd = [...document.querySelectorAll(".current-trade .kv")].find((k) => k.querySelector("dt")?.textContent === "LTP")?.querySelector("dd");
        const before = dd.textContent;
        const t0 = performance.now();
        const done = new Promise((r) => {
          new MutationObserver(() => dd.textContent !== before && r(performance.now() - t0)).observe(dd, { childList: true, subtree: true, characterData: true });
        });
        fetch("/__fixture/bump");
        return Math.round(await done);
      });
      results.push({ page: "desk-refresh", refreshMs, pass: refreshMs < 200 });
      console.log(`${refreshMs < 200 ? "PASS" : "FAIL"} refresh  push → DOM ${refreshMs} ms (target < 200 ms)`);

      // No open ticket + founder STOP on every index: the panel must say ON HOLD and why.
      await page.evaluate(() => fetch("/__fixture/flat"));
      await page.reload({ waitUntil: "load" });
      await page.waitForSelector(".current-trade__empty");
      const hold = (await page.locator(".current-trade .state-pill").first().textContent()).trim();
      await page.locator(".current-trade").screenshot({ path: resolve(OUT, "desk_1440_on_hold.png") });
      results.push({ page: "desk-on-hold", hold, pass: hold === "ON HOLD" });
      console.log(`${hold === "ON HOLD" ? "PASS" : "FAIL"} on-hold  current trade pill "${hold}"`);
      await ctx.close();
    }
  } finally {
    await browser.close();
    await new Promise((r) => server.httpServer.close(r));
    for (const c of clients) c.end();
    rmSync(outDir, { recursive: true, force: true });
  }
  writeFileSync(resolve(OUT, "results.json"), JSON.stringify(results, null, 2));
  const failed = results.filter((r) => !r.pass);
  console.log(`${results.length - failed.length}/${results.length} checks passed · screenshots in ${OUT}`);
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
