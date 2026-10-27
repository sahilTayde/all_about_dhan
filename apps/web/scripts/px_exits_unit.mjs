// PX exit labels + shadow exits (display only). Input: px_exits_fixture_response.json = TEST FIXTURE, not real data.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { boardKey, LABEL_COLOR, pxExitsView, shadowStrip, statusCard, trailText } from "../src/lib/pxExits.js";
import { deskDay, exitRule, periodNets } from "../src/lib/deskModel.js";

const body = JSON.parse(readFileSync(new URL("./px_exits_fixture_response.json", import.meta.url)));
const NOW = Date.parse("2026-10-21T13:40:30+05:30");
const v = pxExitsView(body, NOW);
assert.equal(v.ok, true);
const card = (rid) => v.open.find((o) => o.row.rule_id === rid).card;

// labels + colours from the spec
assert.equal(LABEL_COLOR.HEALTHY, "#2e7d32"); assert.equal(LABEL_COLOR.FADING, "#f9a825"); assert.equal(LABEL_COLOR.REVERSING, "#c62828");
const orb = card("PX_ORB_A");
assert.equal(orb.label, "REVERSING"); assert.equal(orb.color, "#c62828");
assert.equal(orb.now, "Now +12.6% · Peak +23.8% (785.60)");
assert.equal(orb.price, "714.70 @13:08 IST (v2_depth)");
assert.equal(orb.index, "Index +28.7 bps with us");
assert.equal(orb.slope, "3m −0.0 / 10m −5.2 bps");
assert.equal(orb.prem, "Prem 3m −0.9%");
assert.equal(orb.vwap, "WITH VWAP 74331 (idx 73969)"); assert.equal(orb.vwapAgainst, false);
assert.equal(orb.held, "76 min");
assert.equal(orb.levels, "Entry 634.65 · Stop 444.25 · Tgt 1015.44 · Trail off (BE at +30%, then HW×0.70)");
assert.equal(orb.updated, "updated 13:40:17 IST"); assert.equal(orb.stale, false);
assert.equal(statusCard(v.open[0].row, NOW + 120000).stale, true);   // > 60 s -> greyed
assert.equal(orb.liveStop, "Live stop 759.22 (trail 15% under HW 893.20 · floor 729.85)");
const eng = card("PX_ENG_5");
assert.equal(eng.label, "HEALTHY"); assert.equal(eng.vwapAgainst, true); assert.ok(eng.vwap.startsWith("AGAINST VWAP"));
assert.equal(card("PX_IB_15").label, "FADING");
assert.match(card("PX_IB_15").price, /\(1m close\)$/);
assert.deepEqual(card("PX_VWAP_CONT").na, true);                       // exit_status.error -> "status n/a"
assert.equal(statusCard({ status: "OPEN" }), null);                      // no exit_status -> show nothing

// live stop / trail text: from data only, '—' when missing
assert.equal(trailText(null), "—");
assert.equal(trailText({ live_stop: null }), "—");
assert.equal(trailText({ live_stop: 397.42, binding: "base stop", trail_armed: false, stop_floor: null, trail_gap: null }), "Live stop 397.42 (trail off, BE at +30%)");
assert.equal(trailText({ live_stop: 729.85, binding: "stop floor", hw: 800, stop_floor: 729.85, trail_gap: null }), "Live stop 729.85 (stop floor)");
const pxRow = { rule_id: "PX_ORB_A", book_id: "PX_ORB_A", underlying: "SENSEX", sig_min: "11:51", stop_px: 444.25, target_px: 1015.44, trail: "BE at +30%, then high-water x 0.70" };
assert.equal(boardKey(pxRow), "PX_ORB_A|SENSEX|11:51");
const lv = v.byKey[boardKey(pxRow)].live;
assert.match(exitRule(pxRow, lv).text, /Stop 444.25 · Target 1015.44 · Trail: Live stop 759.22 \(trail 15% under HW 893.20 · floor 729.85\)/);
assert.equal(exitRule(pxRow, lv).kind, "levels");
assert.match(exitRule(pxRow).text, /Trail: BE at \+30%, then high-water x 0.70/);   // runner text when no live data
assert.match(exitRule({ ...pxRow, trail: undefined }).text, /Trail: — ·/);         // no fixed text any more
assert.ok(!/high-water × 0.70/.test(exitRule({ ...pxRow, trail: undefined }).text));

// closed shadow strip
const s = v.strip;
assert.equal(s.label, "SHADOW, not traded");
assert.equal(s.rows.length, 2);
assert.equal(s.rows[0].actual, -21947.36); assert.equal(s.rows[0].base60, -18856.31); assert.equal(s.rows[0].ts, -18856.31);
assert.equal(s.rows[1].ts, null);            // null leg stays null ("—"), never 0
assert.equal(s.rows[1].drSkip, true); assert.equal(s.rows[1].dr, 0);
assert.equal(s.footer.t50MinusBase.n, 2); assert.equal(Math.round(s.footer.t50MinusBase.value * 100) / 100, Math.round(((-18856.31 + 18856.31) + (62590.1 - 75292.6)) * 100) / 100);
assert.equal(s.footer.tsMinusBase.n, 1); assert.equal(s.footer.tsMinusBase.of, 2); assert.equal(s.footer.tsMinusBase.value, 0);
assert.equal(s.footer.ts, -18856.31);
assert.deepEqual(shadowStrip(null).rows, []); assert.equal(shadowStrip([]).footer.actual, null);
assert.equal(v.narrow.length, 1); assert.equal(v.narrow[0].skip, true);

// missing-file states
const none = pxExitsView({ ok: true, day: "2026-10-21", sources: { rows: "missing", live_status: "missing", live_exits: "missing", shadow_overlays: "missing", shadow_narrow_open: "missing" }, rows: [], shadow_overlays: [], shadow_narrow_open: [] });
assert.equal(none.open.length, 0); assert.equal(none.strip.rows.length, 0); assert.ok(none.sources.every((x) => x.state === "missing"));
assert.equal(pxExitsView({ ok: false, status: "NO_ROUTE" }).ok, false);
assert.equal(pxExitsView(null).status, "LOADING");

// ISOLATION: shadow / label fields on board rows change no desk total
const closedPx = { book_id: "PX_EP010", rule_id: "PX_EP010", desk_status: "TRADED", closed_ist: "2026-10-21T10:20", realized_pnl_inr: -21947.36, charges_inr: 205 };
const board = (extra) => ({ session_ist_date: "2026-10-21", open_trades: [{ ...pxRow, desk_status: "TRADED", ...extra }], closed_trades: [{ ...closedPx, ...extra }] });
const shadowExtra = { exit_status: body.rows[1].exit_status, shadow_overlays: { t50: { net_inr_1_5x: 999999 } }, regime: body.rows[1].regime, shadow_narrow_open: body.rows[1].shadow_narrow_open, net_inr_1_5x: 999999 };
const a = deskDay({ board: board({}), days: [] }), b = deskDay({ board: board(shadowExtra), days: [] });
for (const k of ["total", "research", "live", "mix"]) assert.deepEqual(a[k], b[k], k);
assert.deepEqual(periodNets({ days: [{ day: "2026-10-21", net: 5, n: 1 }] }), periodNets({ days: [{ day: "2026-10-21", net: 5, n: 1 }], px_exits: body }));
// the view exposes no desk-total-shaped field
assert.ok(!("net" in v) && !("total" in v) && !("deskNet" in v));
// deskModel imports only trailText from pxExits (wording, no money)
const dm = readFileSync(new URL("../src/lib/deskModel.js", import.meta.url), "utf8");
assert.deepEqual(dm.match(/import[^;]*pxExits[^;]*;/g), ['import { trailText } from "./pxExits.js";']);
console.log("px_exits_unit ok");
