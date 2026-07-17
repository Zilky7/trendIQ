export type Confidence = "low" | "medium" | "high";

export interface TechnicalContext {
  close: number;
  sma_50: number;
  sma_200: number;
  rsi_14: number;
  atr_14: number;
  distance_from_20d_high: number;
  average_volume_20: number;
  latest_volume: number;
  volume_ratio: number;
}

export interface EventEvidence {
  kind: string;
  occurred_on: string;
  title: string;
  url: string;
}

export interface Attribution {
  kind: string;
  weight: number;
  confidence: Confidence;
  evidence: EventEvidence | null;
}

export interface EventCoverage {
  provider: string;
  state: "available" | "partial" | "unavailable";
  detail: string;
  events: EventEvidence[];
}

export interface ExecutionPlan {
  side: "long" | "neutral";
  entry: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  take_profit_3: number | null;
  invalidation: string;
}

export interface ChartBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma_50: number | null;
  sma_200: number | null;
}

export interface AnalysisReportData {
  symbol: string;
  model_version: string;
  report_source: "ai" | "rules";
  source_label: string;
  event_coverage: EventCoverage[];
  attributions: Attribution[];
  technical_context: TechnicalContext;
  summary: string;
  reasoning_steps: string[];
  risks: string[];
  execution_plan: ExecutionPlan;
  disclaimer: string;
  chart_bars: ChartBar[];
}
