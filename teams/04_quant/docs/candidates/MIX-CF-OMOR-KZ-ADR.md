# MIX-CF-OMOR-KZ-ADR — Chart Fanatics Omor/NBB killzones + ADR day profile

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT`  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `IB-fyWI5j8w` · guest **Omor / NBB Trader**  
**Bind:** [`../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)  
**Not** clubbed into TG London / Jade session-liq / prior CF. No STRAT-015+.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
```

---

## Teacher recipe (SOURCE_FACT summary)

1. London / NY / London-close killzones (ASR clocks inconsistent).  
2. Profile how the daily candle builds across sessions.  
3. ADR(5): if average range already spent, skip late chase.  
4. London–NY OTE named as session bridge.

---

## Computable proxy

**DATA_INSUFFICIENT** for NSE — do not invent IST killzone boxes from US/UK times. ADR alone without session map is not the teacher recipe.

---

## YAML stub

```yaml
mix_id: MIX-CF-OMOR-KZ-ADR
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: IB-fyWI5j8w, channel: chart-fanatics, guest: Omor / NBB Trader}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: FX_ICT
india_transfer: DATA_INSUFFICIENT
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-MMM-FRAME, MIX-CF-TG-TRIDENT, MIX-CF-JADECAP-SESSION-LIQ]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Remain DI until an explicit IST session map is specified and scored; do not delete the teacher row.
