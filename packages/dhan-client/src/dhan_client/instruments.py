"""Instrument list — documented CSV + segment path.

https://dhanhq.co/docs/v2/instruments/

Public CSVs (no token in the docs):
  https://images.dhan.co/api-data/api-scrip-master.csv
  https://images.dhan.co/api-data/api-scrip-master-detailed.csv

Segment list:
  GET-or-VERIFY ``https://api.dhan.co/v2/instrument/{exchangeSegment}``

Column names differ between compact and detailed files — use the tags from
that page. Do not invent NIFTY/BANKNIFTY/SENSEX IDs; filter the CSV.
"""

from __future__ import annotations

from typing import Optional

from dhan_client import endpoints
from dhan_client.errors import DhanApiError
from dhan_client.logging_util import get_logger
from dhan_client.rest import RestClient, dry_run_envelope
from dhan_client.types import JsonDict

log = get_logger(__name__)

# Compact tags copied from the instruments page. Security-id column is NOT named
# in that table — inspect the live CSV header (see SECURITY_ID_COLUMN_CANDIDATES).
COMPACT_COLUMNS = (
    "SEM_EXM_EXCH_ID",
    "SEM_SEGMENT",
    "SEM_INSTRUMENT_NAME",
    "SM_SYMBOL_NAME",
    "SEM_CUSTOM_SYMBOL",
    "SEM_EXCH_INSTRUMENT_TYPE",
    "SEM_SERIES",
    "SEM_LOT_UNITS",
    "SEM_EXPIRY_DATE",
    "SEM_STRIKE_PRICE",
    "SEM_OPTION_TYPE",
    "SEM_TICK_SIZE",
    "SEM_EXPIRY_FLAG",
)

# Detailed CSV tags from the same page.
DETAILED_COLUMNS = (
    "EXCH_ID",
    "SEGMENT",
    "INSTRUMENT",
    "UNDERLYING_SECURITY_ID",
    "UNDERLYING_SYMBOL",
    "SYMBOL_NAME",
    "DISPLAY_NAME",
    "INSTRUMENT_TYPE",
    "SERIES",
    "LOT_SIZE",
    "SM_EXPIRY_DATE",
    "STRIKE_PRICE",
    "OPTION_TYPE",
    "TICK_SIZE",
    "EXPIRY_FLAG",
)

# Compact CSV security-id column is not named on the instruments page table.
# Inspect the downloaded header before filtering. UNKNOWN/VERIFY.
SECURITY_ID_COLUMN_CANDIDATES = (
    "SECURITY_ID",
    "SEM_SECURITY_ID",
    "SEM_SMST_SECURITY_ID",
    "SMST_SECURITY_ID",
    "UNDERLYING_SECURITY_ID",
)


class InstrumentClient:
    def __init__(self, rest: RestClient) -> None:
        self._rest = rest

    def scrip_master_url(self, *, detailed: bool = False) -> str:
        if detailed:
            return endpoints.SCRIP_MASTER_DETAILED_CSV
        return endpoints.SCRIP_MASTER_CSV

    def fetch_scrip_master_text(self, *, detailed: bool = False) -> str:
        """Download the public CSV. Dry-run returns an empty stub string."""
        url = self.scrip_master_url(detailed=detailed)
        if self._rest.settings.dry_run:
            log.info("dry-run: skip download of instrument CSV")
            return (
                "# dry_run: instrument master not downloaded\n"
                f"# url={url}\n"
                "# Look up SECURITY_ID from the live CSV; do not hardcode index IDs.\n"
            )
        response = self._rest.get_public(url)
        if not response.is_success:
            raise DhanApiError(
                f"instrument CSV HTTP {response.status_code}",
                status_code=response.status_code,
            )
        return response.text

    def fetch_segment(self, exchange_segment: str) -> JsonDict:
        """Segment-wise list. Path documented; HTTP method VERIFY (curl --location)."""
        segment = exchange_segment.strip()
        if not segment:
            raise ValueError("exchange_segment is required")
        path = endpoints.INSTRUMENT_SEGMENT.format(exchange_segment=segment)
        if self._rest.settings.dry_run:
            return dry_run_envelope("GET", path)
        return self._rest.request("GET", path)


def first_security_id_column(header: Optional[list[str]]) -> Optional[str]:
    """Pick a security-id column if the CSV header matches a candidate. VERIFY."""
    if not header:
        return None
    upper = {name.upper(): name for name in header}
    for candidate in SECURITY_ID_COLUMN_CANDIDATES:
        if candidate.upper() in upper:
            return upper[candidate.upper()]
    return None
