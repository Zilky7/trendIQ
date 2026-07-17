"""Evidence-backed single-symbol reports with deterministic AI fallback."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
import re
from typing import Any, Mapping

import numpy as np
import pandas as pd

from app.domain.attribution import Attribution, score_attributions
from app.domain.events import EventCoverage
from app.domain.indicators import build_technical_context
from app.domain.models import TechnicalContext
from app.domain.strategy import StrategyFeatures, determine_signal
from app.providers.ai import AIClient
from app.providers.events import EarningsSecEventProvider, MacroEventProvider
from app.providers.market_data import NasdaqHistoricalDataProvider, YFinanceMarketDataProvider


DISCLAIMER = "仅供研究参考，不构成投资建议"
MODEL_VERSION = "research-v1"
_SYMBOL = re.compile(r"^[A-Z0-9.-]{1,10}$")
_CHART_BAR_LIMIT = 260


def validate_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    if not _SYMBOL.fullmatch(normalized):
        raise ValueError("symbol must contain 1-10 uppercase letters, numbers, dots, or hyphens")
    return normalized


def build_symbol_report(
    symbol: str,
    *,
    market_data: YFinanceMarketDataProvider | NasdaqHistoricalDataProvider | None = None,
    ai_client: AIClient | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Build a report from market bars and typed event-provider coverage only."""
    normalized_symbol = validate_symbol(symbol)
    report_date = today or date.today()
    # Three years gives ample history for the required 200-day context without
    # claiming that yfinance is a real-time or authoritative source.
    start = (report_date - timedelta(days=3 * 365)).isoformat()
    end = (report_date + timedelta(days=1)).isoformat()
    bars_result = (market_data or NasdaqHistoricalDataProvider()).daily_bars(
        normalized_symbol, start, end
    )
    context = build_technical_context(bars_result.bars)
    chart_bars = _build_chart_bars(bars_result.bars)
    coverages = _event_coverages(start, end)
    attributions = score_attributions(
        [event for coverage in coverages for event in coverage.events]
    )
    rules_report = _rules_report(
        normalized_symbol,
        context=context,
        chart_bars=chart_bars,
        source_label=bars_result.source_label,
        coverages=coverages,
        attributions=attributions,
    )
    ai_response = (ai_client or AIClient()).generate(_ai_facts(rules_report))
    return _merge_ai_explanation(rules_report, ai_response)


def _event_coverages(start: str, end: str) -> tuple[EventCoverage, ...]:
    return (
        EarningsSecEventProvider().events_between(start, end),
        MacroEventProvider().events_between(start, end),
    )


def _rules_report(
    symbol: str,
    *,
    context: TechnicalContext,
    chart_bars: list[dict[str, Any]],
    source_label: str,
    coverages: tuple[EventCoverage, ...],
    attributions: list[Attribution],
) -> dict[str, Any]:
    features = StrategyFeatures(
        close=context.close,
        sma_50=context.sma_50,
        sma_200=context.sma_200,
        rsi_14=context.rsi_14,
        distance_from_20d_high=context.distance_from_20d_high,
        atr_14=context.atr_14,
        volume_ratio=context.volume_ratio,
    )
    signal = determine_signal(features)
    execution_plan = _execution_plan(context, signal.side)
    return {
        "symbol": symbol,
        "model_version": MODEL_VERSION,
        "report_source": "rules",
        "source_label": source_label,
        "event_coverage": [_coverage_record(item) for item in coverages],
        "attributions": [_attribution_record(item) for item in attributions],
        "technical_context": asdict(context),
        "chart_bars": chart_bars,
        "summary": _rule_summary(context, signal.side),
        "reasoning_steps": _reasoning_steps(context, signal.reason),
        "risks": _risks(context, coverages),
        "execution_plan": execution_plan,
        "disclaimer": DISCLAIMER,
    }


def _build_chart_bars(bars: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize a bounded, validated slice of the same bars used for analysis."""
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not isinstance(bars.index, pd.DatetimeIndex) or not bars.index.is_monotonic_increasing:
        raise ValueError("chart bars require strictly chronological dates")
    if bars.index.has_duplicates:
        raise ValueError("chart bars require strictly chronological dates")

    values = bars.loc[:, required].astype(float)
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError("chart bars require finite OHLCV values")
    if (
        (values["Volume"] < 0).any()
        or (values["Low"] > values[["Open", "Close"]].min(axis=1)).any()
        or (values["High"] < values[["Open", "Close"]].max(axis=1)).any()
        or (values["Low"] > values["High"]).any()
    ):
        raise ValueError("chart bars require finite OHLCV values with valid price bounds")

    sma_50 = values["Close"].rolling(50).mean()
    sma_200 = values["Close"].rolling(200).mean()
    chart_frame = values.assign(sma_50=sma_50, sma_200=sma_200).tail(_CHART_BAR_LIMIT)
    chart_bars: list[dict[str, Any]] = []
    for timestamp, row in chart_frame.iterrows():
        chart_bars.append(
            {
                "date": timestamp.date().isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "sma_50": _finite_or_none(row["sma_50"]),
                "sma_200": _finite_or_none(row["sma_200"]),
            }
        )
    return chart_bars


def _finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _execution_plan(context: TechnicalContext, side: str) -> dict[str, Any]:
    if side != "long" or context.atr_14 <= 0:
        return {
            "side": "neutral",
            "entry": None,
            "stop_loss": None,
            "take_profit_1": None,
            "take_profit_2": None,
            "take_profit_3": None,
            "invalidation": "等待策略条件满足后再制定执行点位",
        }
    close, atr = context.close, context.atr_14
    return {
        "side": "long",
        "entry": round(close, 2),
        "stop_loss": round(close - 1.5 * atr, 2),
        "take_profit_1": round(close + 2 * atr, 2),
        "take_profit_2": round(close + 3 * atr, 2),
        "take_profit_3": round(close + 4 * atr, 2),
        "invalidation": "日线收盘跌破止损价位",
    }


def _rule_summary(context: TechnicalContext, side: str) -> str:
    if side == "long":
        return "趋势与动能规则均满足，执行点位由 ATR 风险单位计算。"
    return "当前未满足冻结策略的全部入场条件，维持观察。"


def _reasoning_steps(context: TechnicalContext, reason: str) -> list[str]:
    return [
        f"收盘价 {context.close:.2f}；50 日均线 {context.sma_50:.2f}；200 日均线 {context.sma_200:.2f}。",
        f"RSI(14) 为 {context.rsi_14:.2f}，距 20 日高点 {context.distance_from_20d_high:.2f}%。",
        f"冻结策略结果：{reason}。",
    ]


def _risks(context: TechnicalContext, coverages: tuple[EventCoverage, ...]) -> list[str]:
    risks = ["未解释部分代表未覆盖或无法由当前证据归因的影响。"]
    if context.rsi_14 >= 70:
        risks.append("RSI(14) 处于或高于超买区域。")
    if any(coverage.state.value != "available" for coverage in coverages):
        risks.append("事件覆盖不完整；没有历史新闻证据时不会推断新闻原因。")
    return risks


def _coverage_record(coverage: EventCoverage) -> dict[str, Any]:
    return {
        "provider": coverage.provider,
        "state": coverage.state.value,
        "detail": coverage.detail,
        "events": [asdict(event) for event in coverage.events],
    }


def _attribution_record(attribution: Attribution) -> dict[str, Any]:
    return {
        "kind": attribution.kind,
        "weight": round(attribution.weight, 2),
        "confidence": attribution.confidence,
        "evidence": asdict(attribution.evidence) if attribution.evidence else None,
    }


def _ai_facts(report: Mapping[str, Any]) -> dict[str, Any]:
    """Supply only existing report facts; credentials never enter this payload."""
    return {
        "technical_context": report["technical_context"],
        "event_coverage": report["event_coverage"],
        "attributions": report["attributions"],
        "summary": report["summary"],
        "reasoning_steps": report["reasoning_steps"],
        "risks": report["risks"],
        "execution_plan": report["execution_plan"],
        "disclaimer": report["disclaimer"],
    }


def _merge_ai_explanation(
    rules_report: dict[str, Any], ai_response: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Use AI prose only if it has the required shape; rules retain all facts."""
    if not ai_response:
        return rules_report
    required = ("summary", "reasoning_steps", "risks", "execution_plan")
    if not all(key in ai_response for key in required):
        return rules_report
    if not isinstance(ai_response["summary"], str):
        return rules_report
    if not isinstance(ai_response["reasoning_steps"], list) or not all(
        isinstance(item, str) for item in ai_response["reasoning_steps"]
    ):
        return rules_report
    if not isinstance(ai_response["risks"], list) or not all(
        isinstance(item, str) for item in ai_response["risks"]
    ):
        return rules_report
    if ai_response["summary"] != rules_report["summary"]:
        return rules_report
    if not set(ai_response["reasoning_steps"]).issubset(rules_report["reasoning_steps"]):
        return rules_report
    if not set(ai_response["risks"]).issubset(rules_report["risks"]):
        return rules_report
    if ai_response["execution_plan"] != rules_report["execution_plan"]:
        return rules_report
    # Execution prices and explanatory prose must remain grounded in the
    # deterministic facts. The model may only select supplied evidence lines.
    merged = dict(rules_report)
    merged.update(
        report_source="ai",
        summary=rules_report["summary"],
        reasoning_steps=ai_response["reasoning_steps"],
        risks=ai_response["risks"],
    )
    return merged
