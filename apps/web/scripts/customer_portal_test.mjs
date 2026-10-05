#!/usr/bin/env node
// Playwright: `/` empty HOLD + one CALL ticket. Screenshots under /opt/cursor/artifacts.
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { build, preview } from "vite";
import { emptyDeskFixture, oneTicketFixture } from "../src/lib/customerPortal.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, "..");
const ART = "/opt/cursor/artifacts";
mkdirSync(ART, { recursive: true });

const emptyRaw = {
  meta: { source: "mock", label: "MOCK", placeholder: true, asOf: "2026-10-04T11:00:00+05:30" },
  underlyings: ["NIFTY"],
  signals: emptyDeskFixture().signals,
  todaysBook: { label: "PAPER", rows: [] },
};
const ticketRaw = {
  meta: { source: "mock", label: "MOCK", placeholder: true, asOf: "2026-10-04T11:05:00+05:30" },
  underlyings: ["NIFTY"],
  signals: oneTicketFixture().signals,
  todaysBook: oneTicketFixture().book,
};

const state = { which: "empty" };

function fixtureApi(req, res, next) {
  const url = new URL(req.url, "http://fixture");
  if (url.pathname === "/v2/snapshot" || url.pathname === "/v2/customer/signals") {
    res.statusCode = 404;
    return res.end("no signals:public");
  }
  if (url.pathname === "/mock/signal.json") {
    res.setHeader("content-type", "application/json");
    return res.end(JSON.stringify(state.which === "empty" ? emptyRaw : ticketRaw));
  }
  return next();
}

async function shot(page, name) {
  const file = resolve(ART, name);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function main() {
  const outDir = mkdtempSync(join(tmpdir(), "c5-03-"));
  const common = {
    root: WEB,
    configFile: resolve(WEB, "vite.config.js"),
    logLevel: "error",
    build: { outDir, emptyOutDir: true },
  };
  await build(common);
  const server = await preview({
    ...common,
    plugins: [
      {
        name: "c5-fixture",
        configurePreviewServer(s) {
          s.middlewares.use(fixtureApi);
        },
      },
    ],
    preview: { host: "127.0.0.1", port: 5201, strictPort: false, proxy: {} },
  });
  const base = server.resolvedUrls.local[0].replace(/\/$/, "");
  const browser = await chromium.launch();
  const fails = [];
  try {
    for (const [name, which, check] of [
      [
        "empty",
        "empty",
        async (page) => {
          const hero = (await page.locator("[data-testid=customer-hero]").innerText()).toUpperCase();
          const badge = await page.locator("[data-mode-badge]").first().innerText();
          const emptyBook = await page.locator("[data-testid=book-empty]").count();
          if (!hero.includes("HOLD")) fails.push("empty hero missing HOLD");
          if (badge !== "MOCK") fails.push(`empty badge ${badge}`);
          if (!emptyBook) fails.push("empty book missing");
          if (badge.toUpperCase() === "LIVE") fails.push("empty showed LIVE");
          if ((await page.locator("button", { hasText: /buy|sell|order/i }).count()) > 0) {
            fails.push("empty has order button");
          }
        },
      ],
      [
        "ticket",
        "ticket",
        async (page) => {
          const hero = (await page.locator("[data-testid=customer-hero]").innerText()).toUpperCase();
          const card = await page.locator("[data-testid=customer-ticket]").innerText();
          const risk = await page.locator("[data-testid=risk-strip]").innerText();
          const badge = await page.locator("[data-mode-badge]").first().innerText();
          if (!hero.includes("CALL")) fails.push("ticket hero missing CALL");
          if (!card.includes("25,000") && !card.includes("25000")) fails.push("ticket missing strike");
          if (!card.includes("120")) fails.push("ticket missing entry");
          if (!risk.toLowerCase().includes("invalid")) fails.push("risk strip missing");
          if (!["MOCK", "PAPER", "SHADOW"].includes(badge)) fails.push(`bad badge ${badge}`);
          if (badge.toUpperCase() === "LIVE") fails.push("ticket showed LIVE");
        },
      ],
    ]) {
      state.which = which;
      const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
      await page.goto(`${base}/`, { waitUntil: "load" });
      await page.waitForSelector("[data-testid=customer-hero]", { timeout: 15000 });
      await check(page);
      await shot(page, `c5-03-${name}-390.png`);
      await page.setViewportSize({ width: 1280, height: 800 });
      await shot(page, `c5-03-${name}-1280.png`);
      await page.close();
    }
  } finally {
    await browser.close();
    try {
      await server.close();
    } catch {
      /* preview already down */
    }
  }
  const log = resolve(ART, "c5-03-portal-tests.txt");
  writeFileSync(log, fails.length ? `FAIL\n${fails.join("\n")}\n` : "PASS empty HOLD + one CALL ticket\n");
  if (fails.length) {
    console.error(fails.join("\n"));
    process.exit(1);
  }
  console.log("PASS customer_portal_test empty + ticket");
}

main();
