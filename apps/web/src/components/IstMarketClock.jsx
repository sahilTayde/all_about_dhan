import { useEffect, useState } from "react";

const IST = "Asia/Kolkata";
const BAR_MS = 5 * 60 * 1000;

function partsFromIst(date) {
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const bag = {};
  for (const p of fmt.formatToParts(date)) {
    if (p.type !== "literal") bag[p.type] = p.value;
  }
  return bag;
}

function istMs(date) {
  const s = date.toLocaleString("en-US", { timeZone: IST });
  return new Date(s).getTime();
}

function nextFiveMin(date) {
  const local = istMs(date);
  const aligned = Math.floor(local / BAR_MS) * BAR_MS;
  const next = aligned + BAR_MS;
  return { remainMs: Math.max(0, next - local), nextMs: next };
}

function pad(n) {
  return String(n).padStart(2, "0");
}

export function IstMarketClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const p = partsFromIst(now);
  const { remainMs } = nextFiveMin(now);
  const totalSec = Math.floor(remainMs / 1000);
  const mm = Math.floor(totalSec / 60);
  const ss = totalSec % 60;
  const clock = `${p.hour}:${p.minute}:${p.second}`;
  const date = `${p.day} ${p.month} ${p.year}`;

  return (
    <div className="ist-clock" aria-live="polite">
      <div className="ist-clock__time">
        <span className="ist-clock__label">India (IST)</span>
        <strong className="ist-clock__digits">{clock}</strong>
        <span className="ist-clock__date">{date}</span>
      </div>
      <div className="ist-clock__bar">
        <span className="ist-clock__label">5-min bar</span>
        <strong className="ist-clock__digits ist-clock__digits--count">
          {pad(mm)}:{pad(ss)}
        </strong>
        <span className="ist-clock__date">to next 09:15 / 09:20… boundary</span>
      </div>
    </div>
  );
}
