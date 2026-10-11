#!/usr/bin/env node
// Crisp running-trade section shots. Viewport 1440×900 (and 390) at deviceScaleFactor 2.
// One clip per section — never full-page shrink.
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { build, preview } from "vite";
import { board, dayHistory, exam, founderBook, founderControls, founderStatus, snapshot, trace } from "./fixture.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, "../..");
const ART = resolve(process.argv.includes("--out") ? process.argv[process.argv.indexOf("--out") + 1] : "/opt/cursor/artifacts/after");

function fixtureApi(req, res, next) {
  const url = new URL(req.url, "http://fixture");
  const p = url.pathname;
  const json = (o) => {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify(o));
  };
  if (p === "/ui/stream" || p === "/v2/stream") {
    res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
    res.write(`data: ${JSON.stringify(snapshot())}\n\n`);
    return undefined;
  }
  if (p === "/ui/snapshot" || p === "/v2/snapshot") return json(snapshot());
  if (p === "/paper/trace" || p === "/v2/trace") return json(trace(url.searchParams.get("trade_id")));
  if (p === "/paper/journal") return json({ ok: true, day: board.session_ist_date, n: (board.decision_journal || []).length, rows: board.decision_journal, orders: "REFUSED", promote: false });
  if (p === "/paper/history") return json(dayHistory(url.searchParams.get("day")));
  if (p === "/paper/ml-books") return json(board);
  if (p === "/paper/sod-exam") return json(exam);
  if (p === "/founder/status") return json(founderStatus);
  if (p === "/founder/controls") return json(founderControls);
  if (p === "/paper/founder-book") return json(founderBook);
  return next();
}

async function sectionShot(page, sel, file, vw, vh) {
  const el = page.locator(sel).first();
  await el.waitFor({ timeout: 15000 });
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  const box = await el.boundingBox();
  if (!box) throw new Error(`no box for ${sel}`);
  const x = Math.max(0, Math.floor(box.x));
  const y = Math.max(0, Math.floor(box.y));
  const clip = {
    x,
    y,
    width: Math.max(1, Math.min(Math.ceil(box.width), vw - x)),
    height: Math.max(1, Math.min(Math.ceil(box.height), vh - y)),
  };
  await page.screenshot({ path: file, fullPage: false, clip });
  return file;
}

async function main() {
  mkdirSync(ART, { recursive: true });
  const outDir = mkdtempSync(join(tmpdir(), "run-trade-"));
  const common = {
    root: WEB,
    configFile: resolve(WEB, "vite.config.js"),
    logLevel: "error",
    build: { outDir, emptyOutDir: true },
  };
  await build(common);
  const plugin = {
    name: "fixture-api",
    configurePreviewServer(server) {
      server.middlewares.use(fixtureApi);
    },
  };
  const server = await preview({
    ...common,
    plugins: [plugin],
    preview: { host: "127.0.0.1", port: 5203, strictPort: false, proxy: {} },
  });
  const base = server.resolvedUrls.local[0].replace(/\/$/, "");
  const browser = await chromium.launch();
  const files = [];
  try {
    const desk = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
    await desk.route("**/*", (route) => {
      const host = new URL(route.request().url()).hostname;
      return host === "127.0.0.1" || host === "localhost" ? route.continue() : route.abort();
    });
    const page = await desk.newPage();
    await page.goto(`${base}/desk`, { waitUntil: "load" });
    await page.waitForSelector("[data-testid=open-positions] [data-testid=pos-card]");
    await page.waitForTimeout(700);
    files.push(await sectionShot(page, "[data-testid=pos-card]", join(ART, "running_trade_1440.png"), 1440, 900));
    files.push(await sectionShot(page, "[data-testid=open-positions]", join(ART, "running_trade_dual_1440.png"), 1440, 900));
    files.push(await sectionShot(page, "[data-testid=desk-today]", join(ART, "desk_today_1440.png"), 1440, 900));
    files.push(await sectionShot(page, "[data-testid=trade-pipeline]", join(ART, "desk_pipeline_1440.png"), 1440, 900));

    await page.goto(`${base}/`, { waitUntil: "load" });
    await page.waitForSelector("[data-testid=customer-portal]");
    await page.waitForTimeout(700);
    if ((await page.locator("[data-testid=open-positions]").count()) > 0) {
      files.push(await sectionShot(page, "[data-testid=open-positions]", join(ART, "customer_running_1440.png"), 1440, 900));
    }
    files.push(await sectionShot(page, "[data-testid=customer-portal]", join(ART, "customer_1440.png"), 1440, 900));

    await page.goto(`${base}/pm`, { waitUntil: "load" });
    await page.waitForSelector("[data-testid=founder-shell]");
    await page.waitForTimeout(700);
    files.push(await sectionShot(page, "[data-testid=open-positions]", join(ART, "founder_running_1440.png"), 1440, 900));
    files.push(await sectionShot(page, "[data-testid=founder-shell]", join(ART, "founder_overview_1440.png"), 1440, 900));
    await page.close();
    await desk.close();

    const phone = await browser.newContext({ viewport: { width: 390, height: 900 }, deviceScaleFactor: 2 });
    await phone.route("**/*", (route) => {
      const host = new URL(route.request().url()).hostname;
      return host === "127.0.0.1" || host === "localhost" ? route.continue() : route.abort();
    });
    const p390 = await phone.newPage();
    await p390.goto(`${base}/desk`, { waitUntil: "load" });
    await p390.waitForSelector("[data-testid=open-positions] [data-testid=pos-card]");
    await p390.waitForTimeout(500);
    files.push(await sectionShot(p390, "[data-testid=open-positions]", join(ART, "running_trade_390.png"), 390, 900));
    await p390.close();
    await phone.close();
  } finally {
    await browser.close();
    await new Promise((r) => server.httpServer.close(r));
    rmSync(outDir, { recursive: true, force: true });
  }
  for (const f of files) console.log(f);
  console.log(`running_shots: ${files.length} files in ${ART}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
