import { useEffect, useRef } from "react";
import { createChart, ColorType, LineStyle } from "lightweight-charts";
import { formatLevel, sideCopy } from "../lib/status.js";

/**
 * MT5-like underlying index path (MOCK/PAPER).
 * Premium entry/SL/target stay on the ticket — only index-unit overlays plot here.
 */
export function IndexChart({ chart, signal, status }) {
  const wrapRef = useRef(null);
  const chartRef = useRef(null);

  const bars = chart?.bars || [];
  const overlays = chart?.overlays || {};
  const side = sideCopy(signal?.side);
  const label = chart?.label || "MOCK";
  const note =
    chart?.note ||
    "Underlying index path — MOCK. Premium levels stay on the ticket. Not a fill. Not advice.";

  useEffect(() => {
    if (!wrapRef.current || bars.length === 0) return undefined;

    const chartApi = createChart(wrapRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b97a5",
        fontFamily:
          '"Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif',
      },
      grid: {
        vertLines: { color: "rgba(42, 51, 61, 0.55)" },
        horzLines: { color: "rgba(42, 51, 61, 0.55)" },
      },
      rightPriceScale: { borderColor: "#2a333d" },
      timeScale: {
        borderColor: "#2a333d",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: "rgba(201, 162, 39, 0.35)", labelBackgroundColor: "#1b222c" },
        horzLine: { color: "rgba(201, 162, 39, 0.35)", labelBackgroundColor: "#1b222c" },
      },
      width: wrapRef.current.clientWidth,
      height: 280,
    });

    const series = chartApi.addAreaSeries({
      lineColor: "#5b9cff",
      topColor: "rgba(91, 156, 255, 0.22)",
      bottomColor: "rgba(91, 156, 255, 0.02)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    const data = bars.map((b) => ({
      time: b.t,
      value: Number(b.v),
    }));
    series.setData(data);

    const markers = [];
    if (overlays.signalAt && overlays.signalPrice != null) {
      markers.push({
        time: overlays.signalAt,
        position: side.kind === "pe" ? "aboveBar" : "belowBar",
        color: side.kind === "pe" ? "#e06b74" : "#3dcc8c",
        shape: side.kind === "pe" ? "arrowDown" : "arrowUp",
        text: `${side.option} BUY`,
      });
    }
    if (overlays.exitAt && overlays.exitPrice != null) {
      markers.push({
        time: overlays.exitAt,
        position: "aboveBar",
        color: "#c9a227",
        shape: "circle",
        text: overlays.exitLabel || "EXIT",
      });
    }
    if (markers.length) series.setMarkers(markers);

    const lineSpecs = [
      { key: "entrySpot", color: "#5b9cff", title: "Entry (index)" },
      { key: "stopSpot", color: "#e06b74", title: "Stop (index)" },
      { key: "targetSpot", color: "#3dcc8c", title: "Target (index)" },
    ];
    for (const spec of lineSpecs) {
      const price = overlays[spec.key];
      if (price == null || price === "") continue;
      series.createPriceLine({
        price: Number(price),
        color: spec.color,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: spec.title,
      });
    }

    chartApi.timeScale().fitContent();
    chartRef.current = chartApi;

    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w) chartApi.applyOptions({ width: w });
    });
    ro.observe(wrapRef.current);

    return () => {
      ro.disconnect();
      chartApi.remove();
      chartRef.current = null;
    };
  }, [bars, overlays, side.kind, side.option]);

  if (!bars.length) {
    return (
      <section className="panel index-chart index-chart--empty" aria-labelledby="chart-heading">
        <div className="panel__head">
          <h2 id="chart-heading">Index path</h2>
          <span className="source-pill">{label}</span>
        </div>
        <p className="muted">No chart bars in this MOCK payload.</p>
      </section>
    );
  }

  return (
    <section className="panel index-chart" aria-labelledby="chart-heading">
      <div className="panel__head">
        <h2 id="chart-heading">
          {signal?.underlying || "Index"} · underlying path
        </h2>
        <span className="source-pill" title="Mock / paper path only">
          {label}
        </span>
      </div>
      <p className="muted index-chart__note">{note}</p>
      <div className="index-chart__meta muted">
        <span>Status: {status}</span>
        {overlays.entrySpot != null && (
          <span>Index entry {formatLevel(overlays.entrySpot)}</span>
        )}
        {overlays.stopSpot != null && (
          <span>Index SL {formatLevel(overlays.stopSpot)}</span>
        )}
        {overlays.targetSpot != null && (
          <span>Index TP {formatLevel(overlays.targetSpot)}</span>
        )}
      </div>
      <div ref={wrapRef} className="index-chart__canvas" role="img" aria-label="Underlying index chart" />
    </section>
  );
}
