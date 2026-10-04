"""P0 Mac run: desk.sh branches (health fallback, node PATH, recorder, preflight)."""

from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DESK = REPO / "scripts" / "desk.sh"


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _source(
    tmp: Path, snippet: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    recon = tmp / "recon"
    recon.mkdir(exist_ok=True)
    merged = os.environ.copy()
    merged.update(env or {})
    merged["DESK_SH_SOURCED"] = "1"
    merged["AAD_RECON"] = str(recon)
    merged["AAD_TAPE_V2"] = str(tmp / "tape")
    script = f"source '{DESK}'\n{snippet}\n"
    return subprocess.run(
        ["/usr/bin/bash", "-c", script],
        cwd=REPO,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_b_dual_tape_runs_without_health_supervise(tmp_path: Path) -> None:
    fake_py = tmp_path / "no_health.py"
    _write_exec(
        fake_py,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys
            if len(sys.argv) >= 3 and sys.argv[1] == "-c" and "health.supervise" in sys.argv[2]:
                raise SystemExit(1)
            raise SystemExit(0)
            """
        ),
    )
    proc = _source(
        tmp_path,
        "dual_tape_launch_inner",
        env={"AAD_PY": str(fake_py)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "WARNING: health.supervise is not importable" in proc.stderr
    assert "health.supervise" not in proc.stdout
    assert (
        "trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0"
        in proc.stdout
    )


def test_b_dual_tape_uses_health_when_importable(tmp_path: Path) -> None:
    fake_py = tmp_path / "has_health.py"
    _write_exec(
        fake_py,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys
            if len(sys.argv) >= 3 and sys.argv[1] == "-c" and "health.supervise" in sys.argv[2]:
                raise SystemExit(0)
            raise SystemExit(0)
            """
        ),
    )
    proc = _source(
        tmp_path,
        "dual_tape_launch_inner",
        env={"AAD_PY": str(fake_py)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "WARNING" not in proc.stderr
    assert "health.supervise --" in proc.stdout
    assert (
        "trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0"
        in proc.stdout
    )


def test_c_find_node_path_then_anaconda_then_homebrew_then_nvm(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path_dir = tmp_path / "on_path"
    path_dir.mkdir()
    _write_exec(path_dir / "node", "#!/bin/sh\nexit 0\n")
    proc = _source(
        tmp_path,
        "find_node && echo NODE_DIR=$NODE_DIR",
        env={"HOME": str(home), "PATH": f"{path_dir}:/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert str(path_dir) in proc.stdout

    anaconda = home / "Documents" / "anaconda3" / "bin"
    anaconda.mkdir(parents=True)
    _write_exec(anaconda / "node", "#!/bin/sh\nexit 0\n")
    proc = _source(
        tmp_path,
        "find_node && echo NODE_DIR=$NODE_DIR",
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "AAD_SKIP_SYSTEM_NODE_DIRS": "1",
        },
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert str(anaconda) in proc.stdout

    nvm_old = home / ".nvm" / "versions" / "node" / "v16.0.0" / "bin"
    nvm_new = home / ".nvm" / "versions" / "node" / "v20.11.0" / "bin"
    nvm_old.mkdir(parents=True)
    nvm_new.mkdir(parents=True)
    _write_exec(nvm_old / "node", "#!/bin/sh\nexit 0\n")
    _write_exec(nvm_new / "node", "#!/bin/sh\nexit 0\n")
    # Hide anaconda so nvm is reached (no PATH node, no anaconda after we remove it).
    (anaconda / "node").unlink()
    proc = _source(
        tmp_path,
        "find_node && echo NODE_DIR=$NODE_DIR",
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "AAD_SKIP_SYSTEM_NODE_DIRS": "1",
        },
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "v20.11.0" in proc.stdout
    assert "v16.0.0" not in proc.stdout


def test_c_find_node_nvm_newest_without_gnu_sort_v(tmp_path: Path) -> None:
    home = tmp_path / "home"
    shim = tmp_path / "shim"
    shim.mkdir()
    home.mkdir()
    _write_exec(
        shim / "sort",
        textwrap.dedent(
            """\
            #!/bin/sh
            for a in "$@"; do
              if [ "$a" = "-V" ]; then
                echo "sort: invalid option -- V" >&2
                exit 2
              fi
            done
            exec /usr/bin/sort "$@"
            """
        ),
    )
    for ver in ("v18.20.4", "v20.9.0", "v20.11.1"):
        d = home / ".nvm" / "versions" / "node" / ver / "bin"
        d.mkdir(parents=True)
        _write_exec(d / "node", "#!/bin/sh\nexit 0\n")
    proc = _source(
        tmp_path,
        "find_node && echo NODE_DIR=$NODE_DIR",
        env={
            "HOME": str(home),
            "PATH": f"{shim}:/usr/bin:/bin",
            "AAD_SKIP_SYSTEM_NODE_DIRS": "1",
        },
    )
    blob = proc.stdout + proc.stderr
    assert proc.returncode == 0, blob
    assert "v20.11.1" in proc.stdout
    assert "v18.20.4" not in proc.stdout
    assert "v20.9.0" not in proc.stdout
    assert "invalid option" not in blob


def test_c_find_node_errors_when_missing(tmp_path: Path) -> None:
    home = tmp_path / "empty_home"
    home.mkdir()
    proc = _source(
        tmp_path,
        "find_node",
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "AAD_SKIP_SYSTEM_NODE_DIRS": "1",
        },
    )
    assert proc.returncode != 0
    assert "ERROR: node not found" in proc.stderr


def test_d_mac_setup_v2_never_touches_legacy_venv() -> None:
    text = (REPO / "scripts" / "mac_setup_v2.sh").read_text(encoding="utf-8")
    assert ".venv-v2" in text
    assert "refusing to install v2 packages into the legacy .venv" in text
    assert "dhan-client" in text and "marketdata" in text
    assert "python3.11" in text and "python3.12" in text
    assert "uv" in text
    assert "packages/shadow" in text
    assert "packages/runtime" in text
    assert "packages/contracts" in text
    assert "packages/brokers" not in text
    assert "packages/ledger" not in text
    assert "packages/risk-engine" not in text
    assert "does not touch .venv" in text or "legacy .venv" in text.lower()


def test_d_mac_setup_refuses_legacy_venv_path(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["/usr/bin/bash", str(REPO / "scripts" / "mac_setup_v2.sh")],
        cwd=REPO,
        env={
            **os.environ,
            "AAD_ROOT": str(REPO),
            "AAD_V2_VENV": str(REPO / ".venv"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "refusing to install v2 packages into the legacy .venv" in proc.stderr
    assert "Legacy .venv was not modified" not in proc.stdout or proc.returncode != 0


def test_e_recorder_start_refuses_second_copy(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "pgrep", "#!/bin/sh\necho 4242\n")
    _write_exec(bin_dir / "screen", "#!/bin/sh\necho .v2-recorder (Detached)\n")
    v2 = tmp_path / "venv-v2" / "bin"
    v2.mkdir(parents=True)
    _write_exec(v2 / "python", "#!/bin/sh\nexit 0\n")
    proc = _source(
        tmp_path,
        "recorder_start",
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "AAD_V2_PY": str(v2 / "python"),
        },
    )
    assert proc.returncode != 0
    assert "already running" in proc.stderr
    assert "Refusing a second copy" in proc.stderr


def test_e_close_stops_v2_recorder() -> None:
    text = DESK.read_text(encoding="utf-8")
    close = text.split("close|night|nightly)", 1)[1].split("website)", 1)[0]
    assert "recorder_stop" in close
    assert "shadow_stop" in close
    assert "stop_dual_tape" in close
    assert "v2_stop" not in close
    assert "v2_start" not in text
    assert "start-all" not in text
    assert "legacy close continues" in close


def test_e_shadow_start_refuses_second_copy(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "pgrep", "#!/bin/sh\necho 4242\n")
    _write_exec(bin_dir / "screen", "#!/bin/sh\necho .v2-shadow (Detached)\n")
    v2 = tmp_path / "venv-v2" / "bin"
    v2.mkdir(parents=True)
    _write_exec(v2 / "python", "#!/bin/sh\nexit 0\n")
    proc = _source(
        tmp_path,
        "shadow_start",
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "AAD_V2_PY": str(v2 / "python"),
            "AAD_SHADOW": str(tmp_path / "shadow-v2"),
        },
    )
    assert proc.returncode != 0
    assert "already running" in proc.stderr
    assert "Refusing a second copy" in proc.stderr


def test_e_shadow_start_requires_runner_not_just_shadow(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "pgrep", "#!/bin/sh\nexit 1\n")
    _write_exec(bin_dir / "screen", "#!/bin/sh\nexit 0\n")
    v2 = tmp_path / "venv-v2" / "bin"
    v2.mkdir(parents=True)
    _write_exec(
        v2 / "python",
        textwrap.dedent(
            """\
            #!/bin/sh
            if [ "$1" = "-c" ]; then
              case "$2" in
                *shadow.runner*)
                  echo "ModuleNotFoundError: No module named 'brokers'" >&2
                  exit 1
                  ;;
                *import*shadow*)
                  exit 0
                  ;;
              esac
            fi
            if [ "$1" = "-m" ] && [ "$2" = "shadow" ]; then
              exit 0
            fi
            exit 0
            """
        ),
    )
    proc = _source(
        tmp_path,
        "shadow_start",
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "AAD_V2_PY": str(v2 / "python"),
            "AAD_SHADOW": str(tmp_path / "shadow-v2"),
        },
    )
    assert proc.returncode != 0
    assert "import shadow.runner failed" in proc.stderr
    assert "STARTED" not in proc.stdout


def test_e_shadow_start_requires_python_m_shadow(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "pgrep", "#!/bin/sh\nexit 1\n")
    _write_exec(bin_dir / "screen", "#!/bin/sh\nexit 0\n")
    v2 = tmp_path / "venv-v2" / "bin"
    v2.mkdir(parents=True)
    _write_exec(
        v2 / "python",
        textwrap.dedent(
            """\
            #!/bin/sh
            if [ "$1" = "-c" ]; then
              exit 0
            fi
            if [ "$1" = "-m" ] && [ "$2" = "shadow" ]; then
              echo "ModuleNotFoundError: No module named 'brokers'" >&2
              exit 1
            fi
            exit 0
            """
        ),
    )
    proc = _source(
        tmp_path,
        "shadow_start",
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "AAD_V2_PY": str(v2 / "python"),
            "AAD_SHADOW": str(tmp_path / "shadow-v2"),
        },
    )
    assert proc.returncode != 0
    assert "python -m shadow failed" in proc.stderr
    assert "STARTED" not in proc.stdout


def test_e_shadow_start_fails_closed_if_follower_dies(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "pgrep", "#!/bin/sh\nexit 1\n")
    _write_exec(bin_dir / "screen", "#!/bin/sh\nexit 0\n")
    v2 = tmp_path / "venv-v2" / "bin"
    v2.mkdir(parents=True)
    _write_exec(
        v2 / "python",
        textwrap.dedent(
            """\
            #!/bin/sh
            exit 0
            """
        ),
    )
    proc = _source(
        tmp_path,
        "shadow_start",
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "AAD_V2_PY": str(v2 / "python"),
            "AAD_SHADOW": str(tmp_path / "shadow-v2"),
        },
    )
    assert proc.returncode != 0
    assert "follower died after start" in proc.stderr
    assert "fail closed" in proc.stderr
    assert "STARTED" not in proc.stdout


def test_e_shadow_start_missing_venv_does_not_touch_legacy(tmp_path: Path) -> None:
    proc = _source(
        tmp_path,
        "shadow_start",
        env={"AAD_V2_PY": str(tmp_path / "no-v2")},
    )
    assert proc.returncode != 0
    assert "mac_setup_v2.sh" in proc.stderr
    assert "does not touch .venv" in proc.stderr


def test_e_morning_does_not_start_shadow() -> None:
    text = DESK.read_text(encoding="utf-8")
    morning = text.split("morning|start)", 1)[1].split("close|night|nightly)", 1)[0]
    assert "shadow_start" not in morning
    assert "recorder_start" not in morning


def test_e_recorder_status_last_log_line(tmp_path: Path) -> None:
    day_dir = tmp_path / "tape" / "2099-01-02"
    day_dir.mkdir(parents=True)
    (day_dir / "recorder.log").write_text(
        "noise\nSUMMARY coverage ok\n", encoding="utf-8"
    )
    fake_py = tmp_path / "ist.py"
    _write_exec(
        fake_py,
        "#!/usr/bin/env python3\nprint('2099-01-02')\n",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "pgrep", "#!/bin/sh\nexit 1\n")
    _write_exec(bin_dir / "screen", "#!/bin/sh\nexit 1\n")
    proc = _source(
        tmp_path,
        "recorder_status",
        env={
            "AAD_PY": str(fake_py),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
        },
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SUMMARY coverage ok" in proc.stdout
    assert "STOPPED" in proc.stdout


def test_legacy_pythonpath_includes_desk_and_risk_engine(tmp_path: Path) -> None:
    # Isolate from a leftover full packages/*/src PYTHONPATH (the PR #70 workaround).
    proc = _source(
        tmp_path,
        'echo "SRC=$(legacy_src_path)"; ensure_legacy_pythonpath; echo "PP=$PYTHONPATH"',
        env={"PYTHONPATH": ""},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    src_line = next(
        line for line in proc.stdout.splitlines() if line.startswith("SRC=")
    )
    pp_line = next(line for line in proc.stdout.splitlines() if line.startswith("PP="))
    for required in (
        "packages/desk/src",
        "packages/risk-engine/src",
        "packages/brokers/src",
        "packages/health/src",
    ):
        assert required in src_line
        assert required in pp_line
    for v2_only in (
        "packages/contracts/src",
        "packages/events/src",
        "packages/runtime/src",
        "packages/oms/src",
        "packages/control/src",
        "packages/boss/src",
        "packages/marketdata/src",
        "packages/data-recorder/src",
    ):
        assert v2_only not in src_line, v2_only
        assert v2_only not in pp_line, v2_only


def test_start_paths_keep_packages_on_pythonpath() -> None:
    text = DESK.read_text(encoding="utf-8")
    assert "ensure_legacy_pythonpath" in text
    assert "legacy_src_path" in text
    api = text.split("start_api()", 1)[1].split("ensure_api_web()", 1)[0]
    assert "apps/api/src" in api
    assert "PYTHONPATH" in api
    # Must not wipe packages/*/src the way `PYTHONPATH=apps/api/src` alone did.
    assert "PYTHONPATH=apps/api/src '" not in text
    dt = text.split("start_dual_tape()", 1)[1].split("arm_dual_tape_when_open()", 1)[0]
    assert "export PYTHONPATH=" in dt
    assert "desk.paper" in text and "risk_engine" in text


def test_f_preflight_fails_when_desk_paper_missing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path_dir = tmp_path / "nodebin"
    path_dir.mkdir()
    home.mkdir()
    _write_exec(path_dir / "node", "#!/bin/sh\nexit 0\n")
    fake_py = tmp_path / "legacy.py"
    _write_exec(
        fake_py,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys
            if len(sys.argv) >= 2 and sys.argv[1] == "-V":
                print("Python 3.9.6")
                raise SystemExit(0)
            code = sys.argv[2] if len(sys.argv) >= 3 and sys.argv[1] == "-c" else ""
            if "desk.paper" in code or "risk_engine" in code:
                mod = "risk_engine" if "risk_engine" in code else "desk.paper"
                print("ModuleNotFoundError: No module named '%s'" % (mod.split(".", 1)[0]), file=sys.stderr)
                raise SystemExit(1)
            raise SystemExit(0)
            """
        ),
    )
    proc = _source(
        tmp_path,
        "preflight",
        env={
            "HOME": str(home),
            "PATH": f"{path_dir}:/usr/bin:/bin",
            "AAD_PY": str(fake_py),
            "AAD_V2_PY": str(tmp_path / "no-v2"),
        },
    )
    blob = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "cannot import desk.paper" in blob
    assert "No module named 'desk'" in blob or "No module named 'risk_engine'" in blob
    assert "preflight FAILED" in blob


def test_f_preflight_fails_only_on_legacy_blockers(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path_dir = tmp_path / "nodebin"
    path_dir.mkdir()
    home.mkdir()
    _write_exec(path_dir / "node", "#!/bin/sh\nexit 0\n")
    missing_py = tmp_path / "no-such-python"
    proc = _source(
        tmp_path,
        "preflight",
        env={
            "HOME": str(home),
            "PATH": f"{path_dir}:/usr/bin:/bin",
            "AAD_PY": str(missing_py),
            "AAD_V2_PY": str(tmp_path / "no-v2"),
        },
    )
    assert proc.returncode != 0
    assert "legacy .venv python missing" in proc.stderr


def test_f_preflight_token_presence_does_not_print_token(tmp_path: Path) -> None:
    envf = REPO / ".env"
    # Never read or echo a real token. Build a private fake root instead.
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    # scan_repo allows the your_* placeholder form; never embed a long fake token in source.
    (fake_root / ".env").write_text(
        "DHAN_CLIENT_ID=your_client_id\nDHAN_ACCESS_TOKEN=your_access_token\n",
        encoding="utf-8",
    )
    (fake_root / "apps" / "api" / "src").mkdir(parents=True)
    (fake_root / "apps" / "web" / "node_modules" / ".bin").mkdir(parents=True)
    (fake_root / ".venv" / "bin").mkdir(parents=True)
    _write_exec(
        fake_root / ".venv" / "bin" / "python",
        "#!/usr/bin/env python3\nimport sys\nprint('Python 3.9.6')\nsys.exit(0)\n",
    )
    home = tmp_path / "home"
    nodebin = tmp_path / "nodebin"
    nodebin.mkdir()
    home.mkdir()
    _write_exec(nodebin / "node", "#!/bin/sh\nexit 0\n")
    recon = tmp_path / "recon"
    recon.mkdir()
    script = f"source '{DESK}'\npreflight\n"
    proc = subprocess.run(
        ["/usr/bin/bash", "-c", script],
        cwd=fake_root,
        env={
            **os.environ,
            "DESK_SH_SOURCED": "1",
            "AAD_ROOT": str(fake_root),
            "AAD_RECON": str(recon),
            "AAD_TAPE_V2": str(tmp_path / "tape"),
            "HOME": str(home),
            "PATH": f"{nodebin}:/usr/bin:/bin",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    blob = proc.stdout + proc.stderr
    assert "your_access_token" not in blob
    assert "your_client_id" not in blob
    assert "Dhan token file" in blob
    assert "values not printed" in blob
    assert envf.name == ".env"  # keep the real path unused


def test_f_morning_and_website_call_preflight() -> None:
    text = DESK.read_text(encoding="utf-8")
    morning = text.split("morning|start)", 1)[1].split("close|night|nightly)", 1)[0]
    website = text.split("\n  website)", 1)[1].split("recorder-start)", 1)[0]
    assert "preflight" in morning
    assert "preflight" in website
    assert "v2_start" not in morning
    assert "recorder_start" not in morning


def test_f_preflight_missing_v2_is_warning_only(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path_dir = tmp_path / "nodebin"
    path_dir.mkdir()
    home.mkdir()
    _write_exec(path_dir / "node", "#!/bin/sh\nexit 0\n")
    fake_py = tmp_path / "legacy.py"
    _write_exec(
        fake_py,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys
            if len(sys.argv) >= 2 and sys.argv[1] == "-V":
                print("Python 3.9.6")
                raise SystemExit(0)
            raise SystemExit(0)
            """
        ),
    )
    proc = _source(
        tmp_path,
        "preflight",
        env={
            "HOME": str(home),
            "PATH": f"{path_dir}:/usr/bin:/bin",
            "AAD_PY": str(fake_py),
            "AAD_V2_PY": str(tmp_path / "no-v2"),
        },
    )
    blob = proc.stdout + proc.stderr
    assert proc.returncode == 0, blob
    assert "WARNING: v2 python missing" in blob
    assert "legacy desk can start" in blob
