import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { backgroundView, istDay, withoutTop } from "../src/lib/backgroundTest.js";

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
{ // without top 3: box net minus 3 best unique closed; dups/open/uncounted ignored
  const c = (strategy, n, x = {}) => ({ strategy, status: "CLOSED", count_in_total: true, net_inr_1_5x: n, ...x });
  const rows = [c("A", 100), c("B", 50), c("C", 30), c("D", -10), c("E", 5), c("A2", 999, { duplicate_of: "A" }), { strategy: "O", status: "OPEN", net_inr_1_5x: null }];
  const w = withoutTop(rows, 175);
  assert.deepEqual(w.top, ["A", "B", "C"]); assert.equal(w.withoutTop3, -5);
  assert.equal(withoutTop([c("A", 1)], 1).withoutTop3, null);
}
console.log("background_test_unit: ok");
