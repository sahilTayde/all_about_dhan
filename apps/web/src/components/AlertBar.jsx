import { useEffect, useMemo, useRef, useState } from "react";

const DISMISS_KEY = "desk.alerts.dismissed.v1";
const ALARM_KEY = "desk.alerts.alarm.v1";
const LOUD = new Set(["CRITICAL", "EMERGENCY"]);
const RANK = { EMERGENCY: 0, CRITICAL: 1, WARNING: 2, INFO: 3 };

let audio = null;

function beep() {
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.32].forEach((at) => {
      const osc = audio.createOscillator();
      const gain = audio.createGain();
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.18, audio.currentTime + at);
      gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + at + 0.25);
      osc.connect(gain).connect(audio.destination);
      osc.start(audio.currentTime + at);
      osc.stop(audio.currentTime + at + 0.26);
    });
  } catch {
    /* no audio device */
  }
}

function readSet(key) {
  try {
    return new Set(JSON.parse(localStorage.getItem(key) || "[]"));
  } catch {
    return new Set();
  }
}

/** Connection alerts the browser can see that the server cannot report about itself. */
function connAlerts(conn) {
  if (conn === "offline") {
    return [{ id: "conn:offline", severity: "CRITICAL", title: "Website lost the API", detail: "Showing the static mock board. Start the API: ./scripts/desk.sh website", source: "browser" }];
  }
  if (conn === "polling") {
    return [{ id: "conn:polling", severity: "WARNING", title: "Live push dropped", detail: "Falling back to one poll every 2 s until the stream reconnects.", source: "browser" }];
  }
  return [];
}

export function AlertBar({ alerts, conn }) {
  const [dismissed, setDismissed] = useState(() => readSet(DISMISS_KEY));
  const [alarm, setAlarm] = useState(() => localStorage.getItem(ALARM_KEY) === "on");
  const [open, setOpen] = useState(false);
  const notified = useRef(new Set());

  const active = useMemo(
    () =>
      [...connAlerts(conn), ...(alerts || [])]
        .filter((a) => a.severity !== "INFO" && !dismissed.has(a.id))
        .sort((a, b) => (RANK[a.severity] ?? 9) - (RANK[b.severity] ?? 9)),
    [alerts, conn, dismissed],
  );

  useEffect(() => {
    for (const a of active) {
      if (!LOUD.has(a.severity) || notified.current.has(a.id)) continue;
      notified.current.add(a.id);
      if (!alarm) continue;
      beep();
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification(`${a.severity}: ${a.title}`, { body: a.detail || "", tag: a.id });
      }
    }
  }, [active, alarm]);

  function dismiss(id) {
    const next = new Set(dismissed).add(id);
    setDismissed(next);
    localStorage.setItem(DISMISS_KEY, JSON.stringify([...next].slice(-200)));
  }

  async function toggleAlarm() {
    const next = !alarm;
    if (next) {
      beep();
      if ("Notification" in window && Notification.permission === "default") await Notification.requestPermission();
    }
    setAlarm(next);
    localStorage.setItem(ALARM_KEY, next ? "on" : "off");
  }

  const shown = open ? active : active.slice(0, 2);
  const top = active[0]?.severity;
  return (
    <section className={`alert-bar alert-bar--${top ? top.toLowerCase() : "clear"}`} aria-live="assertive" aria-label="Alerts">
      <div className="alert-bar__head">
        <strong>{top ? `${active.length} active alert${active.length > 1 ? "s" : ""}` : "No active alerts"}</strong>
        {active.length > 2 ? (
          <button type="button" className="link-btn" onClick={() => setOpen((v) => !v)}>
            {open ? "show fewer" : `show all ${active.length}`}
          </button>
        ) : null}
        <button type="button" className={`chip-btn${alarm ? " is-on" : ""}`} onClick={toggleAlarm} aria-pressed={alarm}>
          {alarm ? "Alarm on · sound + notification" : "Enable alarm"}
        </button>
      </div>
      {shown.length ? (
        <ul className="alert-bar__list">
          {shown.map((a) => (
            <li key={a.id}>
              <span className={`sev sev--${a.severity.toLowerCase()}`}>{a.severity}</span>
              <strong>{a.title}</strong>
              <span className="alert-bar__detail">{a.detail}</span>
              <button type="button" className="icon-btn" aria-label={`Dismiss ${a.title}`} onClick={() => dismiss(a.id)}>
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
