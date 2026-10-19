import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { clock, labShadowView, tradeKey } from "../src/lib/labShadow.js";

// TEST FIXTURE rows (made up, src=TEST_FIXTURE) — same shape the API returns for events.csv
const r = (strategy, status, und, side, strike, entry, net15, x = {}) => ({
  seen_ist: "2026-10-19 09:51", lag_min: 20, strategy, family: "F", status, und, side, strike, sig: "09:31", entry,
  exit: "09:52", ask_in: 100, bid_out: 110, net15, reason: null, src: "TEST_FIXTURE", ...x });

assert.equal(labShadowView({ ok: false, status: "NO_DATA" }).ok, false);
assert.equal(labShadowView(null).status, "NO_DATA");
assert.equal(clock("2026-10-19 09:51"), "09:51"); assert.equal(clock("2026-10-19T9:05:00+05:30"), "09:05");
assert.equal(clock("09:51"), "09:51"); assert.equal(clock(null), null);
assert.equal(tradeKey(r("A", "PRIMARY", "NIFTY", "PE", 25000, null, 1)), null); // missing part: never merged

{ // overlap: R01 + B3a same trade -> shown once under the higher status, "also" names the other, counted once
  const v = labShadowView({ ok: true, rows: [
    r("B3a", "WATCH", "NIFTY", "PE", 25000, "09:32", 6420),
    r("R01", "PRIMARY", "NIFTY", "PE", 25000, "09:32", 6420),
    r("ORB_A", "WATCH", "NIFTY", "CE", 25100, "10:01", -5210.5, { seen_ist: "2026-10-19 10:21" }),
    r("B2", "PRIMARY", "SENSEX", "PE", 81800, "11:31", null, { seen_ist: "2026-10-19 11:51", exit: null, bid_out: null }),
    r("B2", "PRIMARY", "SENSEX", "CE", 82000, "10:31", 2675.25, { seen_ist: "2026-10-19 10:51" }),
    r("MOM_5", "PARKED", "NIFTY", "PE", 24900, "11:01", -4380, { seen_ist: "2026-10-19 11:21" }),
  ] });
  assert.equal(v.trades.length, 5); assert.equal(v.merged, 1);
  const r01 = v.trades.find((t) => t.strategy === "R01");
  assert.deepEqual(r01.also, ["B3a"]); assert.ok(!v.trades.some((t) => t.strategy === "B3a"));
  assert.deepEqual(v.groups.map((g) => g.status), ["PRIMARY", "WATCH", "PARKED"]);
  const prim = v.groups[0].strategies;
  assert.deepEqual(prim.map((s) => [s.strategy, s.trades, s.net15]), [["R01", 1, 6420], ["B2", 2, 2675.25]]); // open B2 net not invented
  assert.equal(prim[1].withNet, 1);
  assert.deepEqual(v.groups[1].strategies.map((s) => s.strategy), ["ORB_A"]); // B3a not counted under WATCH
  assert.equal(v.feedStarts, "09:51"); // first row after 09:20
  assert.deepEqual(v.trades.map((t) => clock(t.seen_ist)), ["09:51", "10:21", "10:51", "11:21", "11:51"]);
}
{ // same name listed twice: newer numbers, counted once; first row at 09:16 -> no feed-starts note
  const v = labShadowView({ ok: true, rows: [
    r("R01", "PRIMARY", "NIFTY", "PE", 25000, "09:17", null, { seen_ist: "2026-10-19 09:16", exit: null }),
    r("R01", "PRIMARY", "NIFTY", "PE", 25000, "09:17", 500, { seen_ist: "2026-10-19 09:46" }),
  ] });
  assert.equal(v.trades.length, 1); assert.equal(v.trades[0].net15, 500); assert.equal(v.feedStarts, null);
  assert.equal(v.groups[0].strategies[0].trades, 1);
}
// isolation: no desk total / paper-extra module reads the lab shadow feed
const totals = ["src/lib/deskModel.js", "src/components/TopBar.jsx", "src/components/PnlChart.jsx", "src/pages/HistoryPage.jsx",
  "src/pages/StrategiesPage.jsx", "src/pages/SignalsPage.jsx", "src/lib/backgroundTest.js", "src/components/BackgroundTestBox.jsx",
  ...readdirSync(new URL("../src/lib/", import.meta.url)).filter((f) => /paper|extra|desk|feed/i.test(f) && f !== "labShadow.js").map((f) => `src/lib/${f}`)];
for (const f of totals) {
  let src; try { src = readFileSync(new URL(`../${f}`, import.meta.url), "utf8"); } catch { continue; }
  assert.ok(!/labShadow|LabShadow|lab-shadow|lab_shadow/.test(src), f);
}
// LivePage only renders the panel; it never passes it a total or reads its numbers
const live = readFileSync(new URL("../src/pages/LivePage.jsx", import.meta.url), "utf8");
assert.equal((live.match(/<LabShadowPanel[^>]*>/g) || []).join(), "<LabShadowPanel />"); // rendered once, no props
assert.ok(!/labShadowView|fetchLabShadow|labShadow\.js/.test(live));
assert.ok(/<LabShadowPanel \/>/.test(live));
console.log("lab_shadow_unit: ok");
