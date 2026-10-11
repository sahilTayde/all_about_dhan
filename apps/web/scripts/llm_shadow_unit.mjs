import assert from "node:assert/strict";
import { moneyLine, shadowCompareView } from "../src/lib/llmShadowCompare.js";

const empty = shadowCompareView(null);
assert.equal(empty.ok, false);
assert.equal(empty.trade, false);
assert.equal(empty.promote, false);

const view = shadowCompareView({
  ok: true,
  r3_net: 1200,
  random_mean: 400,
  r3_minus_random: 800,
  n_days: 2,
  days: [{ day: "2026-10-09" }, { day: "2026-10-10" }],
});
assert.equal(view.ok, true);
assert.equal(view.r3Net, 1200);
assert.equal(view.randomMean, 400);
assert.equal(view.delta, 800);
assert.equal(moneyLine(800), "+800");
assert.ok(!/R3_PREREG|SKIP|TAKE/.test(JSON.stringify(view)));

console.log("llm_shadow_unit: ok");
