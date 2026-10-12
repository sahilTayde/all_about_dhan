import { useEffect, useState } from "react";
import { NAV_LINKS } from "./AppNav.jsx";
import { RULES, clockPair, healthDots, inr, tone } from "../lib/deskModel.js";

function useNow() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

const fmt = (d, tz, sec) => new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", second: sec ? "2-digit" : undefined, hour12: false }).format(d);

function marketState(d) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kolkata", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(d).map((x) => [x.type, x.value]));
  const m = Number(p.hour) * 60 + Number(p.minute);
  if (p.weekday === "Sat" || p.weekday === "Sun") return { text: "Closed", tone: "grey" };
  if (m >= 555 && m < 930) return { text: "Market open", tone: "green" };
  if (m >= 540 && m < 555) return { text: "Pre-open", tone: "amber" };
  return { text: "Closed", tone: "grey" };
}

/** Terminal top bar: brand, pages, IST clock, market state, status light, desk today, day-loss meter, health dots. */
export function TopBar({ path, light, dd, snap, conn }) {
  const now = useNow();
  const ms = marketState(now);
  const net = dd?.total?.net;
  const used = net == null ? 0 : Math.min(100, Math.max(0, Math.round((Math.min(0, net) / RULES.dayLossInr) * 100)));
  const dots = snap ? healthDots(snap, conn) : [];
  const active = (href) => (href === "/" ? path === "/" : href === "/desk" ? path === "/desk" : path === href || path.startsWith(`${href}/`));
  return (
    <header className="tb" data-testid="topbar">
      <div className="tb__row">
        <a className="tb__brand" href="/desk">all_about_dhan<span>paper desk</span></a>
        <nav className="tb__nav" aria-label="Pages">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} className={active(l.href) ? "is-on" : ""} aria-current={active(l.href) ? "page" : undefined}>{l.label}</a>
          ))}
        </nav>
        <div className="tb__clock" title="India time and your time">
          <strong className="num">{fmt(now, "Asia/Kolkata", true)}</strong><span>IST</span>
          <em className="num">{fmt(now, "America/Chicago")} CT</em>
          <span className={`pill pill--${ms.tone}`}>{ms.text}</span>
        </div>
      </div>
      {dd ? (
        <div className="tb__row tb__row--stats">
          <span className={`light light--${light.tone}`} data-testid="status-light"><i />{light.text}</span>
          <div className="tb__stat" data-testid="desk-today">
            <span>Desk today</span>
            <strong className={`num ${tone(dd.total.net)}`}>{inr(dd.total.net)}</strong>
            <em>{dd.total.n ?? "—"} trades · {dd.total.wins ?? "—"} won · after charges · updated {clockPair(snap?.board?.as_of_ist)}</em>
          </div>
          <div className="tb__meter" data-testid="day-loss-meter" title="Loss used against the day stop">
            <span>Day stop {inr(RULES.dayLossInr)} · losers {dd.losers}/{RULES.maxLosersPerDay}</span>
            <div className="meter"><i className={used >= 100 ? "is-red" : used >= 60 ? "is-amber" : "is-green"} style={{ width: `${used}%` }} /></div>
          </div>
          <div className="tb__dots">
            {dots.map((d) => <span key={d.id} className={`hdot hdot--${d.tone}`} title={`${d.label}: ${d.detail}`}><i />{d.label}</span>)}
          </div>
        </div>
      ) : null}
    </header>
  );
}
