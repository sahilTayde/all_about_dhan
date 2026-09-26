#!/usr/bin/env node
// Serve apps/web with Vite, answer every data URL from the synthetic fixture, and screenshot
// Desk / Founder / Customer at several widths. Fails (exit 1) on horizontal page overflow or when
// the trade-table P/L / Status columns sit outside the viewport at >= 1280px.
//
//   node scripts/ui_snapshots/run.mjs [--out DIR] [--widths 390,1280,1440,1920]
//
// Offline: the proxy to :8000 is disabled and any non-loopback request is aborted.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { createServer } from "vite";
import { board, exam, founderBook, founderStatus } from "./fixture.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, "../..");
const args = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
};
const OUT = resolve(arg("out", resolve(HERE, "out")));
const WIDTHS = arg("widths", "390,1280,1440,1920").split(",").map(Number);
const PAGES = [
  { name: "desk", path: "/desk", tradeTable: true },
  { name: "founder", path: "/pm", tradeTable: true },
  { name: "customer", path: "/customer", tradeTable: false },
];

const JSON_ROUTES = [
  [/\/(paper\/ml-books|mock\/ml_paper_dashboard\.json)/, board],
  [/\/(paper\/sod-exam|mock\/sod_exam_report\.json)/, exam],
  [/\/founder\/status/, founderStatus],
  [/\/paper\/founder-book/, founderBook],
  [/\/paper\/human-override/, { ok: false, note: "fixture" }],
];

async function main() {
  mkdirSync(OUT, { recursive: true });
  const server = await createServer({
    root: WEB,
    configFile: resolve(WEB, "vite.config.js"),
    logLevel: "error",
    server: { host: "127.0.0.1", port: 5199, strictPort: false, proxy: {} },
  });
  await server.listen();
  const base = server.resolvedUrls.local[0].replace(/\/$/, "");
  const browser = await chromium.launch();
  const results = [];
  try {
    for (const width of WIDTHS) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
      await ctx.route("**/*", (route) => {
        const url = new URL(route.request().url());
        if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") return route.abort();
        const hit = JSON_ROUTES.find(([re]) => re.test(url.pathname));
        if (hit) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(hit[1]) });
        return route.continue();
      });
      for (const pg of PAGES) {
        const page = await ctx.newPage();
        const errors = [];
        page.on("pageerror", (e) => errors.push(String(e)));
        await page.goto(`${base}${pg.path}`, { waitUntil: "networkidle" });
        await page.waitForTimeout(600);
        const m = await page.evaluate(() => {
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
              const visible = r.width > 0 && r.height > 0;
              cols[key] = { right: Math.round(r.right), limit: Math.round(Math.min(vw, box.right)), visible };
            }
            const row = table.querySelector("tbody tr");
            cols.rowHeight = row ? Math.round(row.getBoundingClientRect().height) : null;
          }
          // overflow-x:hidden on html/body hides page scroll but still cuts content off, so also
          // list elements that poke past the viewport and are not inside a deliberate scroller/clip.
          const roots = new Set([
            document.documentElement,
            document.body,
            document.getElementById("root"),
            ...document.querySelectorAll(".shell"),
          ]);
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
          return { scrollWidth: se.scrollWidth, clientWidth: se.clientWidth, clipped: clipped.slice(0, 8), cols, title: document.title };
        });
        const overflowOk = m.scrollWidth <= m.clientWidth && m.clipped.length === 0;
        let colsOk = true;
        if (pg.tradeTable && width >= 1280) {
          for (const k of ["pnl", "status"]) {
            const c = m.cols[k];
            if (!c || !c.visible || c.right > c.limit) colsOk = false;
          }
        }
        const file = resolve(OUT, `${pg.name}_${width}.png`);
        await page.screenshot({ path: file, fullPage: true });
        const r = { page: pg.name, width, ...m, overflowOk, colsOk, errors, file };
        results.push(r);
        const tag = overflowOk && colsOk && !errors.length ? "PASS" : "FAIL";
        console.log(
          `${tag} ${pg.name.padEnd(8)} ${String(width).padStart(4)}px  scrollWidth=${m.scrollWidth} clientWidth=${m.clientWidth}` +
            (pg.tradeTable ? `  P/L=${JSON.stringify(m.cols.pnl)} Status=${JSON.stringify(m.cols.status)} rowH=${m.cols.rowHeight}` : "") +
            (m.clipped.length ? `  clipped=${JSON.stringify(m.clipped)}` : "") +
            (errors.length ? `  errors=${JSON.stringify(errors)}` : ""),
        );
        await page.close();
      }
      await ctx.close();
    }
  } finally {
    await browser.close();
    await server.close();
  }
  writeFileSync(resolve(OUT, "results.json"), JSON.stringify(results, null, 2));
  const failed = results.filter((r) => !r.overflowOk || !r.colsOk || r.errors.length);
  console.log(`${results.length - failed.length}/${results.length} checks passed · screenshots in ${OUT}`);
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
