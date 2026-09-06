"""Offline / dry-run fixtures. Not live data. Cited as source=fixture."""

from __future__ import annotations

from desk_intel.schema import ChainSnapshot, NewsEvent, StrikeRow, TapePrint
from desk_intel.time_ist import now_ist_iso

# Compliance example: crude 90→95 is a RISK_OFF *hypothesis*, not PE spray.
FIXTURE_NEWS: list[NewsEvent] = [
    NewsEvent(
        event="CRUDE_MOVE",
        time_ist="2026-09-01T07:10:00+05:30",
        source_id="fixture_eia_style",
        source_url="https://www.eia.gov/rss/todayinenergy.xml",
        headline="Brent crude jumps from 90 to 95 on supply headline (FIXTURE)",
        tags=["MACRO_EVENT", "CRUDE"],
        risk_bias="RISK_OFF",
        surprise_vs_consensus=None,
        surprise_note="UNKNOWN — fixture has no consensus print",
        keywords_hit=["crude", "oil"],
        cited_url="https://www.eia.gov/rss/todayinenergy.xml",
        summary=(
            "HYPOTHESIS only: energy / INR / risk-off overlay. "
            "Not an automatic BUY PE. Confirm with chain OI and opening drive."
        ),
        layer="HYPOTHESIS",
    ),
    NewsEvent(
        event="RBI_WATCH",
        time_ist="2026-09-01T08:00:00+05:30",
        source_id="fixture_rbi_style",
        source_url="https://rbi.org.in/Scripts/rss.aspx",
        headline="RBI commentary watch — no policy print in fixture window",
        tags=["MACRO_EVENT", "RBI"],
        risk_bias="MIXED",
        surprise_vs_consensus=None,
        keywords_hit=["RBI"],
        cited_url="https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        summary="Placeholder calendar row. Surprise vs consensus UNKNOWN.",
        layer="HYPOTHESIS",
    ),
]


FIXTURE_TAPE_NOTE = (
    "VERIFY/TODO public delayed quote. Not a DhanHQ endpoint. "
    "GIFT Nifty (NSE IFSC) succeeded SGX Nifty. Do not scrape HTML as the only path."
)


def fixture_gift_prints() -> list[TapePrint]:
    return [
        TapePrint(
            id="gift_nifty_fixture",
            bucket="gift_nifty",
            status="FIXTURE",
            headline="GIFT Nifty ~25080 vs cash fixture 25000 (+80 pts premium)",
            source_url="https://www.nseindia.com/market-data/gift-nifty",
            note=FIXTURE_TAPE_NOTE,
            level=25080.0,
            vs_cash_note="+80 pts premium to cash Nifty fixture (HYPOTHESIS overlay, not a fill)",
            tags=["GIFT_NIFTY", "PRE_MARKET"],
        ),
        TapePrint(
            id="sgx_legacy_fixture",
            bucket="sgx",
            status="TODO",
            headline="SGX Nifty delayed quote — DATA_INSUFFICIENT (migrated to GIFT; no public XML in yaml)",
            source_url="https://www.sgx.com/derivatives/delayed-prices",
            note="SGX page is HTML. VERIFY remaining public feed. Not a Dhan endpoint.",
            tags=["SGX", "TODO"],
        ),
    ]


def fixture_global_prints() -> list[TapePrint]:
    return [
        TapePrint(
            id="us_close_fixture",
            bucket="global_us",
            status="FIXTURE",
            headline="US close fixture: S&P / Nasdaq mixed; crude bid (see EIA RSS path)",
            source_url="https://finance.yahoo.com/news/rssindex",
            note="Overnight US tape as regime context. RSS preferred; numbers here are FIXTURE.",
            tags=["US_CLOSE", "GLOBAL"],
        ),
        TapePrint(
            id="asia_fixture",
            bucket="global_asia",
            status="FIXTURE",
            headline="Asia fixture: Nikkei / Hang Seng mixed — not a Dhan quote",
            source_url="https://feeds.bbci.co.uk/news/business/rss.xml",
            note="Asia open context. VERIFY live RSS; do not invent index prints.",
            tags=["ASIA", "GLOBAL"],
        ),
    ]


def fixture_preopen_prints() -> list[TapePrint]:
    return [
        TapePrint(
            id="nse_preopen_fixture",
            bucket="pre_open",
            status="VERIFY",
            headline="NSE cash pre-open typically 09:00–09:08 IST — VERIFY FROM circular (no Dhan REST)",
            source_url="https://www.nseindia.com/market-data/pre-open-market-cm-and-emerge-market",
            note="HTML page. Do not scrape as the only path. Fixture has no bid/ask grid.",
            tags=["PRE_OPEN"],
        ),
    ]


def fixture_strikes(spot: float = 25000.0, step: float = 50.0) -> list[StrikeRow]:
    """Small ATM-centered chain so PCR / max-pain / buildup run without Dhan."""
    rows: list[StrikeRow] = []
    atm = round(spot / step) * step
    for i, offset in enumerate((-3, -2, -1, 0, 1, 2, 3)):
        k = atm + offset * step
        # Slight PE-heavy OI below ATM, CE wall above — typical stub, not a forecast.
        ce_oi = 800_000 + i * 40_000 + (120_000 if offset >= 1 else 0)
        pe_oi = 950_000 - i * 30_000 + (150_000 if offset <= -1 else 0)
        rows.append(
            StrikeRow(
                strike=float(k),
                ce_oi=ce_oi,
                pe_oi=pe_oi,
                ce_oi_prev=ce_oi - (25_000 if offset >= 0 else 5_000),
                pe_oi_prev=pe_oi - (40_000 if offset <= 0 else 8_000),
                ce_volume=50_000 + i * 2_000,
                pe_volume=60_000 + i * 1_500,
                ce_ltp=120.0 - offset * 18,
                pe_ltp=110.0 + offset * 16,
                ce_security_id=42000 + i * 2,
                pe_security_id=42001 + i * 2,
                ce_gamma=0.0012,
                pe_gamma=0.0011,
                ce_delta=0.5 - offset * 0.08,
                pe_delta=-0.5 + offset * 0.08,
            )
        )
    return rows


def fixture_chain(
    underlying: str = "NIFTY",
    *,
    expiry: str = "2026-09-03",
    spot: float = 25000.0,
    mode: str = "morning",
    dry_run: bool = True,
) -> ChainSnapshot:
    return ChainSnapshot(
        underlying=underlying,
        expiry=expiry,
        spot=spot,
        as_of_ist=now_ist_iso(),
        mode=mode,  # type: ignore[arg-type]
        dry_run=dry_run,
        strikes=fixture_strikes(spot),
        source="fixture",
        note="Dry-run fixture chain. Not a DhanHQ response.",
    )
