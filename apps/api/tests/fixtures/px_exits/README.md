# TEST FIXTURE — not real data

Built for the desk exit-labels page from the 2026-10-19 shadow-overlays bundle (`DEPLOY/logs/sample_exit_status_and_shadow.json`,
`DEPLOY/tests/fixtures/oct19_1308_paper_extra.json`) and the real Oct 19 `live_exits.json` schema (ORB_A stop_floor 729.85 /
trail_gap 0.15). Day relabelled 2026-10-21. The FADING row (PX_IB_15), the error row (PX_VWAP_CONT), the second shadow line
(null TS leg, DR would-skip) and the regime values are made up to cover every display state. Lines carry `"fixture": true`;
the recon json carries a `fixture` note. Never copy into `data/`.
