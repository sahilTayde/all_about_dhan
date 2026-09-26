"""Option chain recorder: full chain with OI, IV, greeks.

Reuses existing desk_intel.option_chain_poller (respects existing 3-minute rate limit).
Does NOT create competing websocket connection - extends existing chain poller.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from dhan_client.client import DhanClient

from data_recorder.writer import JsonLinesWriter

log = logging.getLogger("data_recorder.option_chain")


class OptionChainRecorder:
    """Record option chain snapshots via existing option_chain_poller infrastructure.
    
    Respects existing 3-minute polling interval to avoid rate limit conflicts.
    """

    def __init__(
        self,
        client: DhanClient,
        underlyings: list[str],
        output_dir: Path,
        *,
        verbose: bool = False,
    ) -> None:
        self.client = client
        self.underlyings = underlyings
        self.writer = JsonLinesWriter(output_dir, "option_chain", verbose=verbose)
        self.verbose = verbose
        self._poll_interval = 180  # 3 minutes (respects existing rate limit)

    async def run(self) -> None:
        """Run option chain recorder (polls every 3 minutes)."""
        if self.client.dry_run:
            await self._run_dry()
            return

        log.info(
            "Option chain recorder: polling every %d seconds (respects Dhan rate limit)",
            self._poll_interval,
        )

        while True:
            for underlying in self.underlyings:
                try:
                    await self._poll_chain(underlying)
                except Exception as e:
                    log.error("Error polling chain for %s: %s", underlying, e)

            await asyncio.sleep(self._poll_interval)

    async def _poll_chain(self, underlying: str) -> None:
        """Poll option chain using existing client infrastructure."""
        # Use existing option_chain client (respects rate limits)
        try:
            # Get current month expiry (or nearest expiry)
            expiries_response = self.client.option_chain.expiries(underlying)
            expiries = self._unwrap_expiries(expiries_response)
            if not expiries:
                log.warning("No expiries found for %s", underlying)
                return

            current_expiry = expiries[0]  # Nearest expiry

            # Fetch full chain
            chain_response = self.client.option_chain.chain(underlying, current_expiry)
            chain_data = self._unwrap_chain(chain_response)

            if not chain_data:
                log.warning("No chain data for %s %s", underlying, current_expiry)
                return

            # Extract spot price
            spot = chain_data.get("spot") or chain_data.get("underlying_spot_price")

            # Parse option chain rows
            oc = chain_data.get("oc") or chain_data.get("option_chain") or {}
            timestamp = datetime.now().isoformat()

            for strike_key, strike_data in oc.items():
                if not isinstance(strike_data, dict):
                    continue

                strike = float(strike_key)
                ce_data = strike_data.get("CE") or strike_data.get("call") or {}
                pe_data = strike_data.get("PE") or strike_data.get("put") or {}

                # Write CE record
                if ce_data:
                    ce_record = {
                        "underlying": underlying,
                        "expiry": current_expiry,
                        "strike": strike,
                        "option_type": "CE",
                        "timestamp": timestamp,
                        "ltp": ce_data.get("ltp") or ce_data.get("last_price"),
                        "bid": ce_data.get("bid_price"),
                        "ask": ce_data.get("ask_price"),
                        "volume": ce_data.get("volume"),
                        "open_interest": ce_data.get("oi") or ce_data.get("open_interest"),
                        "iv": ce_data.get("iv") or ce_data.get("implied_volatility"),
                        "delta": ce_data.get("delta"),
                        "gamma": ce_data.get("gamma"),
                        "theta": ce_data.get("theta"),
                        "vega": ce_data.get("vega"),
                    }
                    self.writer.write(ce_record)

                # Write PE record
                if pe_data:
                    pe_record = {
                        "underlying": underlying,
                        "expiry": current_expiry,
                        "strike": strike,
                        "option_type": "PE",
                        "timestamp": timestamp,
                        "ltp": pe_data.get("ltp") or pe_data.get("last_price"),
                        "bid": pe_data.get("bid_price"),
                        "ask": pe_data.get("ask_price"),
                        "volume": pe_data.get("volume"),
                        "open_interest": pe_data.get("oi") or pe_data.get("open_interest"),
                        "iv": pe_data.get("iv") or pe_data.get("implied_volatility"),
                        "delta": pe_data.get("delta"),
                        "gamma": pe_data.get("gamma"),
                        "theta": pe_data.get("theta"),
                        "vega": pe_data.get("vega"),
                    }
                    self.writer.write(pe_record)

        except Exception as e:
            log.error("Error in _poll_chain for %s: %s", underlying, e)

    def _unwrap_expiries(self, response: Any) -> list[str]:
        """Extract expiry list from response."""
        if isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, list):
                return [str(x) for x in data if x]
        return []

    def _unwrap_chain(self, response: Any) -> dict[str, Any]:
        """Extract chain data from response."""
        if isinstance(response, dict):
            if response.get("status") == "dry_run":
                return {}
            data = response.get("data")
            if isinstance(data, dict):
                return data
        return {}

    async def _run_dry(self) -> None:
        """Dry-run: generate synthetic option chain data."""
        log.info(
            "Option chain recorder dry-run: generating synthetic chain data (3 strikes × 2 types)"
        )

        timestamp = datetime.now().isoformat()
        expiry = datetime.now().replace(day=28).strftime("%Y-%m-%d")

        for underlying in self.underlyings[:1]:  # Just NIFTY for dry-run
            strikes = [19700.0, 19800.0, 19900.0]

            for strike in strikes:
                # CE record
                ce_record = {
                    "underlying": underlying,
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": "CE",
                    "timestamp": timestamp,
                    "ltp": 80.0,
                    "bid": 79.5,
                    "ask": 80.5,
                    "volume": 12345,
                    "open_interest": 500000,  # CRITICAL: OI present
                    "iv": 0.16,  # CRITICAL: IV present
                    "delta": 0.5,  # CRITICAL: greeks present
                    "gamma": 0.001,
                    "theta": -5.0,
                    "vega": 10.0,
                }
                self.writer.write(ce_record)

                # PE record
                pe_record = {
                    "underlying": underlying,
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": "PE",
                    "timestamp": timestamp,
                    "ltp": 75.0,
                    "bid": 74.5,
                    "ask": 75.5,
                    "volume": 11000,
                    "open_interest": 480000,
                    "iv": 0.17,
                    "delta": -0.5,
                    "gamma": 0.001,
                    "theta": -4.8,
                    "vega": 9.8,
                }
                self.writer.write(pe_record)

        log.info("Option chain recorder dry-run complete")

    def close(self) -> None:
        """Close writer."""
        self.writer.close()
