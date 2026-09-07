# How signals work (plain English)

**PAPER only. No live orders. Not a win-rate claim.**

## The one path

1. **Bars** — Index 1-minute closes for NIFTY, BANKNIFTY, or SENSEX.
2. **Pattern** — CF **plugin registry** (`cf_paper_registry.detect_cf_signal`) tries detectors in order:
   - **Okala India** (`detect_okala_signal`) — LEVEL / FORK / H_CROSS / REPAIR
   - **Structure CF overnight** (`detect_structure_signal`) — any MIX-CF-* cell with robust WR > 50% (n≥20) from the overnight grid
3. **Side** — Pattern says **buy CE** or **buy PE** (call or put).
4. **Premium ticket** — Entry / Stop / Target come from the **option premium** (LTP), not from the index number pretending to be a premium.
5. **Paper card / API** — That lean shows on the paper signal snapshot. Orders are always refused.

## Premium levels (starter)

When we have an ATM option LTP:

| Field | Rule | Units |
|-------|------|--------|
| Entry | Option LTP | premium ₹ |
| Target | Entry × 1.25 | premium ₹ |
| Stop | Entry × 0.75 | premium ₹ |
| Spot | Index last | **underlying**, separate |

Stop ×0.75 is a **PAPER starter hypothesis** until a real premium swing / greek map exists. Re-enable stricter DI later if you want.

If LTP is missing: we still show CE/PE **intent**, and leave Entry/Stop/Target empty with an honest data gap.

## Who may fire

- **Okala NIFTY** — cells with robust research WR > 50% (n≥20) from `OKALA_IN_BACKTEST_2026-09-07`.
- **Structure CF** — overnight accepted cells in `data/recon/CF_OVERNIGHT_*_2026-09-07.json` (167 cells across Fabio/Marco/Mayne/Marci/Tori/Andrea/Omor/Umar/Forest/Carmine/Jadecap/Brando; TG/Kane had **0** accepts this pass).
- **BANKNIFTY / SENSEX** — same pattern rules under `FOUNDER_STARTER_EXTEND` when NIFTY cells qualify (caution label; no live promote).

Rollup: [`data/recon/CF_OVERNIGHT_BACKTEST_ROLLUP_2026-09-07.md`](../../../data/recon/CF_OVERNIGHT_BACKTEST_ROLLUP_2026-09-07.md).

## News does not kill the ticket (for now)

`NEWS_VETO_ENABLED` defaults to **false**. BIG_NEWS / NEWS_DAY / fixture macro may still be **noted**, but they do **not** force HOLD on the customer paper ticket.

To turn news holds back on later:

```bash
export NEWS_VETO_ENABLED=true
```

Agents can still write notes. They must not block CE/PE when a registered CF pattern (or a simple chain/tech lean) fires.

## Dry-run

```bash
python -m backtest_engine okala-signal --underlying NIFTY --option-ltp 100
python -m backtest_engine cf-signal --underlying NIFTY --option-ltp 100
python -m backtest_engine cf-overnight   # re-run overnight grid (cache OHLC)
```

## Honesty

- PAPER notify only · **NO_PROMOTE** live  
- Gate `RESEARCH_READY_FOR_PROGRAMMING` is **not** set  
- Catalog `win_rate` stays null  
- Optimize later
