"""Premium-stop BACKGROUND SHADOWS (PAPER/RESEARCH ONLY; never desk rows, never in desk P&L).
Port of research/lab/2026-10-13_premium_stops/ps_a.py one(), sealed specs:
SHADOW_EP009_P.md (b09d74bf..), SHADOW_B2_P.md (1006e2ac..), SHADOW_VWAPCONT_PE_P.md (daf44776..).
Rules: strike ref = index OPEN of entry minute e=f+dl; K=round(S/50)*50 - sg*off; entry = first option OPEN in [e,e+2] + 0.05;
stop E(1-S) / target E+k*S*E checked on 1-min option CLOSES, stop first; fill = first OPEN in [m+1,m+3] - 0.05;
else TIME at capm=min(capx or em+hold, 915): last close in [capm-3,capm] (>=em) - 0.05. X floored at 0.05.
Live: only bars <= last complete minute are used; anything not yet decidable -> OPEN / PENDING."""
T0 = 0.05
CONFIGS = {   # name: (research strat, off, S, k, dl, PE-only)
    "EP009_P":       ("EP-009",    50,  0.2, 2.0, 1, False),
    "B2_P":          ("B2",        200, 0.3, 2.0, 0, False),
    "VWAPCONT_PE_P": ("VWAP_CONT", 100, 0.3, 1.5, 1, True),
}
def strike(sref, sg, off): return int(round(sref / 50) * 50) - sg * off
def levels(E, S, k): return round(E * (1 - S), 2), round(E + k * S * E, 2)
def _first_open(b, m, last):
    for mm in (m, m + 1, m + 2):
        if mm in b and mm <= last: return mm, b[mm][0]
    return None
def exit_one(b, e_m, S, k, hold=None, capx=None, cap_known=True, last=10**9):
    """b: {minute: (open, close)} for the contract. e_m: entry index minute. capx: fixed cap minute (B2) or None (em+hold).
    cap_known False -> cap not decided yet (B2 path still running): no TIME exit. last: last COMPLETE minute."""
    b = {m: v for m, v in b.items() if m <= last}
    r = _first_open(b, e_m, last)
    if r is None: return dict(status="PENDING_ENTRY" if e_m + 2 > last else "NO_ENTRY")
    em, E = r[0], round(r[1] + T0, 2); st, tg = levels(E, S, k)
    capm = min(capx if capx is not None else em + hold, 915)
    out = dict(em=em, en=E, stop_px=st, target_px=tg, capm=capm if cap_known else None)
    top = min(capm, last) if cap_known else min(915, last)
    for m in range(em, top + 1):
        if m not in b: continue
        c = b[m][1]
        if c <= E * (1 - S): kind = "STOP"
        elif c >= E + k * S * E: kind = "TARGET"
        else: continue
        fo = _first_open(b, m + 1, last)
        if fo is None:
            out.update(status="EXITING" if m + 3 > last else "NO_EXIT", xm=m, kind=kind); return out
        out.update(status="CLOSED", xm=m, kind=kind, fill_m=fo[0], ex=round(max(fo[1] - T0, .05), 2)); return out
    if cap_known and capm <= last:
        p = next(((mm, b[mm][1]) for mm in range(capm, capm - 4, -1) if mm in b and mm >= em), None)
        if p is None: out.update(status="NO_EXIT", xm=capm, kind="TIME"); return out
        out.update(status="CLOSED", xm=capm, kind="TIME", fill_m=p[0], ex=round(max(p[1] - T0, .05), 2)); return out
    lm = max((m for m in b if m >= em), default=None)
    out.update(status="OPEN", mark_m=lm, mark_px=None if lm is None else b[lm][1]); return out
