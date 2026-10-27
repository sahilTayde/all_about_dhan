import assert from "node:assert/strict";
import { deskDay } from "../src/lib/deskModel.js";

// Fallback (no feed day row): Today must not add MIX/shadow rows (e.g. the 25-lot MIX-DEFAULT-BUY losses).
const board = {
  session_ist_date: "2026-10-12",
  open_trades: [],
  closed_trades: [
    { book_id: "R01_PDIV_5_ALL_H20", desk_status: "TRADED", closed_ist: "2026-10-12T12:53", realized_pnl_inr: 5000, charges_inr: 60 },
    { book_id: "MIX-DEFAULT-BUY", closed_ist: "2026-10-12T09:52", realized_pnl_inr: -27117.61, charges_inr: 90 },
    { book_id: "R15_X", desk_status: "SHADOW", shadow: true, closed_ist: "2026-10-12T11:00", realized_pnl_inr: 1200, charges_inr: 40 },
  ],
};
const d = deskDay({ board, days: [] });
assert.equal(d.total.fromFeed, false);
assert.equal(d.total.net, 5000);
assert.equal(d.total.charges, 60);
assert.equal(d.total.n, 1);
// Feed path unchanged
assert.equal(deskDay({ board, days: [{ day: "2026-10-12", net: 4940, charges: 60, n: 1, wins: 1 }] }).total.net, 4940);
console.log("desk_today_unit ok");
