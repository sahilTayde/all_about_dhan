import { useEffect, useRef } from "react";
import { ColorType, createChart } from "lightweight-charts";
import { hasPremiumChart } from "../../lib/tradeMarks.js";

const UP = "#3dcc8c";
const DOWN = "#e06b74";
const MARK = "#5b9cff";

/**
 * Entry / exit (and any recorded path) on a premium chart.
 * No invented ticks. Empty when fewer than two known marks.
 */
export function PremiumChart({ marks, height = 220 }) {
  const ref = useRef(null);
  const ok = hasPremiumChart(marks);

  useEffect(() => {
    if (!ok || !ref.current) return undefined;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b97a5",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(42,51,61,0.45)" },
        horzLines: { color: "rgba(42,51,61,0.45)" },
      },
      rightPriceScale: { borderColor: "#2a333d" },
      timeScale: { borderColor: "#2a333d", timeVisible: true, secondsVisible: true },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addLineSeries({
      color: MARK,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    series.setData(marks.points.map((p) => ({ time: p.time, value: p.value })));
    const colorOf = (id) => (id === "stop" || id === "low" ? DOWN : id === "target" || id === "high" ? UP : "#c9a227");
    for (const line of marks.lines || []) {
      series.createPriceLine({
        price: line.value,
        color: colorOf(line.id),
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: line.label,
      });
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [ok, marks]);

  if (!ok) {
    return (
      <div className="chart-empty" data-testid="premium-chart-empty" role="status">
        No recorded premium path. Entry / exit marks need two timestamps.
      </div>
    );
  }
  return <div ref={ref} className="chart-box premium-chart" style={{ height }} data-testid="premium-chart" role="img" aria-label="Premium path" />;
}
