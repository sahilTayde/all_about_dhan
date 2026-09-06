# `cas_calls[]` JSON

One file per session: `YYYY-MM-DD.json`.

Nightly (`desk_intel.nightly`) copies `calls` into `data/recon/YYYY-MM-DD.json` as **`cas_calls`**.  
Missing file → empty list. **Never** writes `04_quant` params.

```json
{
  "schema_version": 1,
  "day": "YYYY-MM-DD",
  "layer": "UNVALIDATED",
  "retune": "BACKTEST_REQUIRED",
  "calls": [
    {
      "underlying": "NIFTY",
      "mechanism": "CLOSING_AUCTION_SESSION",
      "bias": "SIDEWAYS",
      "confidence": 0.2,
      "window": "research_only",
      "as_of_ist": "2026-09-01T16:05:00+05:30",
      "realized_bias": null,
      "close_vs_ref_pts": null,
      "notes": "DATA_INSUFFICIENT — no live tape.",
      "retune": "BACKTEST_REQUIRED"
    }
  ]
}
```

`bias`: `BOUNCE` | `SIDEWAYS` | `FALL`.  
`mechanism`: `CLOSING_AUCTION_SESSION` | `PRE_OPEN` | `PCA` | `POST_CLOSE` | `CASH_BASIS`.
