import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const mockedChart = vi.hoisted(() => {
  const state = { series: [] as Array<{ setData: ReturnType<typeof vi.fn>; createPriceLine: ReturnType<typeof vi.fn> }> };
  const chart = {
    addSeries: vi.fn(() => {
      const series = { setData: vi.fn(), createPriceLine: vi.fn() };
      state.series.push(series);
      return series;
    }),
    remove: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
  };
  return { chart, state };
});

const createChart = vi.hoisted(() => vi.fn(() => mockedChart.chart));

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: "candlestick",
  ColorType: { Solid: "solid" },
  HistogramSeries: "histogram",
  LineSeries: "line",
  createChart,
}));

import { PriceChart } from "../components/PriceChart";

beforeEach(() => {
  createChart.mockClear();
  mockedChart.chart.addSeries.mockClear();
  mockedChart.chart.remove.mockClear();
  mockedChart.state.series.length = 0;
});

it("maps backend OHLCV and moving-average values into chart series and cleans up on update", async () => {
  const bars = [
    { date: "2025-01-02", open: 100, high: 105, low: 98, close: 103, volume: 1500, sma_50: null, sma_200: 90 },
    { date: "2025-01-03", open: 103, high: 107, low: 101, close: 102, volume: 2300, sma_50: 96, sma_200: 91 },
  ];
  const { rerender, unmount } = render(<PriceChart symbol="MU" support={94} resistance={108} bars={bars} />);

  expect(screen.queryByText("MU 暂无可绘制的 OHLCV 数据")).not.toBeInTheDocument();
  await waitFor(() => expect(createChart).toHaveBeenCalledTimes(1));
  expect(mockedChart.chart.addSeries).toHaveBeenCalledTimes(4);
  expect(mockedChart.state.series[0].setData).toHaveBeenCalledWith([
    { time: "2025-01-02", open: 100, high: 105, low: 98, close: 103 },
    { time: "2025-01-03", open: 103, high: 107, low: 101, close: 102 },
  ]);
  expect(mockedChart.state.series[1].setData).toHaveBeenCalledWith([{ time: "2025-01-03", value: 96 }]);
  expect(mockedChart.state.series[2].setData).toHaveBeenCalledWith([
    { time: "2025-01-02", value: 90 },
    { time: "2025-01-03", value: 91 },
  ]);
  expect(mockedChart.state.series[3].setData).toHaveBeenCalledWith([
    { time: "2025-01-02", value: 1500, color: "#22c55e80" },
    { time: "2025-01-03", value: 2300, color: "#fb718580" },
  ]);
  expect(mockedChart.state.series[0].createPriceLine).toHaveBeenCalledWith(expect.objectContaining({ price: 94, title: "Support" }));
  expect(mockedChart.state.series[0].createPriceLine).toHaveBeenCalledWith(expect.objectContaining({ price: 108, title: "Resistance" }));

  rerender(<PriceChart symbol="MU" support={94} resistance={108} bars={[...bars, { date: "2025-01-06", open: 102, high: 110, low: 100, close: 109, volume: 3000, sma_50: 97, sma_200: 92 }]} />);
  await waitFor(() => expect(createChart).toHaveBeenCalledTimes(2));
  expect(mockedChart.chart.remove).toHaveBeenCalledTimes(1);

  unmount();
  expect(mockedChart.chart.remove).toHaveBeenCalledTimes(2);
});
