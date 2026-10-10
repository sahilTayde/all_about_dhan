#!/usr/bin/env node
// C5-08: journey phases, last-known path, no invented live prices, reduced motion.
import assert from "node:assert/strict";
import {
  buildJourney,
  journeyPhase,
  journeySteps,
  lastKnownPath,
  motionAllowed,
  sparklineGeometry,
} from "../src/lib/customerJourney.js";
import {
  closedTicketFixture,
  emptyDeskFixture,
  oneTicketFixture,
  selectCustomerView,
} from "../src/lib/customerPortal.js";

const empty = selectCustomerView(emptyDeskFixture(), "NIFTY");
assert.equal(journeyPhase(empty.status, { waiting: empty.waiting, hasTicket: Boolean(empty.ticket) }), "SIGNAL");
const emptyJourney = buildJourney(empty, null);
assert.equal(emptyJourney.phase, "SIGNAL");
assert.equal(emptyJourney.steps[0].state, "active");
assert.equal(emptyJourney.steps[1].state, "wait");
assert.equal(emptyJourney.path.points.length, 0);
assert.equal(emptyJourney.path.source, "DATA_INSUFFICIENT");
assert.equal(emptyJourney.path.invented, false);
assert.equal(emptyJourney.spark.d, "");

const ticket = selectCustomerView(oneTicketFixture(), "NIFTY");
assert.equal(ticket.status, "IN-PROGRESS");
assert.equal(journeyPhase(ticket.status, { waiting: ticket.waiting, hasTicket: Boolean(ticket.ticket) }), "HOLD");
const openJourney = buildJourney(ticket, null);
assert.equal(openJourney.phase, "HOLD");
assert.deepEqual(
  openJourney.steps.map((s) => s.state),
  ["done", "done", "active", "wait"],
);
assert.equal(openJourney.path.source, "last-known journal");
assert.equal(openJourney.path.invented, false);
assert.equal(openJourney.path.points.length, 3);
assert.equal(openJourney.path.points[0].v, 120);
assert.equal(openJourney.path.points[2].v, 124);
assert.ok(openJourney.spark.d.startsWith("M"));
assert.ok(openJourney.chips.some((c) => c.label === "CALL"));
assert.ok(openJourney.chips.some((c) => c.label === "IN-PROGRESS"));

const closed = selectCustomerView(closedTicketFixture(), "BANKNIFTY");
assert.equal(closed.status, "ACHIEVED");
const closedJourney = buildJourney(closed, { as_of: "2026-10-04T13:42:00+05:30", tape_last: { as_of_ist: "2026-10-04T13:42:00+05:30", source: "demo.jsonl" } });
assert.equal(closedJourney.phase, "EXIT");
assert.equal(closedJourney.steps[3].state, "active");
assert.equal(closedJourney.path.source, "last-known journal");
assert.equal(closedJourney.path.points.at(-1).v, 200);
assert.ok(closedJourney.chips.some((c) => String(c.label).includes("tape")));

assert.equal(journeyPhase("WATCH", { waiting: false, hasTicket: false }), "SIGNAL");
assert.equal(journeyPhase("CONFIRMED", { waiting: false, hasTicket: true }), "ENTRY");
assert.equal(journeyPhase("DEALER_KILLED", { waiting: true, hasTicket: false }), "EXIT");
assert.deepEqual(journeySteps("ENTRY").map((s) => s.state), ["done", "active", "wait", "wait"]);

const noInvent = lastKnownPath({ ticket: { entry: 120 } });
assert.equal(noInvent.points.length, 1);
assert.equal(noInvent.source, "last-known ticket");
assert.equal(noInvent.invented, false);

const geo = sparklineGeometry([{ t: 0, v: 10 }, { t: 1, v: 20 }]);
assert.ok(geo.d.includes("M"));
assert.equal(geo.dots.length, 2);

assert.equal(motionAllowed(() => ({ matches: true })), false);
assert.equal(motionAllowed(() => ({ matches: false })), true);

console.log("PASS customer_journey_unit phases + last-known path + reduced motion");
