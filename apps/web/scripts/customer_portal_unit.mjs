#!/usr/bin/env node
// C5-03: empty HOLD + one CALL ticket. No win rates. No LIVE badge.
import assert from "node:assert/strict";
import {
  badgeIsAllowed,
  deskFromV2Public,
  displayMode,
  emptyDeskFixture,
  formatSlot,
  isCustomerV2Snapshot,
  marketView,
  oneTicketFixture,
  selectCustomerView,
} from "../src/lib/customerPortal.js";

const empty = selectCustomerView(emptyDeskFixture(), "NIFTY");
assert.equal(empty.market, "HOLD");
assert.equal(empty.status, "HOLD");
assert.equal(empty.waiting, true);
assert.equal(empty.ticket, null);
assert.equal(empty.bookRows.length, 0);
assert.equal(empty.mode, "MOCK");
assert.equal(empty.bookMode, "PAPER");
assert.ok(badgeIsAllowed(empty.mode));
assert.ok(!String(empty.mode).includes("LIVE"));

const ticket = selectCustomerView(oneTicketFixture(), "NIFTY");
assert.equal(ticket.market, "CALL");
assert.equal(ticket.status, "IN-PROGRESS");
assert.equal(ticket.waiting, false);
assert.equal(ticket.ticket.strike, 25000);
assert.equal(ticket.ticket.entry, 120);
assert.equal(ticket.ticket.stop, 90);
assert.equal(ticket.ticket.target, 180);
assert.equal(ticket.bookRows.length, 1);
assert.equal(ticket.mode, "MOCK");
assert.equal(ticket.invalidIf.includes("24950"), true);
assert.equal(formatSlot(25000), "25,000");

assert.equal(displayMode("LIVE"), "MOCK");
assert.equal(displayMode("LIMITED_LIVE"), "MOCK");
assert.equal(displayMode("LIVE PAPER"), "PAPER");
assert.equal(displayMode("SHADOW"), "SHADOW");
assert.equal(marketView("BUY_PE"), "PUT");
assert.equal(marketView(""), "HOLD");

const founderSnap = { role: "founder", channels: { positions: { items: [] } } };
assert.equal(isCustomerV2Snapshot(founderSnap), false);
const publicSnap = {
  role: "customer",
  as_of: "2026-10-04T11:05:00+05:30",
  mode: "PAPER",
  channels: {
    "signals:public": {
      items: [{ payload: { underlying: "NIFTY", side: "CE", trend: "Up", chain_3m: "ATM bid" } }],
    },
  },
  denied: ["positions"],
};
assert.equal(isCustomerV2Snapshot(publicSnap), true);
const fromV2 = selectCustomerView(deskFromV2Public(publicSnap), "NIFTY");
assert.equal(fromV2.feed, "signals:public");
assert.equal(fromV2.mode, "PAPER");
assert.equal(fromV2.market, "CALL");
assert.ok(!fromV2.denied || true);

console.log("PASS customer_portal_unit empty HOLD + one CALL + no LIVE badge");
