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
const state = { bumped: false, flat: false, down: false, episode: 0, indexing: false };
const clients = new Set();
function currentSnap() {
  const s = structuredClone(snapshot());
  if (state.bumped) {
    s.board.open_trades[0].last_ltp = 139.95;
    s.board.open_trades[0].last_updated_ts += 2;
  }
  if (state.flat) {
    s.board.open_trades = [];
    s.founder_book.index_status = { NIFTY: "START", BANKNIFTY: "STOP", SENSEX: "STOP" };
  }
  if (state.indexing) {
    // API still reading the model log: only today is known, the all-days totals are partial.
    s.history_complete = false;
    s.days = s.days.slice(0, 1);
    s.account = { ...s.account, net_inr: s.days[0].net, gross_inr: s.days[0].gross, charges_inr: s.days[0].charges, n_days: 1, equity_inr: 500000 + s.days[0].net };
  }
  // A new episode of the same alert (it cleared and came back): same id, new start time.
  s.alerts = s.alerts.map((a) => ({ ...a, since: `episode-${state.episode}` }));
  return s;
}
const push = () => {
  for (const c of clients) c.write(`data: ${JSON.stringify(currentSnap())}\n\n`);
};
function fixtureApi(req, res, next) {
  const url = new URL(req.url, "http://fixture");
  const p = url.pathname;
  const json = (o) => {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify(o));
  };
  if (state.down && p.startsWith("/ui/")) {
    res.statusCode = 503;
    return res.end("fixture: API down");
  }
  if (p === "/ui/stream") {
    res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "keep-alive" });
    res.write(`data: ${JSON.stringify(currentSnap())}\n\n`);
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return undefined;
  }
  if (p.startsWith("/__fixture/")) {
    const what = p.slice("/__fixture/".length);
    if (what === "bump") state.bumped = true;
    if (what === "flat") state.flat = true;
    if (what === "episode") state.episode += 1;
    if (what === "indexing") state.indexing = true;
    if (what === "down") {
      state.down = true;
      for (const c of clients) c.destroy();
      clients.clear();
    }
    push();
    return json({ ok: true, clients: clients.size });
  }
  if (state.down && p.startsWith("/ui/")) {
    res.statusCode = 503;
    return res.end("fixture: API down");
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
    // Interactive elements cut off INSIDE an overflow:hidden/clip ancestor (per axis). A scroll
    // container between the element and that ancestor makes the overflow reachable, so it is skipped.
    const clippedInside = [];
    const interactive = document.querySelectorAll(
      'button, a[href], input, select, textarea, [role="button"], [role="tab"], [tabindex]:not([tabindex="-1"])',
    );
    for (const el of interactive) {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      let scrollX = false;
      let scrollY = false;
      for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
        const cs = getComputedStyle(a);
        const b = a.getBoundingClientRect();
        const cut = (v) => v === "hidden" || v === "clip";
        const scroll = (v) => v === "auto" || v === "scroll";
        const outX = r.left < b.left - 1 || r.right > b.right + 1;
        const outY = r.top < b.top - 1 || r.bottom > b.bottom + 1;
        if ((cut(cs.overflowX) && !scrollX && outX) || (cut(cs.overflowY) && !scrollY && outY)) {
          const label = (el.textContent || el.getAttribute("aria-label") || el.tagName).trim().slice(0, 24);
          clippedInside.push(`${el.tagName.toLowerCase()} "${label}" in ${a.tagName.toLowerCase()}.${String(a.className).split(" ")[0]}`);
          break;
        }
        scrollX = scrollX || scroll(cs.overflowX);
        scrollY = scrollY || scroll(cs.overflowY);
      }
    }
    const text = document.body.innerText;
    const bad = (text.match(/\b(NaN|undefined)\b/g) || []).length;
    const count = (s) => document.querySelectorAll(s).length;
    const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime;
    return {
      scrollWidth: se.scrollWidth,
      clientWidth: se.clientWidth,
      clipped: clipped.slice(0, 8),
      clippedInside: clippedInside.slice(0, 8),
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
        const overflowOk = m.scrollWidth <= m.clientWidth && m.clipped.length === 0 && m.clippedInside.length === 0;
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
            (m.clippedInside.length ? `  clippedInside=${JSON.stringify(m.clippedInside)}` : "") +
            (m.bad ? `  NaN/undefined=${m.bad}` : "") +
            (missing.length ? `  missing=${JSON.stringify(missing)}` : "") +
            (errors.length ? `  errors=${JSON.stringify(errors)}` : ""),
        );
        await page.close();
      }
      await ctx.close();
    }

    if (FEATURES) {
      const check = (name, pass, detail) => {
        results.push({ page: name, pass: Boolean(pass), detail });
        console.log(`${pass ? "PASS" : "FAIL"} ${name.padEnd(16)} ${detail}`);
      };
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      await ctx.grantPermissions(["notifications"]);
      // Count browser notifications (the alarm) without a real OS popup.
      await ctx.addInitScript(() => {
        window.__notes = [];
        window.Notification = class {
          static permission = "granted";
          static requestPermission = async () => "granted";
          constructor(title) {
            window.__notes.push(title);
          }
        };
      });
      const page = await ctx.newPage();
      const traceHits = [];
      page.on("request", (r) => r.url().includes("/paper/trace") && traceHits.push(r.url()));
      await page.goto(`${base}/desk`, { waitUntil: "load" });
      await page.waitForSelector(".grid .current-trade .kv");

      // Alarm: enabling it must sound + notify for the CRITICAL alert that is already showing.
      await page.locator(".alert-bar .chip-btn").click();
      await page.waitForTimeout(300);
      const notes = await page.evaluate(() => window.__notes.slice());
      check("alarm-existing", notes.some((t) => t.startsWith("CRITICAL")), `notifications after Enable alarm: ${JSON.stringify(notes)}`);

      // Dismissal lasts one episode: dismiss, then the same alert starts again → it must be back.
      const critical = page.locator(".alert-bar__list li", { hasText: "Restart during an open trade" });
      await critical.locator(".icon-btn").click();
      const hidden = (await critical.count()) === 0;
      await page.evaluate(() => fetch("/__fixture/episode"));
      await page.waitForTimeout(400);
      const back = (await critical.count()) === 1;
      const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("desk.alerts.dismissed.v2") || "[]"));
      check("dismiss-episode", hidden && back && stored.length === 0, `hidden=${hidden} back-on-new-episode=${back} stale-dismissals=${stored.length}`);

      // Row + trace screenshot, then push-to-DOM refresh time (fixture flips the open ticket's LTP).
      await page.locator("table.desk-history tbody tr").nth(1).click();
      await page.locator(".trace-node").nth(2).click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: resolve(OUT, "desk_1440_row_and_trace.png"), fullPage: false, clip: { x: 0, y: 0, width: 1440, height: 900 } });
      await page.locator("table.desk-history tbody tr").first().click(); // the open ticket
      await page.waitForTimeout(300);
      const hitsBefore = traceHits.length;
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
      check("refresh", refreshMs < 200, `push → DOM ${refreshMs} ms (target < 200 ms)`);
      await page.waitForTimeout(400);
      check("trace-refresh", traceHits.length > hitsBefore, `open-ticket trace refetched after its update (${traceHits.length - hitsBefore} request)`);

      // Past day: model-log rows have no close time → Out reads "—", never "open".
      const pastDay = await page.locator(".filter-row select").first().locator("option").nth(1).getAttribute("value");
      await page.locator(".filter-row select").first().selectOption(pastDay);
      await page.waitForSelector("table.desk-history tbody tr td.col-end");
      const outs = await page.locator("table.desk-history tbody td.col-end").allTextContents();
      await page.locator(".grid > section.panel").first().screenshot({ path: resolve(OUT, "desk_1440_past_day.png") });
      check("past-day-out", outs.length > 0 && !outs.includes("open"), `${pastDay}: Out cells ${JSON.stringify([...new Set(outs)])}`);

      // No open ticket; founder has NIFTY on, SENSEX off, and SENSEX is first in the skip list.
      await page.evaluate(() => fetch("/__fixture/flat"));
      await page.reload({ waitUntil: "load" });
      await page.waitForSelector(".current-trade__empty");
      const hold = (await page.locator(".current-trade .state-pill").first().textContent()).trim();
      const why = (await page.locator(".current-trade__empty .muted").first().textContent()).trim();
      await page.locator(".current-trade").screenshot({ path: resolve(OUT, "desk_1440_on_hold.png") });
      check("on-hold", hold === "ON HOLD" && why.includes("NIFTY") && !why.includes("SENSEX"), `pill "${hold}" · ${why}`);
      await page.setViewportSize({ width: 390, height: 900 });
      await page.waitForTimeout(300);
      const cut = await page.evaluate(() =>
        [...document.querySelectorAll(".last-ticket dd")].filter((dd) => dd.scrollWidth > dd.clientWidth + 1).map((dd) => dd.textContent),
      );
      await page.locator(".current-trade").screenshot({ path: resolve(OUT, "desk_390_on_hold.png") });
      check("last-ticket-390", cut.length === 0, `truncated last-ticket values at 390px: ${JSON.stringify(cut)}`);
      await page.setViewportSize({ width: 1440, height: 900 });

      // Founder: P&L-by-stage bars add up to the book net; START/STOP fully inside its panel.
      await page.goto(`${base}/pm`, { waitUntil: "load" });
      await page.waitForSelector(".stage-total");
      const [sum, net] = await page.locator(".stage-total b").allTextContents();
      check("stage-sum", sum === net, `sum of bars ${sum} · book net ${net}`);
      await page.locator(".founder-desk").screenshot({ path: resolve(OUT, "founder_1440_trade_desk.png") });
      await page.locator(".grid > div").filter({ has: page.locator(".stage-bars") }).screenshot({ path: resolve(OUT, "founder_pnl_by_stage.png") });

      // History still indexing: every all-days / account / multi-day chart figure shows a label, no rupees.
      await page.evaluate(() => fetch("/__fixture/indexing"));
      for (const [path, need] of [["/desk", 4], ["/pm", 9]]) {
        await page.goto(`${base}${path}`, { waitUntil: "load" });
        await page.waitForSelector(".needs-history", { timeout: 5000 }).catch(() => {}); // absent = FAIL below
        await page.waitForTimeout(400);
        const cells = await page.locator(".needs-history").allInnerTexts();
        const leaks = cells.filter((t) => t.includes("₹") || !t.includes("Indexing history"));
        const allDaysTab = path === "/pm" ? await page.locator(".seg button", { hasText: "All days" }).isDisabled() : true;
        await page.screenshot({ path: resolve(OUT, `${path.slice(1)}_1440_indexing.png`), fullPage: true });
        check(
          `indexing${path}`,
          cells.length >= need && leaks.length === 0 && allDaysTab,
          `${cells.length} all-days figures show "Indexing history…", rupee leaks=${JSON.stringify(leaks)}, all-days chart tab disabled=${allDaysTab}`,
        );
      }
      state.indexing = false;

      // API down: static mock must read MOCK · OFFLINE with a banner, never PAPER.
      await page.evaluate(() => fetch("/__fixture/down"));
      for (const path of ["/desk", "/pm"]) {
        await page.goto(`${base}${path}`, { waitUntil: "load" });
        await page.waitForSelector(".offline-banner", { timeout: 8000 }).catch(() => {});
        const badge = (await page.locator(".source-pill").first().textContent()).trim();
        const banner = await page.locator(".offline-banner").count();
        await page.screenshot({ path: resolve(OUT, `${path.slice(1) || "desk"}_1440_offline.png`), clip: { x: 0, y: 0, width: 1440, height: 520 } });
        check(`offline${path}`, badge.includes("OFFLINE") && !badge.includes("PAPER") && banner === 1, `badge "${badge}" banner=${banner}`);
      }
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
