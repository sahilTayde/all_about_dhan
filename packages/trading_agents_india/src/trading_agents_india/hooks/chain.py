"""Option-chain watcher inputs: Dhan chain if tokens work, else fixtures.

Flags fake-breakout / thin-wall as HYPOTHESIS; DI when no data.
Never invents live OI walls as SOURCE_FACT without a parseable chain.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

ChainLean = Literal["CE", "PE", "NEUTRAL", "NO_TRADE"]
HypothesisFlag = Literal[
    "NONE",
    "FAKE_BREAKOUT_HYPOTHESIS",
    "THIN_WALL_HYPOTHESIS",
    "BOTH_HYPOTHESIS",
]

# VERIFY vs workspace.yaml / instrument master — not hard truth.
_SCRIP_HINTS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "SENSEX": (51, "IDX_I"),
}


@dataclass
class ChainWatchResult:
    underlying: str
    source: str  # dhan_live | fixture | desk_intel | unavailable
    chain_lean: ChainLean
    hypothesis_flag: HypothesisFlag
    summary: str
    layer: str = "HYPOTHESIS"
    data_gaps: list[str] = field(default_factory=list)
    wall_notes: list[str] = field(default_factory=list)
    raw_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fixture_watch(underlying: str, chain_lean: ChainLean) -> ChainWatchResult:
    flag: HypothesisFlag = "NONE"
    walls: list[str] = []
    if chain_lean == "NEUTRAL":
        flag = "THIN_WALL_HYPOTHESIS"
        walls.append(
            "HYPOTHESIS: fixture NEUTRAL lean — treat ATM walls as thin / untrusted"
        )
    elif chain_lean == "PE":
        # Soft fade days often fake CE breakouts then reverse — hypothesis only
        flag = "FAKE_BREAKOUT_HYPOTHESIS"
        walls.append(
            "HYPOTHESIS: PE lean fixture — watch for failed CE spray / fake breakout"
        )
    return ChainWatchResult(
        underlying=underlying,
        source="fixture",
        chain_lean=chain_lean,
        hypothesis_flag=flag,
        summary=(
            f"Chain watcher ({underlying}): fixture lean={chain_lean}; "
            f"flag={flag}. Not live OI. Fake-breakout/thin-wall are hypotheses only."
        ),
        data_gaps=[
            "DATA_INSUFFICIENT: live Dhan chain not required for dry fixtures",
        ],
        wall_notes=walls,
    )


def _parse_chain_lean_from_payload(payload: dict[str, Any]) -> tuple[ChainLean, list[str]]:
    """Honest minimal parse — prefer explicit bias fields; else DI→NEUTRAL."""
    gaps: list[str] = []
    for key in ("chain_lean", "lean", "bias", "option_bias"):
        val = payload.get(key)
        if isinstance(val, str) and val.upper() in ("CE", "PE", "NEUTRAL", "NO_TRADE"):
            return val.upper(), gaps  # type: ignore[return-value]
    # Nested data common in Dhan responses — do not invent OI walls
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("chain_lean", "lean"):
            val = data.get(key)
            if isinstance(val, str) and val.upper() in ("CE", "PE", "NEUTRAL", "NO_TRADE"):
                return val.upper(), gaps  # type: ignore[return-value]
    gaps.append(
        "DATA_INSUFFICIENT: option-chain payload lacks parseable lean — NEUTRAL"
    )
    return "NEUTRAL", gaps


def _hypotheses_from_lean(lean: ChainLean) -> tuple[HypothesisFlag, list[str]]:
    if lean == "NEUTRAL":
        return "THIN_WALL_HYPOTHESIS", [
            "HYPOTHESIS: thin/unclear wall — do not treat as alpha"
        ]
    if lean == "NO_TRADE":
        return "BOTH_HYPOTHESIS", [
            "HYPOTHESIS: NO_TRADE chain — fake-breakout + thin wall risk"
        ]
    return "NONE", []


def try_fetch_dhan_chain(underlying: str) -> Optional[ChainWatchResult]:
    """Attempt live Dhan optionchain. Fail soft → None (caller uses fixture)."""
    und = underlying.upper()
    hint = _SCRIP_HINTS.get(und)
    if hint is None:
        return None
    scrip, seg = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return None
    try:
        client = DhanClient(dry_run=False)
        # If tokens empty, client may dry-run or error — treat as unavailable
        if getattr(client.settings, "dry_run", True):
            client.close()
            return None
        body_u = {"UnderlyingScrip": scrip, "UnderlyingSeg": seg}
        expiries = client.option_chain.expiry_list(body_u)
        # Expiry list shape varies — pick first string date if present
        expiry = None
        data = expiries.get("data") if isinstance(expiries, dict) else None
        if isinstance(data, list) and data:
            expiry = str(data[0])
        elif isinstance(data, dict):
            lst = data.get("expiryList") or data.get("expiries") or []
            if lst:
                expiry = str(lst[0])
        if not expiry:
            client.close()
            return ChainWatchResult(
                underlying=und,
                source="unavailable",
                chain_lean="NEUTRAL",
                hypothesis_flag="THIN_WALL_HYPOTHESIS",
                summary="Dhan expiry list empty/unparsed — DI",
                data_gaps=["DATA_INSUFFICIENT: no expiry from Dhan optionchain"],
            )
        raw = client.option_chain.chain({**body_u, "Expiry": expiry})
        client.close()
        lean, gaps = _parse_chain_lean_from_payload(raw if isinstance(raw, dict) else {})
        flag, walls = _hypotheses_from_lean(lean)
        keys = sorted(raw.keys()) if isinstance(raw, dict) else []
        return ChainWatchResult(
            underlying=und,
            source="dhan_live",
            chain_lean=lean,
            hypothesis_flag=flag,
            summary=(
                f"Chain watcher ({und}): Dhan POST /optionchain lean={lean}; "
                f"flag={flag}. Wall notes are HYPOTHESIS unless OI parse validated."
            ),
            layer="SOURCE_FACT" if lean != "NEUTRAL" or "DATA_INSUFFICIENT" not in str(gaps) else "HYPOTHESIS",
            data_gaps=gaps
            + [
                "VALIDATION: OI wall / fake-breakout still HYPOTHESIS without validated parser"
            ],
            wall_notes=walls,
            raw_keys=keys[:24],
        )
    except Exception as exc:  # noqa: BLE001
        return ChainWatchResult(
            underlying=und,
            source="unavailable",
            chain_lean="NEUTRAL",
            hypothesis_flag="THIN_WALL_HYPOTHESIS",
            summary=f"Dhan chain fetch failed ({type(exc).__name__}) — DI",
            data_gaps=[f"DATA_INSUFFICIENT: dhan chain error {type(exc).__name__}"],
        )


def watch_chain(
    underlying: str,
    *,
    fixture_lean: ChainLean = "NEUTRAL",
    prefer_live: bool = False,
) -> ChainWatchResult:
    if prefer_live:
        live = try_fetch_dhan_chain(underlying)
        if live is not None and live.source == "dhan_live":
            return live
        if live is not None and live.source == "unavailable":
            # Merge DI onto fixture
            fx = _fixture_watch(underlying, fixture_lean)
            fx.data_gaps = list(dict.fromkeys(list(live.data_gaps) + list(fx.data_gaps)))
            fx.summary = live.summary + " | falling back to fixture. " + fx.summary
            return fx
    return _fixture_watch(underlying, fixture_lean)
