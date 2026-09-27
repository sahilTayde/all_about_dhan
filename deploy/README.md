# V2 deploy runbook (paper only)

No live orders. Default compose profile is **replay** and needs no credentials.

| Action | Command |
|---|---|
| Start (laptop / CI) | `docker compose -f deploy/docker/compose.yaml up --build` |
| Stop | `docker compose -f deploy/docker/compose.yaml down` |
| Deploy | `deploy/scripts/deploy.sh <git-sha>` — refuses 09:00–15:35 IST unless `--emergency` |
| Rollback | same script; auto-rollback if `ENGINE_STATUS READY` never arrives |
| Backup | `deploy/scripts/backup.sh` (restic if `RESTIC_REPOSITORY` is set on the host) |
| Restore | `deploy/scripts/restore.sh <snapshot>` — must reproduce `output_hash` |
| Breaker | `python -m runtime reset-breaker <service>` after `RESTART_LOOP` |
| Health | `python -m runtime health --state-dir …` |
| Flatten | out-of-band flatten is V2-11; do not place broker orders |

VPS: `aad.service` runs compose + `compose.vps.yaml`. Firewall 443 only. Token refresh is VERIFY (V2-12/V2-15).
