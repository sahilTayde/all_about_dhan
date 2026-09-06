import { useEffect, useState } from "react";
import { apiMode, fetchPaperDesk } from "./lib/signalApi.js";
import { fieldsFromSignal } from "./lib/status.js";
import { Header } from "./components/Header.jsx";
import { UnderlyingPicker } from "./components/UnderlyingPicker.jsx";
import { SignalBadge } from "./components/SignalBadge.jsx";
import { StagedSignal } from "./components/StagedSignal.jsx";
import { TradeFields } from "./components/TradeFields.jsx";
import { TookTrade } from "./components/TookTrade.jsx";
import { SystemOutcome } from "./components/SystemOutcome.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { StatusLights } from "./components/StatusLights.jsx";
import { FactorChecklist } from "./components/FactorChecklist.jsx";

const EMPTY_FILL = { lots: "", spot: "", pnl: "" };

export function InternalDesk() {
  const [desk, setDesk] = useState(null);
  const [error, setError] = useState(null);
  const [underlying, setUnderlying] = useState("NIFTY");
  const [fields, setFields] = useState(fieldsFromSignal(null));
  const [tookTrade, setTookTrade] = useState(null);
  const [userFill, setUserFill] = useState(EMPTY_FILL);

  useEffect(() => {
    let cancelled = false;
    fetchPaperDesk()
      .then((data) => {
        if (cancelled) return;
        setDesk(data);
        const first = data.underlyings?.[0] || "NIFTY";
        setUnderlying(first);
        setFields(fieldsFromSignal(data.signals?.[first]));
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleUnderlying(next) {
    setUnderlying(next);
    setFields(fieldsFromSignal(desk?.signals?.[next]));
    setTookTrade(null);
    setUserFill(EMPTY_FILL);
  }

  const signal = desk?.signals?.[underlying];
  const sourceLabel = apiMode() === "remote" ? "API" : "MOCK";

  if (error) {
    return (
      <div className="shell">
        <Header
          title="Internal desk"
          kicker="engineering"
          sub="Research view — not the customer desk"
          sourceLabel="ERROR"
        />
        <p className="error-banner">{error}</p>
      </div>
    );
  }

  if (!desk || !signal) {
    return (
      <div className="shell">
        <Header
          title="Internal desk"
          kicker="engineering"
          sub="Research view — not the customer desk"
          sourceLabel={sourceLabel}
        />
        <p className="muted">Loading internal desk…</p>
      </div>
    );
  }

  return (
    <div className="shell shell--internal">
      <p className="internal-banner" role="status">
        Internal research view. Indicator lights stay off the customer desk.{" "}
        <a href="/">Back to customer desk</a>
      </p>
      <Header
        title="Internal desk"
        kicker="engineering"
        sub="Staged honesty, factor checklist, indicator lights"
        sourceLabel={sourceLabel}
      />

      <div className="desk-grid">
        <UnderlyingPicker
          underlyings={desk.underlyings}
          value={underlying}
          onChange={handleUnderlying}
        />
        <SignalBadge side={signal.side} />
        <StagedSignal staged={signal.staged} lifecycle={signal.lifecycle} />
        <TradeFields
          values={fields}
          onChange={(key, value) =>
            setFields((prev) => ({ ...prev, [key]: value }))
          }
        />
        <TookTrade
          value={tookTrade}
          onChange={setTookTrade}
          fill={userFill}
          onFillChange={(key, value) =>
            setUserFill((prev) => ({ ...prev, [key]: value }))
          }
        />
        <SystemOutcome
          tookTrade={tookTrade}
          outcome={signal.systemOutcome}
          lifecycle={signal.lifecycle}
          userFill={userFill}
        />
        <section className="panel" aria-labelledby="internal-lights">
          <h2 id="internal-lights">Engine lights</h2>
          <StatusLights lights={signal.staged?.lights} />
          <FactorChecklist factors={signal.staged?.factors} />
        </section>
      </div>
    </div>
  );
}
