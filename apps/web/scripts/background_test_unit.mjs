import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { backgroundView, istDay } from "../src/lib/backgroundTest.js";

assert.equal(backgroundView({ ok: false, status: "NO_DATA" }).ok, false);
assert.equal(backgroundView(null).rows.length, 0);
const body = { ok: true, summary: { closed_unique: 1, net_inr_1_5x: 100, failed: 1 },
  trades: [{ strategy: "B2", verified: "PASS" }, { strategy: "X", verified: "FAIL" }] };
assert.equal(backgroundView(body).rows.length, 1);           // FAIL hidden by default
assert.equal(backgroundView(body, true).rows.length, 2);     // toggle shows it
assert.equal(backgroundView(body).net, 100);
assert.equal(istDay(Date.parse("2026-10-12T19:00:00Z")), "2026-10-13");
// isolation: no desk total module reads the background test
for (const f of ["src/lib/deskModel.js", "src/components/TopBar.jsx", "src/components/PnlChart.jsx", "src/pages/HistoryPage.jsx", "src/pages/StrategiesPage.jsx", "src/pages/SignalsPage.jsx"]) {
  assert.ok(!/backgroundTest|BackgroundTest|background-test/.test(readFileSync(new URL(`../${f}`, import.meta.url), "utf8")), f);
}
console.log("background_test_unit: ok");
