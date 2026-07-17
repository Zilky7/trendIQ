"use client";

import { FormEvent, useEffect, useState } from "react";

import { AnalysisReport } from "./AnalysisReport";
import { PriceChart } from "./PriceChart";
import type { AnalysisReportData } from "../lib/types";

export function AnalysisWorkspace({ initialSymbol }: { initialSymbol: string }) {
  const [symbol, setSymbol] = useState(initialSymbol.toUpperCase());
  const [activeSymbol, setActiveSymbol] = useState(initialSymbol.toUpperCase());
  const [report, setReport] = useState<AnalysisReportData>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(undefined);
    fetch(`/api/reports/${encodeURIComponent(activeSymbol)}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("report request failed");
        return response.json() as Promise<AnalysisReportData>;
      })
      .then((data) => setReport(data))
      .catch((requestError: unknown) => {
        if ((requestError as { name?: string }).name !== "AbortError") setError(`无法获取 ${activeSymbol} 的分析报告。请稍后重试。`);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [activeSymbol, requestVersion]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextSymbol = symbol.trim().toUpperCase();
    if (nextSymbol) {
      setActiveSymbol(nextSymbol);
      setRequestVersion((version) => version + 1);
    }
  }

  return <main className="h-screen overflow-hidden">
    <header className="topbar"><strong>TrendIQ Research</strong><form className="symbol-form" onSubmit={submit}><label htmlFor="symbol">股票代码</label><input id="symbol" className="symbol-input" value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} /><button className="primary-button" type="submit" disabled={loading}>{loading ? "分析中" : "分析图表"}</button></form></header>
    <div className="workspace">
      <section aria-label="price chart" className="chart-panel min-h-0"><p className="eyebrow">{activeSymbol} · 日线 K 线 / 成交量 / SMA50 / SMA200</p><PriceChart symbol={activeSymbol} bars={report?.chart_bars} support={report?.execution_plan.stop_loss} resistance={report?.execution_plan.take_profit_1} /></section>
      <aside aria-label="analysis report" className="report-panel min-h-0 overflow-y-auto"><AnalysisReport report={report} loading={loading} error={error} /></aside>
    </div>
  </main>;
}
