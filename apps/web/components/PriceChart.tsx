"use client";

import { CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, type CandlestickData, type IChartApi, type LineData, type Time } from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { ChartBar } from "../lib/types";

interface PriceChartProps {
  bars?: ChartBar[];
  symbol: string;
  support?: number | null;
  resistance?: number | null;
}

/** A small adapter boundary keeps the chart library out of report rendering and tests. */
export function PriceChart({ bars = [], symbol, support, resistance }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || bars.length === 0) return;

    const chart: IChartApi = createChart(container, {
      autoSize: true,
      height: container.clientHeight,
      layout: { background: { type: ColorType.Solid, color: "#0b1220" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
    });
    const candles = chart.addSeries(CandlestickSeries, { upColor: "#22c55e", downColor: "#fb7185", borderVisible: false, wickUpColor: "#22c55e", wickDownColor: "#fb7185" });
    candles.setData(bars.map((bar) => ({ time: bar.date as Time, open: bar.open, high: bar.high, low: bar.low, close: bar.close })) as CandlestickData<Time>[]);

    const addAverage = (color: string, key: "sma_50" | "sma_200") => {
      const points = bars.flatMap((bar) => (bar[key] === null ? [] : [{ time: bar.date as Time, value: bar[key] }]));
      if (points.length > 0) chart.addSeries(LineSeries, { color, lineWidth: 2 }).setData(points as LineData<Time>[]);
    };
    addAverage("#38bdf8", "sma_50");
    addAverage("#a78bfa", "sma_200");
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "" });
    volume.setData(bars.map((bar) => ({ time: bar.date as Time, value: bar.volume, color: bar.close >= bar.open ? "#22c55e80" : "#fb718580" })));
    if (support !== null && support !== undefined) candles.createPriceLine({ price: support, color: "#fbbf24", lineStyle: 2, axisLabelVisible: true, title: "Support" });
    if (resistance !== null && resistance !== undefined) candles.createPriceLine({ price: resistance, color: "#fb7185", lineStyle: 2, axisLabelVisible: true, title: "Resistance" });
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [bars]);

  return (
    <><p className="source">支撑 {support === null || support === undefined ? "—" : `$${support.toFixed(2)}`} · 压力 {resistance === null || resistance === undefined ? "—" : `$${resistance.toFixed(2)}`}</p><div className="chart-shell">
      <div ref={containerRef} className="chart-canvas" data-testid="lightweight-chart">
        {bars.length === 0 && <div className="chart-empty">{symbol} 暂无可绘制的 OHLCV 数据</div>}
      </div>
    </div></>
  );
}
