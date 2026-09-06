# TRANSCRIPT_STRATEGY_BIND — Phase-1 STRAT rules vs spoken English

**Team:** 01_research  
**Date:** 2026-09-03  
**Layer:** `SOURCE_FACT` only. Not `VALIDATION`. Not `HYPOTHESIS`.  
**Status:** `EXTRACTED` / `DRAFT`. Gate: **not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Corpus:** `data/transcripts/normalized_en/<video_id>.md` (`tlang=en`, `youtube_translate`). **English file wins** if a STRAT / ENGINE_MIX / Hindi packet disagrees.  
**Do not treat as advice or edge.** No win rates. No apps. Education ≠ advice.

Prior mix pass copied timestamps from STRAT files. This file **re-read** the English transcripts and binds each Phase-1 rule to spoken English. Paraphrases are of YouTube English, not Hindi ASR. Quotes are not invented. Numbers stay `[UNCERTAIN_TRANSCRIPT]` when ASR/translate is messy.

Coalition packets used as *index of claims*, not as authority: [`OPTIONS_INDEX_PACKET.md`](OPTIONS_INDEX_PACKET.md), [`TA_STRUCTURE_PACKET.md`](TA_STRUCTURE_PACKET.md). 04 mix read-only: [`ENGINE_MIX.md`](../../../04_quant/docs/ENGINE_MIX.md). Candidates: `STRAT-001` … `STRAT-014`.

`bind` = **CONFIRMED** | **CONFLICT** | **WEAK** (ASR messy) | **NOT_IN_EN** | **PROJECT_MIX** (clubbing not spoken as one recipe).

---

## Guests (SOURCE_FACT affiliation only)

Spoken affiliation is **not** a validated edge. SEBI-registered / “research analyst” on a Dhan video ≠ approved strategy.

| video_id | spoken name | spoken affiliation (EN) | ts | what it is not |
|----------|-------------|-------------------------|----|----------------|
| `2RnBT9DDDNI` | Dr. Gokul Chhabra / Gokul Jhabra (EN uses both spellings) | Host: “SEBI registered Research Analyst” / “Also SEBI registered. Practicing” | 01:57–02:06, 02:44–02:50 | Not a 02/03 validation. Not a reason to code STRAT-003. |
| `HAUSZx-hYdY` | Himanshu Arora | Host: “Star Trader of this Dhan Platform” | 00:54–01:02 | **Not** spoken as SEBI RA in this EN file. “SEBI regulation has come” (~16:27) is expiry-calendar talk, not his registration. |
| `pvmvkiS1cx4` | Mukul Choudhary | Self-intro host | 00:02–00:04 | No RA claim in the open. |

---

## Bind table (STRAT-001 … 014)

One row per **rule 04/STRAT claims**. Same `strat_id` may have several rows.

| strat_id | rule 04/STRAT claims | EN video_id | EN timestamp | paraphrase of English (not Hindi ASR) | bind | notes |
|----------|----------------------|-------------|--------------|----------------------------------------|------|-------|
| STRAT-001 | Parent **hourly** + child **5 or 10 minute** | `HAUSZx-hYdY` | 42:30–42:31 | “Check the market on two time frames… One is on the hourly chart and one is On five or 10 minute charts.” | CONFIRMED | Dual-TF start of recipe is 41:32; the TF pair is spoken at 42:30. |
| STRAT-001 | MACD (12/26 then ×3 or ×4), histogram only; MA **10, 30, 100**; buy **above that candle’s high** | `HAUSZx-hYdY` | 45:07–47:54, 46:45–46:54, 01:00:07–01:00:19 | Uses MACD; “Increases the MACD parameters… four times… three times or four times”; params “12 and 26 periods”; drop lines, keep histogram (green bullish / red bearish). Three MAs: “10 periods, 30 Period, 100 periods.” Child: “MACD is bullish on the 5-minute chart and Again, 10, 30, and 100… I would buy above the high of that candle.” | CONFIRMED | ×3 vs ×4 is WEAK on the multiplier (see next row). Signal length **9** is not clearly spoken. |
| STRAT-001 | MACD all-params **×3 or ×4** as a frozen spec | `HAUSZx-hYdY` | 45:37–46:04 | Speaks **both** “four times” and “three times or four times”; “I would do both things four times.” | WEAK | Do not freeze 48/104/36. Search grid stays 04’s job; 01 cannot pick a winner from EN. |
| STRAT-001 | Recap MA stack **10 > 30 > 100** vs **10 above 30 and 300** | `HAUSZx-hYdY` | 47:48–47:54 vs 59:24–59:28 vs 01:00:12–01:00:14 | First: “If 10 period moving average is above 30 and 30 is above 100.” Recap: “10 periods The moving averages are above 30 and above **300**.” Child recap returns to “10, 30, and **100**.” | CONFLICT | Same speaker, same video. 100 vs 300 is `[UNCERTAIN_TRANSCRIPT]`. Search, do not silently correct. |
| STRAT-001 | Trail: MA **9** vs **10** vs 30 | `HAUSZx-hYdY` | 56:24–56:48 | Hold “until my 10th period Hold until the moving average is above 30.” Then: “See **Nine** here throughout this period As soon as the period moving average is below 30.” | WEAK | 9 vs 10 in one breath. |
| STRAT-001 | Alt TF **2h parent / 15m child** (STRAT yaml comment) | `HAUSZx-hYdY` | 01:02:51–01:02:54 | “You can increase the time frame… you can use it too hourly… You can also do it on charts and **15 minute** charts.” Parent/child “must have a big gap.” | NOT_IN_EN | **15m child alt is spoken. 2h parent is not spoken in HAUS.** 2h is `gA5FtEnSABM` (different recipe). Rewrite the yaml comment. |
| STRAT-001 | yaml `market: [NIFTY, BANKNIFTY, SENSEX]` as the taught universe | `HAUSZx-hYdY` | 43:14–44:19, 59:49–59:52 | Universe: “Nifty's top 100 stocks”; “I am following this strategy in Nifty 100”; “I limit up to Nifty 100”; demo Bajaj Auto. Later: usable “For Cash and You Can Use It for Options” (01:03:04–01:03:09). NIFTY named as an underlying-move example (~42:52), not as the only chart. | PROJECT_MIX | Options **application** is spoken. **Index-options-only book** is a transfer. Tag PROJECT if 001 is the NIFTY/BN/SENSEX primary. |
| STRAT-002 | Buy **slightly OTM** (1–2 strikes); ATM “pumped”; adverse ~**40 delta**; target **20–30%** premium | `HAUSZx-hYdY` | 57:40–58:46, 58:18–58:24, 01:01:00–01:01:08 | “I purchase an out of the money option… slightly out of the money… one or two strikeouts.” ATM “Most Overvalued.” Against: “I will be at **40 delta**.” Target: “around **20 to 30%** when choosing this option The value increases, I book a profit.” | CONFIRMED | This is **HAUS**, not 2Rn. Slightly OTM is **002**, not 003. |
| STRAT-002 | Beginner rupee stop **1500–1700** vs **2500** target | `HAUSZx-hYdY` | 01:05:49–01:05:52 | “If it is worth ₹2500 then you can spend maximum ₹1500 With a stop loss around 1700.” | WEAK | Rupee toy; `[UNCERTAIN_TRANSCRIPT]`. |
| STRAT-002 | Overlay on **003** as well as 001 (`STRAT-002.md`: “Overlay on 001 (or 003)”) | `2RnBT9DDDNI` | 38:06–38:13 | 2Rn: “I am always in the money and maximise the Inside Money… **OTM at all This is not recommended.**” | CONFLICT | 002 and 003 are **different videos**. Do not put slightly-OTM on a 003 ticket. ENGINE_MIX already split 002 vs 005; STRAT-002.md “or 003” must be rewritten. |
| STRAT-003 | **3-minute index futures**; not cash; not stock options this class | `2RnBT9DDDNI` | 20:57–21:16, 21:59–22:16, 22:24–22:28 | After a messy “1 minute. 3 minutes” line, “**3 minutes K Time Frame Is a Preferable Time** Because we are doing intraday”; “we are not seeing spots. We Looking at the **futures**.” “this is the strategy… **only look at the index** Use it.” Bank Nifty → “Trade in Bank Nifty **futures**.” | CONFIRMED | 20:59 “1 minute / 3 minutes” is ASR noise; he settles on **3m**. 3m is still not an HQ `{1,5,15,25,60}` interval — that gap is 02/03, not a transcript deny. |
| STRAT-003 | VWAP default + **VWMA length 20** + Supertrend **“103”** | `2RnBT9DDDNI` | 21:40–21:57 | VWAP (“VIP”): “No settings have been changed. just a little color.” VWMA: “I have taken its length. **20**.” Supertrend: “By default… I will keep the setting of **103** the same.” | WEAK | Structure CONFIRMED. Digits **10, 3** are inferred from “103” + `H_6kee` “10 3”. Keep `[UNCERTAIN_TRANSCRIPT]` on 2Rn digits. Do not freeze from this line alone. |
| STRAT-003 | **All three** for put (price below VWAP and VWMA and ST) and call (price above all three) | `2RnBT9DDDNI` | 25:13–26:07 | Put: price “below” VWAP/VWMA (“VVPWM”) “**will be below the super trend**… my **put buy** trade gets activated.” Call: “If my price Greater than weave is super trendy in BWM so… my **call entry** here It will be activated.” | CONFIRMED | EN is messy on names (VVP/BWM) but the all-three rule is spoken. Same-bar AND, not “any one.” |
| STRAT-003 | Exit: **3m close** the other side of Supertrend; **no** cost-to-cost trail | `2RnBT9DDDNI` | 27:07–27:39 | “if he **closes above the super trend**… I will definitely lose my position. Will have to cut it.” “**Do not use a trailing stop loss.** cost to You will recover the cost. Get out at cost. then again Make an entry.” | CONFIRMED | Matches STRAT-003 “Do not cost-to-cost trail on ST.” |
| STRAT-003 | Supertrend vs VWAP **disagree** → no new entry (sideways) | `2RnBT9DDDNI` | 34:54–36:01 | “this is super trendy and it It is VVP… According to VVP, the price is bullish. Price bearish according to super trend… whenever the price crosses any two or three indicators That's a **no no zone** That's a **no trading zone**… **no new entry** is activated here.” | CONFIRMED | Spoken “70% non-trading / 30% trading” (~24:26–24:30) is anecdote, not a metric. |
| STRAT-003 | yaml also copies **09:15–09:45 skip** and **flatten 15:15** | `2RnBT9DDDNI` | 23:48–24:06 | Same speaker, same recipe: “candles from **9:15 to 9:45 Ignore it completely**… starting after 9:45 and all their positions from **3:15 First it has to be cut.** … **Not for BTST.** Overnight… no.” | CONFIRMED | Same video as STRAT-009. **Not** a club with HAUS 007. |
| STRAT-004 | Dhan **Super Scalper** on **option premium**; Fast EMA + Slow EMA; **1-minute**; long when price above both and fast > slow; stop below slow EMA | `2RnBT9DDDNI` | 46:59–48:21, 55:02–55:15 | “This is called a **super scalper**… **Fast EMA, Slow EMA**, Sell Label… **1 minute time frame**” (he first says 3m then “ok 1 minute This is to be placed on a **1 minute** time frame”). “When the price is above both… If the **fast EMA is above the slow EMA**, I want to find scalping **calls**.” Stop: “**Below the slow EMA** and my target is **1:2**.” | CONFIRMED | Structure + 1m premium chart CONFIRMED. 1:2 is WEAK (`[UNCERTAIN_TRANSCRIPT]`). He also wants 3m all-three true at 55:07–55:08 — that AND is **this video’s** confirm, still not HAUS MACD. |
| STRAT-004 | Numeric **fast/slow EMA lengths** | `2RnBT9DDDNI` | 47:16–55:15 (full Super Scalper block) | Fast EMA and Slow EMA are named. **No period lengths spoken** (no 9/21, no 8/21, no 5/13). | NOT_IN_EN | Stay `UNKNOWN`. Do not invent 9/21. 004 stays parked until chart-export VERIFY. |
| STRAT-005 | Strike from **spot** at signal; **ITM / max ATM**; **OTM not recommended**; “two in the money” | `2RnBT9DDDNI` | 38:06–39:20 | “I am always **in the money** and maximise the Inside Money… **OTM at all This is not recommended.**” Strike from **spot** at signal time, not the futures chart. “I have **two in the money**… 2450 that is almost **at the money**.” | CONFIRMED | Different video from HAUS slightly-OTM (002). |
| STRAT-005 | Call delta **0.60–0.75** (yaml `[0.60, 0.75]`; spoken 0.63–0.74) | `2RnBT9DDDNI` | 01:02:42–01:03:50 | Host asks for a delta range. Guest: RSI “**50 to 75**” in a bull market → “just little The number will change from **60 to 75**.” Then “when I delta If I am looking at **60** then 60 means **66**… from **6 to 75**” (ASR). Safer: “**71**… **74**… **Butt74** Then He Goes Deep… There is not that much logic.” “So from **063 to 74**… these four strikes.” Puts: “converted into **minus**.” | WEAK | Direction CONFIRMED (high delta, not OTM). Exact 0.60–0.75 band is analogy + messy digits. Avoid >~0.74 is spoken as “deep… not that much logic.” |
| STRAT-005 | Host “avoid **50-multiples**” vs guest | `2RnBT9DDDNI` | 01:03:51–01:04:05 | Host: “**50 Generally avoid** options with multiples I do. Do you do it too…” Guest: “**No sir, we will trade.**” Host reason: liquidity thinner vs multiples of 100. | CONFLICT | Host vs guest in the same video. STRAT `avoid_50_multiples: TEST_ON_OFF` is the honest bind. |
| STRAT-006 | **2-minute** chart; **EMA 10 and 20 only**; NIFTY / BANKNIFTY / SENSEX; **ITM 100–200 points** (not ATM, not OTM, not deep ITM) | `pvmvkiS1cx4` | 00:46–02:33, 01:03–01:21 | “Nifty 50, Sussex, Bank Nifty”; analysis on **spot**, trade on **options**. “**in the money** options by default. There will be no at the money… no out of the money… I don't even want to go deep… **100 200 points**… Bank Nifty then also it is 100-200… Nifty also.” TF: “we will use **2 minutes**.” Indicators: “two **10 and 20 EMAs**… not… simple… not… double exponential.” | CONFIRMED | Chart default “**9 and 26**. We don't want 10 or 20” then “**We use 10**… **and 20**” (04:00–04:06) is UI noise; intended pair is 10/20. |
| STRAT-006 | Delta **0.55–0.60** | `pvmvkiS1cx4` | 01:27–01:32, 17:15–17:18 | “choose options within **555 to 6 delta**.” Later: “in the money option whose delta is from **0.55 to six**.” | WEAK | `[UNCERTAIN_TRANSCRIPT]`. Do not freeze 0.55–0.60 as if clearly spoken. |
| STRAT-006 | Beginners should **not** scalp by **buying** options | `pvmvkiS1cx4` | 13:06–13:16 | “if **India VIX is above 15-16** then **beginners should not do scalping in option buying.** You can do scalping by **selling** options but **not by buying**… or… hedging.” | WEAK | STRAT-006 dropped the **VIX > 15–16** condition and made it a blanket beginner ban. Spoken rule is **conditional**. Keep both: ITM-buy recipe **and** the VIX/beginner warning. |
| STRAT-007 | New entries **after 10:00**, mostly **not after 14:30** (“2:30”), **not after 15:00**; best ~11:00–13:00 | `HAUSZx-hYdY` | 55:18–55:52, 01:00:22–01:00:35 | “I trade after **10:00 AM**… mostly after **2:30** Does not initiate. after **3:00 p.m.** I definitely don't… From **10 o'clock to 2:30** I am mostly I initiate… Best… around **11:00**… **12:00**… **1:00 pm**.” Recap: setup “forming after [10:00] and … before **2:30**… After 2:30 I'll probably I'll take it sometimes… after **3:00 pm** it is not certain.” | CONFIRMED | Himanshu / HAUS only. 14:45 vs 15:00 is messy at 55:30–55:33. |
| STRAT-007 | **AND** with STRAT-009 so Phase-1 starts 10:00 and flattens 15:15 | `HAUSZx-hYdY` + `2RnBT9DDDNI` | (two speakers) | No video teaches “skip until 10:00 **and** flatten 15:15” as one clock. HAUS: 10:00–14:30. Gokul: ignore 09:15–09:45, flatten 15:15, **start 09:45**. | PROJECT_MIX | Conservative intersection is 04’s. See § ENGINE_MIX clubs. |
| STRAT-008 | If NIFTY buy and BANKNIFTY sell (mixed): **avoid that day** or trade only **dominant** index — **not both** | `2RnBT9DDDNI` | 01:08:37–01:09:14 | “Nifty… **buy** signals And is Bank Nifty offering a **sale**? Yes sir, it happens… **Mixed signals**… **Avoid That Day** and Yet If You Are Interested Go for Your **Dominant Index**… **Don't trade both.**” If one buy / one sell: “**avoid that day**.” | CONFIRMED | SENSEX as third named index is later priority talk (01:04:44–01:04:47), not a full three-way formula. Alignment on each market’s **future** is 03, not spoken as “fake combined volume.” |
| STRAT-008 | If all aligned: **1 lot each** vs 3 lots in one | `2RnBT9DDDNI` | 01:10:25–01:10:45 | “Should I say goodbye to all three or just one? Take **three lots**.” “Depends on your capital… recommendation… **diversify over two**. A never-flop It's done, the other one gives the return.” | WEAK | Spoken “diversify over two,” not a frozen 1-lot-each test. Size test remains 04. |
| STRAT-009 | Ignore **09:15–09:45**; flatten **before 15:15**; intraday; no overnight | `2RnBT9DDDNI` | 23:48–24:06 | “candles from **9:15 to 9:45 Ignore it completely**… all our strategies are for **9:45 Will start later**… all their positions from **3:15 First it has to be cut.** This strategy is for **intraday**. **Not for BTST.** Overnight someone There is no question of carry forward.” | CONFIRMED | Gokul / 2Rn only. Complements 007; **do not merge speakers.** |
| STRAT-010 | Take 003/001 **only if** futures footprint **volume-delta** agrees; optional POC; imbalance ≥**3×** | `YUXJv_xBStw`, `DzT_681GThA` | YUX 02:48–04:54, 05:53–06:08; DzT 02:23–02:48, 08:48–09:28, 19:29+ | YUX: OF on “any **stock or index**”; demo **futures**; **delta**, **POC**, **imbalance**; RSI/MACD/MAs called **lagging**. DzT: delta = buy vol − sell vol (**not** Greek); POC = highest buy+sell in the candle; imbalance default buy vol ≥ **three times** previous price’s sell vol; four price/delta rules; demo **Reliance**; “stock **or index**.” DzT also: you cannot trade on OF **or** TA **alone**. | PROJECT_MIX | Tool + definitions CONFIRMED. **No CE/PE / strike / 003-filter recipe.** Using OF to gate 003/001 is 04’s overlay. HQ OF history: `DATA_INSUFFICIENT` (not a transcript fact). |
| STRAT-011 | Supertrend default **10, 3** | `H_6keeRUCDM` | 01:40–01:51, 09:31–09:36 | Quiz: default Supertrend “10 {ock} 1, B 10 {comma} 2 or C 10 {comma} 3.” Answer: “default parameters of super trend are **10 3**.” | CONFIRMED | Spoken on **stock / gold** charts. Params CONFIRMED; index-option use is the next row. |
| STRAT-011 | Parent RSI oversold + **green candle**; child Supertrend close-through; apply to **index options** | `H_6keeRUCDM` | 01:24–01:27, 06:00–06:36, 09:38–09:44, 12:14–12:34 | “if you trade in **equity market** or you trade in **gold or silver**.” Parent: “**RSI is oversold**… a **green candle** formed in a falling market.” Child: “prices go **above Super Trend**… buy **above this high**.” “I use this strategy on **stocks** on weekly plus daily… **commodity**… **2 hourly plus 45 minutes**… stocks you can also do it **daily plus two hourly**.” | PROJECT_MIX | **No NIFTY / BANKNIFTY / SENSEX options** in this EN file. Index-option 011 is a transfer. RSI **period** not named (Wilder 14 is VALIDATION default, not Dhan-spoken). |
| STRAT-011 | gA5 RSI **divergence** on NIFTY → **buy** CE/PE (intraday) | `gA5FtEnSABM` | 03:03–03:42, 04:10–04:18, 08:06–08:09, 13:35–13:42 | NIFTY 2h (“Too Early”) chart. **Will not become an option buyer** on that swing horizon (theta). “If I were to do this **intraday**, I would be **buying** options. However, for now, I'm teaching you how to **sell**.” RSI divergence → “slightly **bullish**.” **Executes a bull put spread** (sell nearer put, buy further OTM put). Intraday or 1–2 days → “option **buying** is preferred”; few days → “prefer option **selling**.” | CONFLICT | View can be bullish. **This video’s fill is a credit spread (013).** Mapping the same view to Phase-1 **buy** CE/PE is PROJECT, and it **conflicts** with the executed example. |
| STRAT-012 | Patterns **not** standalone; **hammer** wick **2–3×** body; optional RSI < 30 | `njqeZc_tYy8` | 00:51–00:54, 07:24–08:36, 09:03–09:05, 13:50–14:02 | “five powerful candlestick patterns.” “Candlestick patterns are **not to be traded independently**” (need trend, 20 SMA, support/resistance, confirmation candle). First pattern **hammer**: “shadow is **two to three times** longer than the body.” Hammer confluence: RSI “already oversold… value is **below 30**.” | CONFIRMED | Stock examples. Hammer extraction is complete enough to bind. |
| STRAT-012 | Four other patterns still `WAITING_FOR_EDIT` / not in EN | `njqeZc_tYy8` | 17:26+, 28:49+, 32:46+, 36:02+ | EN **names** the rest of the five: **bullish engulfing**, **morning star**, **dark cloud cover**, **inside bar**. Video end: “Today we decode the top five.” | WEAK | **Not** `NOT_IN_EN`. STRAT-012’s “four patterns WAITING” is **stale vs EN**. Full rule tables (entry/stop) were not re-extracted this pass — WAITING on **detail**, not on **existence**. Rewrite the candidate line. |
| STRAT-012 | Allow 001/003 entry only if last 5m/15m pattern agrees (index options) | `njqeZc_tYy8` | (stock charts throughout) | No spoken “use hammer to filter Gokul 3m VWAP+ST” or “HAUS MACD.” | PROJECT_MIX | Overlay on 001/003 is 04. |
| STRAT-013 | **Bull put credit** (weekly); **WAITING** sell — not Phase-1 buy | `gA5FtEnSABM` | 07:20–08:09, 10:08–10:50 | Budget week → does not want to stay in selling into the event; still picks **bull put spread**: sell a put, buy a slightly further OTM put. Skip same-day expiry in the demo. | CONFIRMED | **SELL.** Do not convert to a CE ticket. Stay WAITING on the buy book. |
| STRAT-014 | Hedged **1-3-2 call ratio**; NIFTY; **Monday 09:45**; next **Tuesday** expiry; 1% stop/target; **WAITING** sell | `6el9Jqnrdz8` | 41:29–44:16 | “the script we are writing is **Nifty**.” Hold ~4–5 days. NIFTY expiry spoken **Tuesday** (dated — VERIFY). Entry **Monday 9:45**, expiry next Tuesday; Mon–Fri, **no weekend carry**. Spot 26000 toy: buy **1** 26200 call, sell **3** 26400, buy **2** 26600 → “I bought one, then sold three, then bought two.” Target and stop **1%**. Basket. Avoid 50-strikes mentioned (~45:28). | CONFIRMED | **SELL / ratio.** Not Phase-1 CE/PE buy UI. Tuesday NIFTY expiry is recording-dated. |

---

## What ENGINE_MIX clubs that NO video taught as one system

These rows are **PROJECT_MIX**. Do not relabel as `DHAN-DERIVED`. Speakers did not teach this as one recipe.

| mix claim (04) | what EN actually taught | videos | bind | rewrite |
|----------------|-------------------------|--------|------|---------|
| Default BULL/BEAR ticket = **003 primary AND 007 AND 009** clocks (no new 09:15–**10:00**, no new after **14:30**, flatten **15:15**) | **Gokul** (`2RnBT9`): ignore 09:15–09:45, **start 09:45**, flatten 15:15. **Himanshu** (`HAUSZx`): new entries after **10:00**, mostly not after **14:30**. Two clocks. Intersection is stricter than either speaker. | `2RnBT9DDDNI` 23:48–24:03; `HAUSZx-hYdY` 55:18–55:42 | PROJECT_MIX | Keep 007 and 009 as **separate filters**. If Phase-1 ANDs them, origin tag **PROJECT-DERIVED**. Do not cite one timestamp as if both men agreed. |
| **5m MACD / Supertrend = confirm-or-kill**, not entry ([`SIGNAL_STAGING.md`](../../../04_quant/docs/SIGNAL_STAGING.md)) | **HAUS** uses child 5m/10m **MACD histogram as the entry filter** (“buy above the high of that candle”). **2Rn** uses **3m** futures VWAP+VWMA+ST as the entry; Super Scalper is a **1m premium** add-on, not 5m MACD. Nobody says “5m MACD only promotes or kills a staged lean.” | `HAUSZx-hYdY` 01:00:07–01:00:19; `2RnBT9DDDNI` 25:13–26:07 | PROJECT_MIX | Desk staging vs HAUS-MACD-entry must stay **two test IDs**. Averaging them is soup. ENGINE_MIX §4 already flags this — bind agrees. |
| **003 + 007 + 009 + staging 5m ST/MACD + 005** as “the Dhan book” | 003+005+008+009 are **one speaker** (Gokul). 007 and 001/002 are **Himanshu**. Staging confirm is **desk spec**. 005 strike is Gokul, not Himanshu’s slightly OTM. | see rows above | PROJECT_MIX | Named mix is allowed as HYPOTHESIS if tagged PROJECT. It is **not** a transcript theorem. |
| Attach **002 and 005** (or 002 on a 003 ticket) | HAUS: slightly OTM. Gokul: OTM **not recommended**. | `HAUSZx-hYdY` 57:40+; `2RnBT9DDDNI` 38:11 | CONFLICT | STRAT-002.md “or 003” must die. Strike follows the **primary’s video**. |
| **011** as index-option reversal primary | `H_6kee` = stocks + gold/silver. `gA5` = NIFTY view then **bull put sell**. | `H_6keeRUCDM`; `gA5FtEnSABM` | PROJECT_MIX | Keep origin PROJECT-DERIVED. Do not say Dhan taught NIFTY option **buys** this way. |
| **010** OF agrees-with-003 gate | YUX/DzT = product + four OF rules. DzT: do not trade OF **or** TA alone. No 003 gate. | `YUXJv_xBStw`; `DzT_681GThA` | PROJECT_MIX | Overlay parked is honest. |

**Same-video clubs (not PROJECT_MIX):** Gokul’s 3m VWAP+VWMA+ST **plus** 09:45 open skip **plus** 15:15 flatten **plus** ITM/ATM strike **plus** mixed-index avoid **plus** Super Scalper confirm — that **is** one class (`2RnBT9DDDNI`). 04 splitting those into 003/004/005/008/009 is bookkeeping, not clubbing two teachers.

---

## STRAT rules that must be rewritten (01 → 04)

01 does not edit `teams/04_quant/**`. These are the mismatches EN forces.

1. **STRAT-001** yaml comment `2h/15m alt spoken` — **2h is NOT_IN_EN** on HAUS. Keep 15m child alt. Tag index-only universe **PROJECT** (spoken universe = NIFTY 100 stocks + options).
2. **STRAT-002.md** “Overlay on 001 **(or 003)**” — **CONFLICT**. 003’s video bans OTM. 002 only on 001-alt.
3. **STRAT-003** Supertrend **10, 3** — keep as inference from “103” + `H_6kee`; do not present 2Rn as having said “ten comma three.”
4. **STRAT-004** — lengths stay **NOT_IN_EN** / `UNKNOWN`. No 9/21.
5. **STRAT-006** beginner line — restore the spoken **VIX > 15–16** condition; not a blanket ban. Delta 0.55–0.60 stays WEAK.
6. **STRAT-011** — cannot read as “Dhan said trade NIFTY options this way.” `H_6kee` is stocks/gold. `gA5` **executed sell**. Buy-CE/PE mapping is PROJECT and **conflicts** with the tape.
7. **STRAT-012** — EN **does** name engulfing / morning star / dark cloud / inside bar. Rewrite “four patterns not extracted” as “named in EN; rule-detail WAITING,” not as missing from the video.
8. **ENGINE_MIX default ticket** — 003+007+009 AND and **5m MACD confirm-or-kill** stay **PROJECT_MIX**. Do not backfill a fake HAUS or Gokul timestamp for the AND.

**013 / 014** stay **SELL** / `WAITING`. EN confirms. Do not rewrite into buy.

---

## Count (this pass)

Counts are **row-level** in the STRAT table, plus **unique** ENGINE_MIX-club rows that are not already a STRAT row (the 5m-MACD staging row and the “named Dhan book” row). WEAK is separate. One STRAT can have several rows.

| bind | n | where |
|------|---|-------|
| **CONFIRMED** | 18 | 001 TFs; 001 MACD/MA/candle-high; 002 OTM/40Δ/20–30%; 003 3m futures; 003 all-three; 003 ST-exit; 003 ST/VWAP skip; 003 same-video clocks; 004 Super Scalper structure; 005 ITM/ATM; 006 2m EMA10/20 + ITM 100–200; 007 HAUS clock; 008 mixed-index; 009 09:45/15:15; 011 ST 10,3 spoken default; 012 hammer + not-standalone; 013 sell; 014 sell |
| **CONFLICT** | 4 | 001 MA 100 vs 300; 002 overlay on 003 / 002 vs 005 strike; 005 host vs guest 50-multiples; 011 gA5 buy-map vs executed bull put |
| **PROJECT_MIX** | 7 | 001 index-only yaml; 007 AND 009; 010 as 003 gate; 011 stock/gold → index options; 012 as 001/003 overlay; ENGINE_MIX 5m MACD confirm-or-kill vs HAUS MACD entry; ENGINE_MIX “003+007+009+staging+005” as one Dhan book |
| **NOT_IN_EN** | 2 | 001 **2h** parent; 004 Super Scalper **numeric lengths** |
| **WEAK** | 9 | 001 MACD ×3/×4; 001 MA 9 vs 10; 002 ₹1500–1700; 003 “103”; 005 0.60–0.75 digits; 006 “555 to 6”; 006 VIX-conditional beginner line vs STRAT blanket; 008 1-lot-each; 012 remaining-pattern **detail** still WAITING |

**Must-rewrite (04):** STRAT-001 2h comment + index universe tag; STRAT-002 “or 003”; STRAT-006 VIX condition; STRAT-011 origin honesty; STRAT-012 WAITING wording; ENGINE_MIX AND clocks + MACD-role stay PROJECT.

---

## HANDOFF (01 bind pass)

**Accepted**

- EN files exist for all nine required IDs. Gokul 003/005/008/009/004 structure binds. Himanshu 001/002/007 binds. Mukul 006 2m EMA 10/20 + ITM 100–200 binds. 013/014 are sell. Guests recorded as affiliation only.

**Rejected**

- Treating SEBI RA / “star trader” as edge. Merging 002+005. Treating 003+007+009 AND or 5m MACD confirm-or-kill as spoken. Using `H_6kee` as an index-option theorem. Inventing Super Scalper lengths. Inventing quotes.

**UNKNOWN / DATA_INSUFFICIENT**

- Super Scalper EMA lengths (NOT_IN_EN). MACD ×3 vs ×4; MA 100 vs 300; 9 vs 10. 2Rn “103.” pvmvki delta “555 to 6.” 012 engulfing / morning star / dark cloud / inside bar **rule detail** still WAITING. OF history on HQ (010) unchanged.

**04 applied (2026-09-03):** ENGINE_MIX + STRAT-001/002/003/004/006/011/012/013/014 cite this bind. 02/03 re-signed. 09 still NOTES_ONLY. 02 does not treat CONFIRMED as math. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.
