import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { clock, compareKind, comparison, hasGap, isLabCell, labShadowView, tradeKey } from "../src/lib/labShadow.js";

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
  assert.equal(v.trades.length, 5); assert.equal(v.merged, 1); assert.equal(v.aliased, 1); assert.equal(v.updated, 0);
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
  assert.equal(v.updated, 1); assert.equal(v.aliased, 0);
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
  assert.deepEqual(g.cmp, []); assert.equal(g.dataGaps, 1); // slot-rule trade rows have no comparison kind -> —
  assert.equal(hasGap(row), false); assert.equal(hasGap(late), true);
  const only = labShadowView({ ok: true, rows: [row] }).groups[0].strategies[0];
  assert.deepEqual(only.cmp, []); assert.equal(only.dataGaps, 0); // empty rand15 stays — (never filled in)
}
{ // comparison kinds (rand15 means different things per row type; live_runner.py normalize())
  const base = { status: "WATCH", und: "NIFTY", side: "CE", strike: 23100, entry: "10:25", seen_ist: "13:05", data_gap: null, situation: null };
  const row = (x) => ({ ...base, ...x });
  // real lines from the 2026-10-19 lab feed (F2 / G5), as parsed
  const F2 = row({ strategy: "F2_UNWIND", family: "exit-overlay", side: null, strike: null, entry: "10:25", net15: -1852.17, rand15: -9629.69, reason: "F2 on R01_PDIV_5_ALL_H20 hit=1 (vs base)", src: "f2unwind" });
  const G5 = row({ strategy: "G5_UNWIND", family: "exit-overlay", side: "PE", strike: 73800, und: "SENSEX", entry: "13:27", net15: -1109.53, rand15: -1109.53, reason: "G5 skip=0 on R01_PDIV_5_ALL_H20 (vs base)", src: "g5unwind" });
  const QT = row({ strategy: "QT:QT_P15", family: "exit-overlay", net15: 900, rand15: 300, reason: "QT_P15 on R01_PDIV_5_ALL_H20 (vs random exit)", src: "quicktarget" });
  const FR = row({ strategy: "FRESH:G06", family: "exit-overlay", net15: 400, rand15: -100, reason: "G06 exit on R01_PDIV_5_ALL_H20 (vs base G00)", src: "freshexits" });
  const AC = row({ strategy: "ANTICHASE_AC1", family: "exit-overlay", net15: 0, rand15: -2000, reason: "anti-chase skip=True rise3=0.15 (vs base)", src: "antichase" });
  const RT = row({ strategy: "ROUTER:R07FEAR", family: "trend", entry: null, net15: 50, rand15: 20, reason: "router arm R07FEAR in calm", src: "parked_router", situation: "calm" });
  const RT2 = row({ strategy: "ROUTER:F2", family: "exit-overlay", entry: null, net15: 70, rand15: 10, reason: "router arm F2 in trend", src: "parked_router" });
  const GB = row({ strategy: "GBV:GB30", family: "exit-overlay", entry: "11:09", net15: 1200, rand15: 150, reason: "giveback GB30 on R01_PDIV_5_ALL_H20", src: "gbv" });
  const CELL = row({ strategy: "B2", family: "breakout", strike: null, entry: "11:31", net15: 700, rand15: -250, reason: "twoday cell B2_c3 fired 11:31", src: "twoday" });
  const OV = row({ strategy: "XO", family: "exit-overlay", entry: "12:00", net15: 10, rand15: 5, reason: "some overlay", src: "x" });
  const OVR = row({ strategy: "XR", family: "exit-overlay", entry: "12:01", net15: 10, rand15: 5, reason: "overlay vs random entry", src: "x" });
  const TR = row({ strategy: "R01_PDIV_5_ALL_H20", family: "trend", entry: "12:02", net15: 10, rand15: 5, reason: "slot rule R01_PDIV_5_ALL_H20 signal 12:01, exit time", src: "trades" });
  assert.equal(compareKind(QT), "vs random exit");
  for (const r of [F2, G5, FR, AC, OV]) assert.equal(compareKind(r), "vs base", r.strategy);
  assert.equal(compareKind(RT), "vs base/random"); assert.equal(compareKind(RT2), "vs base/random"); // before the overlay fallback
  assert.equal(compareKind(GB), "random"); assert.equal(compareKind(CELL), "random"); assert.ok(isLabCell(CELL));
  assert.ok(isLabCell({ src: "harvest", reason: "" })); assert.ok(!isLabCell(TR));
  assert.equal(compareKind(OVR), null); assert.equal(compareKind(TR), null); // overlay mentioning random / plain trade -> —
  assert.equal(compareKind({ ...F2, rand15: null }), null); // empty rand15 -> no comparison, never filled
  assert.deepEqual(comparison(F2), { kind: "vs base", value: -9629.69, delta: 7777.52 }); // overlay added +7,777.52
  assert.deepEqual(comparison(G5), { kind: "vs base", value: -1109.53, delta: 0 });
  assert.equal(comparison(QT).delta, null); assert.equal(comparison(GB).delta, null); // delta only for vs base

  // per strategy: each kind keeps its own sum; a vs-base value never enters the random sum
  const mixed = [
    row({ ...GB, strategy: "MIXED", entry: "09:30" }),                              // random 150
    row({ ...F2, strategy: "MIXED", entry: "09:31", side: "CE", strike: 1 }),        // vs base -9629.69, delta +7777.52
    row({ ...AC, strategy: "MIXED", entry: "09:32" }),                               // vs base -2000, delta +2000
    row({ ...TR, strategy: "MIXED", entry: "09:33", rand15: null }),                 // none
  ];
  const v = labShadowView({ ok: true, rows: [...mixed, F2, G5] });
  const m = v.groups[0].strategies.find((s) => s.strategy === "MIXED");
  assert.equal(m.trades, 4);
  assert.deepEqual(m.cmp.map((c) => [c.kind, c.sum, c.k, c.delta]), [["random", 150, 1, null], ["vs base", -11629.69, 2, 9777.52]]);
  const rnd = m.cmp.find((c) => c.kind === "random"); assert.equal(rnd.sum, 150); // no vs-base number leaked in
  const f2 = v.groups[0].strategies.find((s) => s.strategy === "F2_UNWIND");
  assert.deepEqual(f2.cmp.map((c) => [c.kind, c.sum, c.delta]), [["vs base", -9629.69, 7777.52]]);
  assert.ok(!v.groups.some((g) => g.strategies.some((s) => s.cmp.some((c) => c.kind === "random" && s.strategy === "F2_UNWIND"))));
  assert.equal(v.trades.find((t) => t.strategy === "G5_UNWIND").cmp.kind, "vs base");
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
