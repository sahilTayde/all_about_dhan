# Founder Guide: How Your Trading System Works

**For:** Sahil (founder). Written in plain English, not programmer jargon.

**Purpose:** This guide explains how your algo trading system works, how you control it, what each stage does, what can go wrong, and how to fix it.

---

## The Big Picture

Your system is like a **prop trading desk** with different people doing different jobs:

1. **You (Founder):** The boss of bosses. You can override anyone, stop everything, or adjust limits. **Your commands always win.**

2. **Pre-Market Analyst:** Wakes up before the market opens (8:45 AM IST), reads the news, checks what happened in US markets overnight, and writes a short summary for the Boss.

3. **Analysts (The Signal Generators):** These are like junior traders. Each one has their own strategy (STRAT-001, STRAT-007, etc.) or watches something specific (option chain, volume, dealer positions). When the Boss asks "Should we buy or sell?", each analyst votes. They don't trade—they just give opinions.

4. **Boss (The Orchestrator):** The head trader. He collects votes from all analysts, checks the rules (don't trade in choppy markets, don't trade after 3 PM, etc.), and decides: "Yes, buy NIFTY 19800 CE, 25 lots" or "No, market is too messy, wait." If he's unsure, he might ask ChatGPT for a second opinion (but ChatGPT is just an advisor—Boss makes the final call).

5. **Risk Manager:** A strict rule-checker. Before any trade goes out, Risk Manager says "PASS" or "VETO." He checks: Are we risking too much? Have we lost too much today already? Is this a duplicate order? If anything is wrong, he blocks the trade. **Even the Boss can't override the Risk Manager** (but you can, because you're the founder).

6. **Desk (The Executor):** Once Boss says "buy" and Risk Manager says "PASS," Desk sends the order to Dhan (your broker). He watches the order: Did Dhan accept it? Did it fill? What price did we get? He tracks the position: Are we in profit? Hit the target? Hit the stop loss? When it's time to exit, Desk closes the position.

7. **Monitor (The Watchdog):** Constantly watches everything. Are all the systems running? Is Dhan connected? Is the data coming in? If something breaks, Monitor alerts you (red flag on your dashboard, Telegram message, etc.).

8. **Post-Market Analyzer (GROK):** After the market closes (4 PM IST), GROK (an AI agent) reviews the day: What went well? What went wrong? He backtests new ideas, replays the exact trades from today, and **creates pull requests (PRs) with proposed changes**. But GROK **never merges PRs himself**—you review and decide whether to approve.

---

## How a Trade Happens (Step by Step)

**09:15 AM:** Market opens. Boss starts asking analysts every minute: "Should we trade?"

**09:30 AM:** Boss asks analysts:
- STRAT-007 (trend strategy): "BUY_CE, confidence 0.8, NIFTY breaking out above 19800."
- Chain analyst: "BUY_PE, confidence 0.6, I see more call selling (bearish)."
- Dealer analyst: "BUY_CE, confidence 0.5, dealers are buying puts (bullish)."
- Volume analyst: "ABSTAIN, no unusual volume."

Boss calculates weighted score (in the future, he'll weight by track record; right now, he uses majority vote). Score: +0.4 (bullish). Threshold is +0.3, so Boss decides: **"BUY_CE."**

Boss checks rules:
- Is the market choppy (consolidation)? **No** (range is wide, trending).
- Is it before 10 AM or after 2:30 PM? **No** (it's 9:30 AM, within trading window).
- Did we lose money in the last 15 minutes? **No**.

Boss picks strike: NIFTY is at 19820. Expiry is in 3 days (DTE = 3, so ≥2), so Boss picks **ITM100** (19720 CE, 100 points in-the-money). He sends: **"ENTRY_APPROVED: NIFTY 19720 CE, 25 lots, target +30%, stop -10%."**

Risk Manager checks:
- Max lots per trade: 25? **PASS** (limit is 25 for paper mode).
- Max open positions: 0 currently, max is 3? **PASS**.
- Daily loss: -₹0 so far, max is -₹15,000? **PASS**.
- Time: 9:30 AM, market is open? **PASS**.
- Duplicate order? **PASS** (no recent duplicate).

Risk Manager says: **"PASS."**

Desk receives approval, sends order to Dhan (in paper mode, Desk simulates the fill without calling Dhan). Order is **FILLED** at ₹52 (premium).

**Entry:** 25 lots × NIFTY lot size (25 shares/lot) × ₹52 = ₹32,500 position value.

Desk monitors the position every 10 seconds, watching the premium price (LTP). 

**10:15 AM:** NIFTY rallies to 19900. Premium is now ₹68 (+30.7% from entry). Target hit!

Boss receives update from Desk: "Position is at +30.7%, target was +30%." Boss says: **"EXIT_APPROVED."**

Desk exits: Sells 25 lots at ₹68.

**Realized P&L:** (₹68 - ₹52) × 25 lots × 25 shares = ₹10,000 (before charges).

**Charges:** Brokerage ₹40, STT ₹2, GST ₹7, total ≈₹49.

**Net P&L:** ₹10,000 - ₹49 = ₹9,951.

Your account ledger shows:
- **TRADE_PNL:** +₹10,000
- **CHARGES:** -₹49
- **Balance:** ₹100,000 (starting) + ₹9,951 = ₹109,951.

---

## Your Controls (Founder Commands)

You have a **Founder Page** (dashboard in your web browser or phone). Here's what you can do:

### 1. Start / Pause / Stop Trading

- **START:** Turn on the system. Boss will start generating signals, Desk will take trades (if Risk Manager approves).
- **PAUSE for N minutes:** Boss stops generating new signals for N minutes (e.g., "pause for 30 min" if you see big news and want to wait). Open positions are monitored but no new entries.
- **STOP:** Boss stops generating signals, but open positions are still monitored. No new entries until you START again.
- **KILL SWITCH:** **Emergency button.** Cancels all pending orders, exits all open positions immediately (market orders, no waiting), and stops all trading. Use this if Dhan API is acting weird, or markets are crashing, or you just want out NOW.

### 2. Override a Trade

- **Cut a loss early:** If a position is losing and you want out before stop loss hits, click the trade, click "EXIT NOW." Desk closes it immediately.
- **Go for bigger target:** If a position hit the first target (say +30%) but you think it'll run more, click "HOLD" or "NEW TARGET +50%." Desk adjusts.
- **Change lot size:** If a position is winning and you want to add more lots (or losing and you want to reduce), click "ADJUST LOTS." (This feature is in the plan, not built yet.)

### 3. Time Windows (Avoid Trading at Certain Times)

If you notice the system loses money every day between 12:00-12:30 PM (lunch hour, low volume), you can set: **"AVOID 12:00-12:30."** Boss will block new entries during that window.

### 4. Risk Limits

You can change these in the Founder Page → **Risk Limits** section:

- **Max lots per trade:** Default 25 (paper mode). When you go live, you might start with 5 lots (limited-live mode), then raise to 100 lots after you're confident.
- **Max daily loss:** Default -₹15,000 (paper mode). If you lose this much in one day, Risk Manager blocks all new trades (you can override, but it'll ask for confirmation).
- **Max open positions:** Default 3. If you want to allow only 1 trade at a time (safer), change to 1.

**Important:** Changing risk limits requires confirmation (a popup will ask "Are you sure?"). This prevents accidental clicks.

### 5. Which Analysts to Use

In the future, you'll have a page where you can **disable analysts**. For example, if "CHAIN-LEAN" analyst (option chain OI bias) keeps losing, you can turn him off. Boss will ignore his votes. Right now, this is in the code (you'd need to edit a config file), but the UI for this is planned.

---

## What Each Stage Means (In Simple Terms)

### Pre-Market (Before 9:15 AM)

**What it does:** Reads the news (MoneyControl, Economic Times), checks what happened in US markets overnight (did S&P 500 go up or down? Did oil spike?), and writes a short summary:

> "NIFTY gap +0.5% (US markets rallied +1.2%, dollar fell, risk-on mood). News: RBI kept rates unchanged (neutral). NIFTY is near yesterday's high (resistance at 19,850)."

Boss reads this summary (it's like a morning brief) and uses it to understand the context before trading starts.

**What can go wrong:**
- News scraper breaks (can't fetch headlines). Monitor will alert you. Fix: Restart the news scraper script, or Boss will trade without news context (not ideal, but not catastrophic).
- Global market data not available (Yahoo Finance API down). Fix: Boss trades without intermarket context.

### Analysts

**What they do:** Each analyst is a mini-strategy or a data-watcher. Examples:

- **STRAT-007:** Looks for trend breakouts (if NIFTY breaks above the 30-minute high with volume, vote BUY_CE).
- **Dealer Analyst:** Watches Nifty Dealer positions (PE writers vs CE writers). If dealers are net long (buying puts to hedge), they're bearish (so vote BUY_CE, because market might reverse up). This logic is tricky and currently **buggy** (reversed signal per the analysis; fix is in the plan).
- **Chain Analyst:** Watches option chain OI (open interest). If call OI is building up, it's resistance (bearish), so vote BUY_PE. Again, this is **currently reversed in the code** (fix planned).
- **ML-001, ML-002:** Machine learning models. Currently **broken** (trained on wrong data, degenerate clusters). They're disabled until fixed.

**What can go wrong:**
- Analyst crashes or times out (takes >500ms to vote). Boss will ignore that analyst's vote and use the others.
- Analyst gives bad signal (e.g., reversed OI logic). This is why **backtesting is critical**—if an analyst has a bad win rate, you should disable him or fix the logic.

### Boss

**What he does:** The decision-maker. Collects votes, checks rules, decides yes/no, picks the strike, sends to Desk.

**Rules he checks:**
1. **Consolidation block:** If the market is moving in a tight range (not trending), Boss blocks entry. Why? Choppy markets whipsaw (you buy, it goes down, you sell, it goes up—you lose on every move).
2. **Time cutoffs:** 
   - No new trades before 10:00 AM (avoid pre-open noise; proven fix from Sep 17-25 analysis).
   - No new trades after 2:30 PM (avoid end-of-day squeeze; proven fix).
   - Flatten all positions by 3:20 PM (5 min before close; avoid holding overnight).
3. **Loss cooldown:** If the last trade was a loss and exited <15 minutes ago, Boss blocks new entry. Why? Prevents revenge trading / overtrading (you lose, you immediately try to make it back, you lose again). Proven fix from Phase 3.
4. **DTE-aware strike selection:** 
   - If expiry is ≥2 days away (DTE ≥ 2): Pick **ITM100** (~100 points in-the-money; moderate premium, good liquidity).
   - If expiry is ≤1 day away (DTE ≤ 1): Pick **deep ITM200** (~200 points in-the-money; behaves more like futures, less theta decay). Proven fix.

**What can go wrong:**
- Boss logic has a bug (picks wrong strike, ignores a rule). This is why **tape replay** is critical—run today's exact market data through Boss, verify his decisions match expected.
- Boss calls ChatGPT (for second opinion) and ChatGPT API is down. Boss will trade without LLM opinion (fallback to his own decision).

### Risk Manager

**What he does:** The final gatekeeper. Blocks trades that violate limits.

**What can go wrong:**
- Risk Manager crashes. Desk should fail-closed (do NOT submit order if risk check fails; alert you).
- Risk limits are too tight (e.g., max loss -₹5,000, you hit it in first trade, no more trades all day). You can loosen limits in Founder Page, but be careful.

### Desk

**What he does:** Sends orders to Dhan, watches fills, monitors positions, exits when Boss says or stop loss hits.

**What can go wrong:**
- **Dhan API down:** Order submission fails. Desk retries 3×, then alerts you. You decide: wait for Dhan to recover, or manually trade via Dhan app/web.
- **Order rejected by Dhan:** Possible reasons: RMS rejection (risk management by Dhan; you don't have enough margin), symbol not found (wrong symbol name), market closed (you tried to trade outside 9:15-3:30). Desk logs error, alerts you.
- **Fill price far from LTP:** Slippage. You wanted to buy at ₹50, got filled at ₹52 (+4% slippage). This happens in low-liquidity strikes. **Solution:** Stick to ATM or ITM strikes (high liquidity), avoid deep OTM.
- **Reconciliation failure:** Desk thinks you have 1 open position, but Dhan says you have 0 (or vice versa). This is **critical**—means data is out of sync. Desk alerts you, halts new trades until resolved. **Fix:** Check Dhan order history manually, update internal book (manual SQL update or use Founder Page tool to "sync with Dhan").

### Monitor

**What he does:** Health checks. Is Dhan API reachable? Is data coming in? Are analysts voting? If anything is down, Monitor alerts you (red flag on dashboard + Telegram message if you set it up).

**What can go wrong:**
- Monitor crashes. You won't get alerts (blind). **Fix:** Monitor should be the simplest, most stable service (just health checks, no complex logic). If it crashes, systemd (on VPS) or your Mac will auto-restart it within 10 seconds.

### Post-Market (GROK, the Improvement Loop)

**What he does:** Every day at 4:00 PM (after market closes), GROK (AI) analyzes:
- Which trades won, which lost, why?
- Which analyst was right, which was wrong?
- Did we miss any opportunities (should have traded but didn't)?
- Did we make mistakes (traded but shouldn't have)?

GROK runs backtests on proposed changes (e.g., "What if we lower STRAT-007 weight in choppy markets?"), runs tape replay (re-simulate today's trades with the change), and if it improves results, **GROK creates a pull request (PR)** with the proposed change.

**You review the PR next morning** (or whenever you have time). The PR will show:
- **Backtest result:** "This change made +₹12,500 more over last 30 days (backtest)."
- **Tape replay result:** "This change made +₹18,300 more over last 7 days (exact trades)."
- **Risk:** "May hurt if choppy market suddenly trends; watch first 3 days."

You decide: **Merge (approve), Reject (ignore), or Shadow-log first (run both old and new in parallel for 3 days, compare).**

**Important:** GROK **never merges his own PRs**. You are the human gate. This prevents GROK from breaking the system.

**What can go wrong:**
- GROK proposes a bad change (backtest was overfitted, doesn't work in real trading). **Fix:** Shadow-log first (run in parallel), reject if it loses.
- GROK creates too many PRs (spam). **Fix:** Set a rule: max 1 PR per day (most important change only).

---

## Health Indicators (What to Watch on Your Dashboard)

Your **Founder Page** has a **Health Panel** (top-right corner, like a traffic light):

### Green = OK
- **Dhan API:** Connected, last order 10 sec ago.
- **Data (option chain):** Last update 1 min ago (fresh).
- **News:** Last headline 5 min ago (recent).
- **Analysts:** All voted in last 2 min.

### Yellow = Warning (Not Critical, But Watch)
- **Dhan API:** Last successful call 3 min ago (slow, but not dead).
- **Data:** Last update 4 min ago (stale, but usable).
- **News:** Last headline 20 min ago (slow day, or scraper is slow).

### Red = Critical (Something is Broken)
- **Dhan API:** No response for >5 min (DOWN). **Action:** Check Dhan status page (https://status.dhan.co or similar). If Dhan is down, you can't trade. Wait for recovery, or manually trade via Dhan app.
- **Data:** No option chain update for >5 min (DOWN). **Action:** Restart option chain recorder script. If still broken, check Dhan API (maybe websocket is down).
- **News:** No headlines for >1 hour (DOWN). **Action:** Restart news scraper. If still broken, pre-market analysis will be incomplete (Boss trades without news context).
- **Analyst (e.g., STRAT-007):** No vote for >10 min (CRASHED or STUCK). **Action:** Restart analyst script. Boss will trade without that analyst's vote (other analysts still work).

**Alert Delivery:**
- **Dashboard:** Red flag appears immediately (websocket push, <10 sec delay).
- **Telegram (optional):** If you set up Telegram bot, you'll get a message on your phone: "⚠️ Dhan API DOWN. Last seen 5 min ago."
- **Email (optional):** If you set up email alerts, you'll get an email (slower, ~1 min delay).

---

## Emergency: What to Do If Things Go Wrong

### 1. Market is crashing, I want out NOW
**Action:** Click **KILL SWITCH** on Founder Page.

**What happens:**
- All pending orders are cancelled.
- All open positions are exited (market orders, immediate).
- Boss stops generating new signals.
- Desk stops taking new trades.

**Recovery:** After the crash, click **START** to resume trading (or leave it stopped if you're done for the day).

---

### 2. I see a position losing a lot, stop loss hasn't hit yet
**Action:** Click the trade in the **Open Positions** list, click **EXIT NOW**.

**What happens:**
- Desk overrides Boss, exits the position immediately (market order).
- Realized P&L is recorded (will be a loss).

---

### 3. Dhan API is down (red flag on dashboard)
**Action:**
- Check Dhan status (web search "Dhan status" or check their Twitter).
- If Dhan is down, you **cannot** send orders via the system. Options:
  - **Wait** for Dhan to recover (usually <10 min).
  - **Manually trade** via Dhan mobile app or web (if you have an urgent position to exit).
- If Dhan is up but the system says it's down:
  - Restart Dhan adapter: `systemctl restart desk` (on VPS) or restart the Desk script (on Mac).
  - Check logs: `logs/desk.log` for error messages (maybe auth token expired; re-login to Dhan).

---

### 4. Reconciliation failure (dashboard says "Position mismatch")
**Action:**
- **Don't panic.** This means Dhan's records and the system's internal records don't match (e.g., system thinks you have 1 position, Dhan says 0).
- **Check Dhan manually:** Open Dhan app/web, go to Positions. What do you see?
- **Compare with system:** Open Founder Page → Positions. What does the system show?
- **Fix:**
  - If Dhan is correct (system is wrong): Founder Page → "Sync with Dhan" button (planned feature; syncs internal book with Dhan). Or manually close the internal position (mark as closed without submitting order).
  - If system is correct (Dhan is wrong): Rare; contact Dhan support (maybe their API glitched).
- **Root cause:** Probably missed a fill notification (websocket dropped, Desk didn't receive FILLED event). Restart Desk, re-subscribe to order updates.

---

### 5. I want to change risk limits (e.g., increase max daily loss from -₹15k to -₹30k)
**Action:**
- Founder Page → **Risk Limits** section.
- Change "Max daily loss" to -30000.
- Click **Save**. A popup will ask: "You are increasing max daily loss from -₹15,000 to -₹30,000. This allows bigger losses. Are you sure?" Click **Confirm**.

**What happens:**
- New limit is saved to `config/risk_limits.yaml`.
- Risk Manager immediately uses the new limit (no restart needed).

**Warning:** Be careful with risk limits. Don't set max daily loss to -₹1,000,000 "just to be safe"—if the system has a bug or market gaps, you could lose a lot before you notice.

---

## Modes: Paper → Shadow → Limited-Live → Live

Your system has **4 modes** (you control this in Founder Page → **Mode** section):

### 1. Paper Mode (Default, Safe)
- **No real orders.** Desk simulates fills (assumes you got filled at LTP, no slippage).
- **No real money.** Starting capital is virtual (₹100,000).
- **Use case:** Testing strategies, UI, flows. Safe, no risk.

### 2. Shadow Mode (Real API, No Fills)
- **Real orders submitted to Dhan, then immediately cancelled** (before fill).
- **No real money** (orders are cancelled before fill; you pay small Dhan cancellation charge, ₹0-5 per order—check Dhan pricing).
- **Use case:** Test broker integration. Measure latency (how fast is Dhan API?). Check for errors (does Dhan reject orders? RMS issues?).
- **Run for 3 days** before going to limited-live (make sure latency is good, error rate is low).

### 3. Limited-Live Mode (Real Money, Small Size)
- **Real orders, real fills, real money.**
- **Low limits:** Max 5 lots per trade, max ₹50k exposure, max -₹10k daily loss.
- **Use case:** First real money. Prove the strategy works with real slippage, real costs, real broker behavior.
- **Graduation criteria:** After ≥20 trades, if you're positive P&L and max drawdown < -20%, you can move to Live mode.

### 4. Live Mode (Full Capital)
- **Real orders, real fills, real money.**
- **High limits:** Max 100 lots per trade (or whatever you set), max ₹25L exposure, max -₹50k daily loss.
- **Use case:** Full deployment. Only after successful limited-live phase + your approval.

**Mode transitions:**
- **Paper → Shadow:** You enable in Founder Page. Requires: broker adapter tested, Dhan credentials valid, you confirm "I understand orders will be submitted and cancelled."
- **Shadow → Limited-Live:** You enable. Requires: shadow mode ran ≥3 days, no API errors, latency good, you confirm "I understand real fills will occur, max ₹10k daily loss."
- **Limited-Live → Live:** You enable. Requires: limited-live ran ≥20 trades, positive P&L, max DD < -20%, you review and approve.

---

## Data: What We Record and Why

Every day, the system records:

1. **Index ticks (1-min bars):** NIFTY, BANKNIFTY, SENSEX. Open, high, low, close per minute. **Why:** Backtesting needs minute-level data to replay trades.

2. **Futures ticks (1-min bars):** NIFTY, BANKNIFTY, SENSEX futures. Open, high, low, close, **volume**. **Why:** Volume is currently missing (lab analysis said this is the #1 blocker). Futures volume shows smart money (institutions trade futures, not options).

3. **Option chain (all strikes, per minute):** LTP, bid, ask, volume, OI (open interest), IV (implied volatility), greeks (delta, gamma, theta, vega). **Why:** OI analysis (which strikes are building up? Where is resistance/support?). IV analysis (is volatility spiking? Calm?). Greeks (hedge delta, gamma scalp).

4. **Heavyweights (top 15 NIFTY stocks, per minute):** Reliance, TCS, HDFC Bank, etc. LTP per minute. **Why:** Breadth analysis (is NIFTY going up because all stocks are up, or just 1-2 big stocks? Strong breadth = healthy trend, weak breadth = reversal risk).

5. **News (headlines + event tags):** MoneyControl, Economic Times. Headline, timestamp, URL, sentiment (bullish/bearish/neutral), event tags (RBI policy, earnings, global shock, etc.). **Why:** Context for Boss ("NIFTY gapped down 2% on US Fed hike; avoid trend-following today"). Event memory ("Last 5 times RBI hiked rates, NIFTY fell avg -1.2% next day; prefer PE today").

6. **Global markets (daily close):** S&P 500, Nasdaq, DXY (dollar index), US 10-year yield, crude oil, gold, USDINR. **Why:** Intermarket analysis (if US markets rallied +2% overnight and dollar fell, India will likely gap up—bullish). Lab analysis showed this correlates with NIFTY gap (0.4), not intraday moves.

**Storage:**
- **During market hours:** Data is written to `data/recon/` (JSON files, one per day per source).
- **After market hours (4 PM):** Nightly ETL job reads JSON files, cleans, aggregates, writes to **warehouse (DuckDB or Parquet files)** for backtesting and analysis.

**Retention:** ≥3 years (backtesting needs historical data). After 3 years, archive to cheap storage or delete.

**Why can't we backfill?** Because Dhan API doesn't provide historical tick data (or charges for it). NSE provides end-of-day bhavcopy (free), but not intraday ticks. **That's why data recorder is PR-001 (highest priority)—start recording NOW, accumulate data over months.**

---

## What's Next? (After This Planning PR Merges)

This PR is **documentation and planning only** (no code changes to runtime system). Once you approve and merge, the next steps are:

1. **PR-001: Data Recorder** (start immediately; cannot backfill).
2. **PR-002: Broker Adapter** (blocks live trading; test in shadow mode).
3. **PR-003: Risk Engine** (blocks live trading; veto power).
4. **PR-004: Health Alarms** (so you know when things break).
5. **PR-005: Ledger & Charges** (accurate P&L and cost tracking).

After these 5 PRs (Phase 1), you'll have the **P0 safety core** ready. Then:

6. **PR-006 to PR-009: Refactor** (extract boss, desk, analysts into separate modules; no behavior change, just cleaner code).
7. **PR-010: Fix Bugs** (look-ahead data leakage, reversed OI signal, degenerate ML models).
8. **PR-011: Proven Fixes** (15-min loss cooldown, DTE-aware strikes, STRAT-007 clock 10:00-14:30).

After these (Phase 2), you'll have a stable, well-tested paper trading system. Then move to VPS, shadow mode, limited-live, and eventually live.

**Timeline (rough estimate, depends on how fast PRs are completed):**
- Phase 1 (PR-001 to PR-005): 3-4 weeks.
- Phase 2 (PR-006 to PR-011): 3-4 weeks.
- Shadow mode testing: 1 week.
- Limited-live: 2-4 weeks (need ≥20 trades).
- Live: After you approve.

**Total:** ~8-12 weeks from now to live trading (if all goes well).

---

## Glossary (Terms You'll Hear)

- **ATM (At-The-Money):** Strike price closest to current index level. E.g., NIFTY at 19800, 19800 CE/PE are ATM. High liquidity.
- **ITM (In-The-Money):** Strike price where option has intrinsic value. For CE: strike < index. For PE: strike > index. E.g., NIFTY at 19800, 19700 CE is ITM100 (~100 points in-the-money). Lower premium than ATM, but more predictable (behaves more like futures).
- **OTM (Out-of-The-Money):** Strike price where option has no intrinsic value, only time value. For CE: strike > index. For PE: strike < index. E.g., NIFTY at 19800, 19900 CE is OTM100. Higher return if correct, but high risk (expires worthless if wrong).
- **OI (Open Interest):** Number of open contracts (not closed yet). High OI at a strike = strong support/resistance (many traders are long/short at that level).
- **IV (Implied Volatility):** Market's expectation of future volatility. High IV = expensive options (market expects big moves). Low IV = cheap options (market expects calm).
- **Theta:** Option decay (how much value option loses per day). ITM deep options have low theta (less decay), ATM/OTM have high theta.
- **Delta:** How much option price changes per 1-point index move. ATM delta ≈ 0.5, deep ITM delta ≈ 1.0 (moves like futures).
- **DTE (Days to Expiry):** How many days until option expires. DTE = 0 = expiry day, DTE = 7 = weekly expiry, DTE = 30 = monthly expiry.
- **Slippage:** Difference between expected fill price and actual fill price. E.g., you wanted to buy at ₹50, got filled at ₹52 → slippage = +₹2 (cost you more). Caused by low liquidity or fast-moving market.
- **P&L (Profit & Loss):** How much money you made/lost. **Unrealized P&L:** Open position (not closed yet; paper profit/loss). **Realized P&L:** Closed position (actual profit/loss in your account).
- **Backtest:** Simulate trading strategy on historical data. E.g., "What if I used STRAT-007 on last 3 years of NIFTY data? Would I have made money?" **Honest backtest:** Uses realistic fills (not signal close), includes costs, no look-ahead (doesn't peek into future). **Flawed backtest:** Assumes perfect fills, no costs, looks ahead (overstates profit; not trustworthy).
- **Tape replay:** Re-run exact trades from a real day using exact market data (quotes, timestamps). More accurate than backtest (because data is real, not historical simulation).

---

**Questions?** If something is unclear, ask in the GitHub issue or chat. This guide will be updated as the system evolves.

---

**Last updated:** 2026-09-26 (Rebuild planning package)
