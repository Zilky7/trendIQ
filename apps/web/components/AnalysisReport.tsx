import type { AnalysisReportData, Attribution, ExecutionPlan, TechnicalContext } from "../lib/types";

interface AnalysisReportProps {
  report?: AnalysisReportData;
  loading: boolean;
  error?: string;
}

const money = (value: number | null) => (value === null ? "—" : `$${value.toFixed(2)}`);
const number = (value: number) => value.toLocaleString("en-US", { maximumFractionDigits: 2 });

function Metrics({ context }: { context: TechnicalContext }) {
  const items = [
    ["收盘价", money(context.close)],
    ["50 日均线", money(context.sma_50)],
    ["200 日均线", money(context.sma_200)],
    ["RSI(14)", number(context.rsi_14)],
    ["距 20 日高点", `${context.distance_from_20d_high.toFixed(2)}%`],
    ["ATR(14)", money(context.atr_14)],
  ];
  return <div className="metric-grid">{items.map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>;
}

function AttributionRow({ attribution }: { attribution: Attribution }) {
  const evidence = attribution.evidence;
  const isUnexplained = attribution.kind === "unexplained";
  return <div className="attribution">
    <strong>{isUnexplained ? "未解释部分" : attribution.kind}</strong>
    <div className="muted">影响权重 {number(attribution.weight)}% · 置信度 {attribution.confidence}</div>
    {isUnexplained ? <div className="muted">未被当前事件覆盖解释，不能据此推断新闻原因。</div> : evidence ? <div><a className="evidence-link" href={evidence.url} target="_blank" rel="noreferrer">{evidence.title}</a><div className="muted">{evidence.occurred_on}</div></div> : <div className="muted">无可链接的事件证据</div>}
  </div>;
}

function Plan({ plan }: { plan: ExecutionPlan }) {
  const items = [["方向", plan.side === "long" ? "偏多" : "观望"], ["入场", money(plan.entry)], ["止损", money(plan.stop_loss)], ["TP1", money(plan.take_profit_1)], ["TP2", money(plan.take_profit_2)], ["TP3", money(plan.take_profit_3)]];
  return <><div className="plan-grid">{items.map(([label, value]) => <div className="plan-item" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><p className="risk">失效条件：{plan.invalidation}</p></>;
}

export function AnalysisReport({ report, loading, error }: AnalysisReportProps) {
  if (loading) return <div className="report-card" aria-live="polite">正在生成分析报告…</div>;
  if (error) return <div className="report-card error" role="alert">{error}</div>;
  if (!report) return <div className="report-card muted">输入股票代码后开始分析。</div>;

  return <>
    <section className="report-card"><p className="source">数据源：{report.source_label} · 模型：{report.model_version} · {report.report_source === "ai" ? "AI 辅助解释" : "规则报告"}</p><h1>{report.symbol} · {report.summary}</h1></section>
    <section className="report-card"><h2>1. 日线技术背景</h2><Metrics context={report.technical_context} /></section>
    <section className="report-card"><h2>2. 分析过程</h2><ol>{report.reasoning_steps.map((step, index) => <li key={`${index}-${step}`}>{step}</li>)}</ol></section>
    <section className="report-card"><h2>3. 事件归因</h2>{report.attributions.length ? report.attributions.map((item) => <AttributionRow key={`${item.kind}-${item.weight}`} attribution={item} />) : <p className="muted">未发现可量化事件归因；不会虚构新闻原因。</p>}</section>
    <section className="report-card"><h2>4. 事件覆盖与风险</h2>{report.event_coverage.map((coverage) => <div key={coverage.provider}><strong>{coverage.provider}</strong><p className="muted">{coverage.state}：{coverage.detail}</p></div>)}<ul>{report.risks.map((risk) => <li className="risk" key={risk}>{risk}</li>)}</ul></section>
    <section className="report-card"><h2>5. 执行计划</h2><Plan plan={report.execution_plan} /></section>
    <footer className="muted">{report.disclaimer}</footer>
  </>;
}
