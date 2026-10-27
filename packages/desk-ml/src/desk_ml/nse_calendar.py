# Vendored verbatim from research/lab/lib/trading_calendar.py (sha256 bd31ed32...) on 2026-10-12 for market_read; CSVs alongside.
"""NSE trading calendar (2026-10-12, desk lead): trading day = weekday not in the NSE trading-holiday list (lib/nse_holidays_<year>.csv).
Covered years: 2025 (nse_holidays_2025.csv, NSE/FAOP/65588 = NSE/CMTR/65587, Dec 13 2024) and 2026 (nse_holidays_2026.csv). Other years raise CalendarError.
Muhurat days (e.g. 2025-10-21, one-hour evening session) count as holidays for the normal session.
prior_trading_day(D) never looks at tape dates and never falls back further: callers must mark DATA_MISSING when that day's tape is absent."""
import csv, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
class CalendarError(RuntimeError): pass
def holidays(year, d=HERE):
    p = Path(d) / f"nse_holidays_{year}.csv"
    if not p.exists(): raise CalendarError(f"no NSE holiday list for {year} ({p})")
    return {r["date"] for r in csv.DictReader(l for l in open(p) if not l.startswith("#"))}
def is_trading_day(day, d=HERE):
    t = datetime.date.fromisoformat(day) if isinstance(day, str) else day
    return t.weekday() < 5 and t.isoformat() not in holidays(t.year, d)
def prior_trading_day(day, d=HERE):
    t = datetime.date.fromisoformat(day) - datetime.timedelta(days=1)
    for _ in range(15):
        if is_trading_day(t, d): return t.isoformat()
        t -= datetime.timedelta(days=1)
    raise CalendarError(f"no trading day within 15 days before {day}")
