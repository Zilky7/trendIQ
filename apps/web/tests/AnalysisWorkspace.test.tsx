import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const chart = vi.hoisted(() => ({
  addSeries: vi.fn(() => ({ setData: vi.fn(), createPriceLine: vi.fn() })),
  remove: vi.fn(),
  timeScale: () => ({ fitContent: vi.fn() }),
}));

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: "candlestick",
  ColorType: { Solid: "solid" },
  HistogramSeries: "histogram",
  LineSeries: "line",
  createChart: vi.fn(() => chart),
}));

import { AnalysisWorkspace } from "../components/AnalysisWorkspace";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("keeps the chart region visible beside the independently scrollable report", () => {
  render(<AnalysisWorkspace initialSymbol="MU" />);

  expect(screen.getByLabelText("price chart")).toBeVisible();
  expect(screen.getByLabelText("analysis report")).toHaveClass("overflow-y-auto");
});

it("shows a loading state while the report is requested", () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

  render(<AnalysisWorkspace initialSymbol="MU" />);

  expect(screen.getByText("正在生成分析报告…")).toBeVisible();
});

it("shows an actionable error when the report request fails", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("unavailable", { status: 502 })));

  render(<AnalysisWorkspace initialSymbol="MU" />);

  expect(await screen.findByText("无法获取 MU 的分析报告。请稍后重试。")).toBeVisible();
});

it("retries the current symbol after a failed request", async () => {
  const failedFetch = vi.fn().mockResolvedValue(new Response("unavailable", { status: 502 }));
  vi.stubGlobal("fetch", failedFetch);

  render(<AnalysisWorkspace initialSymbol="MU" />);
  await screen.findByRole("alert");
  fireEvent.submit(screen.getByRole("button", { name: "分析图表" }).closest("form")!);

  await waitFor(() => expect(failedFetch).toHaveBeenCalledTimes(2));
});

it("never renders an AI credential even when a report is displayed", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        symbol: "MU",
        model_version: "research-v1",
        report_source: "rules",
        source_label: "Yahoo Finance",
        event_coverage: [],
        attributions: [],
        technical_context: {
          close: 100,
          sma_50: 90,
          sma_200: 80,
          rsi_14: 55,
          atr_14: 4,
          distance_from_20d_high: -2,
          average_volume_20: 10,
          latest_volume: 12,
          volume_ratio: 1.2,
        },
        chart_bars: [{
          date: "2025-01-02", open: 98, high: 101, low: 97, close: 100, volume: 1000000, sma_50: 95, sma_200: 90,
        }],
        summary: "测试摘要",
        reasoning_steps: ["趋势确认"],
        risks: ["事件风险"],
        execution_plan: {
          side: "long",
          entry: 100,
          stop_loss: 94,
          take_profit_1: 108,
          take_profit_2: 112,
          take_profit_3: 116,
          invalidation: "跌破止损",
        },
        disclaimer: "仅供研究参考，不构成投资建议",
        ai_api_key: "should-not-render",
      }),
    ),
  );

  render(<AnalysisWorkspace initialSymbol="MU" />);

  await waitFor(() => expect(screen.getByRole("heading", { name: /测试摘要/ })).toBeVisible());
  expect(screen.getByText("支撑 $94.00 · 压力 $108.00")).toBeVisible();
  expect(screen.queryByText("should-not-render")).not.toBeInTheDocument();
});
