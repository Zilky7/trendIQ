import { expect, test } from "@playwright/test";

const reportFixture = {
  symbol: "MU",
  model_version: "research-v1",
  report_source: "rules",
  source_label: "deterministic E2E fixture",
  event_coverage: [{ provider: "news", state: "unavailable", detail: "fixture has no news coverage", events: [] }],
  attributions: [
    { kind: "earnings", weight: 60, confidence: "high", evidence: { kind: "earnings", occurred_on: "2025-01-15", title: "Fixture earnings", url: "https://example.test/earnings" } },
    { kind: "unexplained", weight: 40, confidence: "medium", evidence: null },
  ],
  technical_context: { close: 100, sma_50: 95, sma_200: 90, rsi_14: 61.2, atr_14: 3.2, distance_from_20d_high: -1.5, average_volume_20: 1000000, latest_volume: 1200000, volume_ratio: 1.2 },
  summary: "偏多，等待回踩确认",
  reasoning_steps: ["价格高于 50 日和 200 日均线。"],
  risks: ["财报前请控制风险。"],
  execution_plan: { side: "long", entry: 99, stop_loss: 96, take_profit_1: 105, take_profit_2: 110, take_profit_3: 115, invalidation: "收盘跌破 $96.00" },
  disclaimer: "仅供研究参考，不构成投资建议",
  chart_bars: [
    { date: "2025-01-13", open: 96, high: 100, low: 95, close: 99, volume: 900000, sma_50: 94, sma_200: 89 },
    { date: "2025-01-14", open: 99, high: 102, low: 98, close: 100, volume: 1200000, sma_50: 95, sma_200: 90 },
  ],
};

test("MU research report renders deterministic evidence in a fixed chart/report workspace", async ({ page }) => {
  await page.route("**/api/reports/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(reportFixture) });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "MU · 偏多，等待回踩确认" })).toBeVisible();
  await page.getByLabel("股票代码").fill("MU");
  await page.getByRole("button", { name: "分析图表" }).click();

  await expect(page.getByLabel("price chart")).toBeVisible();
  await expect(page.getByText("RSI(14)")).toBeVisible();
  await expect(page.getByText("未解释部分")).toBeVisible();
  await expect(page.getByText("仅供研究参考，不构成投资建议")).toBeVisible();
  await expect(page.getByLabel("price chart")).toHaveCSS("overflow", "hidden");
  await expect(page.getByLabel("analysis report")).toHaveCSS("overflow-y", "auto");
});
