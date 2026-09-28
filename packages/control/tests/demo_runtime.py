"""Short V2-11 runtime demo: pause, kill, rearm, flatten. Paper only."""

from __future__ import annotations

import json
from pathlib import Path

from helpers import make_handler, open_one

from control.flatten import flatten_paper
from control.handler import submit


def main(tmp: Path) -> dict:
    pm, clock = open_one(tmp)
    handler = make_handler(tmp, clock, manager=pm)
    pause = submit(handler, "PAUSE", {"minutes": 10}, actor="sahil", reason="lunch", command_id="demo-pause")
    kill = submit(handler, "KILL", {}, actor="sahil", reason="demo-kill", command_id="demo-kill")
    rearm = submit(handler, "REARM", {}, actor="sahil", reason="demo-rearm", command_id="demo-rearm")
    pm2, clock2 = open_one(tmp)
    flat = flatten_paper(account="founder", clock=clock2, risk=pm2.router.risk, manager=pm2)
    out = {
        "pause": pause["status"],
        "kill": kill["status"],
        "rearm": rearm["status"],
        "flatten_ok": flat["ok"],
        "open_after_kill": len(pm.open_book()),
        "open_after_flatten": len(pm2.open_book()),
        "paper_only": True,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        main(Path(raw))
