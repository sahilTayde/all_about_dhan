import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { clock, hasGap, labShadowView, tradeKey } from "../src/lib/labShadow.js";

// TEST FIXTURE rows (made up, src=TEST_FIXTURE) — same shape the API returns for events.csv; bare HH:MM like the real feed
const r = (strategy, status, und, side, strike, entry, net15, x = {}) => ({
  seen_ist: "09:51", lag_min: 20, strategy, family: "F", status, und, side, strike, sig: "09:31", entry,
  exit: "09:52", ask_in: 100, bid_out: 110, net15, rand15: null, data_gap: null, situation: null, reason: null, src: "TEST_FIXTURE", ...x });

assert.equal(labShadowView({ ok: false, status: "NO_DATA" }).ok, false);
assert.equal(labShadowView(null).status, "NO_DATA");
assert.equal(clock("2026-10-19 09:51"), "09:51"); assert.equal(clock("2026-10-19T9:05:00+05:30"), "09:05");
assert.equal(clock("09:51"), "09:51"); assert.equal(clock(null), null);
assert.equal(tradeKey(r("A", "PRIMARY", "NIFTY", "PE", 25000, null, 1)), null); // missing part: never merged

{ // overlap: R01 + B3a same trade -> shown once under the higher status, "also" names the other, counted once
  const v = labShadowView({ ok: true, rows: [
    r("B3a", "WATCH", "NIFTY", "PE", 25000, "09:32", 6420),
    r("R01", "PRIMARY", "NIFTY", "PE", 25000, "2026-10-19 09:32", 6420, { seen_ist: "2026-10-19 09:51" }), // full form still ok
    r("ORB_A", "WATCH", "NIFTY", "CE", 25100, "10:01", -5210.5, { seen_ist: "10:21" }),
    r("B2", "PRIMARY", "SENSEX", "PE", 81800, "11:31", null, { seen_ist: "11:51", exit: null, bid_out: null }),
    r("B2", "PRIMARY", "SENSEX", "CE", 82000, "10:31", 2675.25, { seen_ist: "10:51" }),
    r("MOM_5", "PARKED", "NIFTY", "PE", 24900, "11:01", -4380, { seen_ist: "11:21" }),
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
    r("R01", "PRIMARY", "NIFTY", "PE", 25000, "09:17", null, { seen_ist: "09:16", exit: null }),
    r("R01", "PRIMARY", "NIFTY", "PE", 25000, "09:17", 500, { seen_ist: "09:46" }),
  ] });
  assert.equal(v.trades.length, 1); assert.equal(v.trades[0].net15, 500); assert.equal(v.feedStarts, null);
  assert.equal(v.groups[0].strategies[0].trades, 1);
}
{ // the real 2026-10-19 feed line, verbatim, parsed the way the API does (bare HH:MM, empty rand15/data_gap/situation)
  const HEADER = "seen_ist,lag_min,strategy,family,status,und,side,strike,sig,entry,exit,ask_in,bid_out,net15,rand15,data_gap,situation,reason,src";
  const LINE = '10:45,21,R01_PDIV_5_ALL_H20,trend,PRIMARY,NIFTY,CE,23100,10:24,10:25,10:45,55.65,41.1,-9629.69,,,,"slot rule R01_PDIV_5_ALL_H20 signal 10:24, exit time",trades';
  const cells = [...LINE.matchAll(/("([^"]*)"|[^,]*)(,|$)/g)].slice(0, 19).map((m) => (m[2] ?? m[1]));
  const NUM = ["lag_min", "strike", "ask_in", "bid_out", "net15", "rand15"];
  const row = Object.fromEntries(HEADER.split(",").map((h, i) => [h, cells[i] === "" ? null : NUM.includes(h) ? Number(cells[i]) : cells[i]]));
  assert.equal(row.reason, "slot rule R01_PDIV_5_ALL_H20 signal 10:24, exit time"); assert.equal(row.src, "trades");
  const twin = { ...row, strategy: "B3a_PDIV5_VOLHIGH", reason: "slot rule B3a_PDIV5_VOLHIGH signal 10:24, exit time" };
  const late = { ...row, seen_ist: "2026-10-19 11:07", entry: "2026-10-19 10:47", strike: 23050, net15: 7160.4, rand15: 500, data_gap: "bid missing 10:52" };
  const v = labShadowView({ ok: true, rows: [late, row, twin] });
  assert.equal(clock(row.seen_ist), "10:45"); assert.equal(clock(row.entry), "10:25");
  assert.equal(tradeKey(row), "NIFTY|CE|23100|10:25"); assert.equal(tradeKey({ ...row, entry: "2026-10-19 10:25" }), tradeKey(row));
  assert.equal(v.trades.length, 2); assert.deepEqual(v.trades.map((t) => clock(t.seen_ist)), ["10:45", "11:07"]); // sorted, mixed forms
  assert.deepEqual(v.trades[0].also, ["B3a_PDIV5_VOLHIGH"]);
  assert.equal(v.feedStarts, "10:45");
  const g = v.groups[0].strategies[0];
  assert.equal(g.strategy, "R01_PDIV_5_ALL_H20"); assert.equal(g.trades, 2); assert.equal(g.net15, -2469.29);
  assert.equal(g.rand15, 500); assert.equal(g.withRand, 1); assert.equal(g.dataGaps, 1); // random only where given
  assert.equal(hasGap(row), false); assert.equal(hasGap(late), true);
  const only = labShadowView({ ok: true, rows: [row] }).groups[0].strategies[0];
  assert.equal(only.rand15, null); assert.equal(only.dataGaps, 0); // empty random stays — (never filled in)
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
