import { render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

const chart = vi.hoisted(() => {
  const series = { setData: vi.fn(), createPriceLine: vi.fn() };
  return { addSeries: vi.fn(() => series), remove: vi.fn(), timeScale: () => ({ fitContent: vi.fn() }), series };
});

const createChart = vi.hoisted(() => vi.fn(() => chart));

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: "candlestick",
  ColorType: { Solid: "solid" },
  HistogramSeries: "histogram",
  LineSeries: "line",
  createChart,
}));

import { PriceChart } from "../components/PriceChart";

it("draws populated OHLCV bars with moving averages and price levels", async () => {
  render(<PriceChart symbol="MU" support={94} resistance={108} bars={[{
    date: "2025-01-02", open: 100, high: 105, low: 98, close: 103, volume: 1500, sma_50: 95, sma_200: 90,
  }]} />);

  expect(screen.queryByText("MU 暂无可绘制的 OHLCV 数据")).not.toBeInTheDocument();
  await waitFor(() => expect(createChart).toHaveBeenCalled());
  expect(chart.addSeries).toHaveBeenCalledTimes(4);
  expect(chart.series.setData).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ open: 100, close: 103 })]));
  expect(chart.series.createPriceLine).toHaveBeenCalledWith(expect.objectContaining({ price: 94, title: "Support" }));
  expect(chart.series.createPriceLine).toHaveBeenCalledWith(expect.objectContaining({ price: 108, title: "Resistance" }));
});
