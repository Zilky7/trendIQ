"""HTTP boundary for reproducible research and evidence-backed reports."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.domain.strategy import ResearchWindow
from app.services.report import build_symbol_report, validate_symbol
from app.services.research_run import ResearchRun, ResearchRunStore


class HealthResponse(BaseModel):
    status: Literal["ok"]


class EventEvidenceResponse(BaseModel):
    kind: str
    occurred_on: str
    title: str
    url: str
    proximity: float
    repeatability: float
    peer_confirmation: float


class EventCoverageResponse(BaseModel):
    provider: str
    state: Literal["available", "partial", "unavailable"]
    detail: str
    events: list[EventEvidenceResponse]


class AttributionResponse(BaseModel):
    kind: str
    weight: float
    confidence: Literal["low", "medium", "high"]
    evidence: EventEvidenceResponse | None


class TechnicalContextResponse(BaseModel):
    close: float
    sma_50: float
    sma_200: float
    rsi_14: float
    atr_14: float
    distance_from_20d_high: float
    average_volume_20: float
    latest_volume: float
    volume_ratio: float


class ExecutionPlanResponse(BaseModel):
    side: Literal["long", "neutral"]
    entry: float | None
    stop_loss: float | None
    take_profit_1: float | None
    take_profit_2: float | None
    take_profit_3: float | None
    invalidation: str


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    model_version: str
    report_source: Literal["ai", "rules"]
    source_label: str
    event_coverage: list[EventCoverageResponse]
    attributions: list[AttributionResponse]
    technical_context: TechnicalContextResponse
    summary: str
    reasoning_steps: list[str]
    risks: list[str]
    execution_plan: ExecutionPlanResponse
    disclaimer: str


class ResearchRunRequest(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    universe: list[str] = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    development_metrics: dict[str, Any] = Field(default_factory=dict)
    validation_metrics: dict[str, Any] = Field(default_factory=dict)


class ResearchRunResponse(BaseModel):
    version: str
    universe: list[str]
    window: dict[str, str]
    parameters: dict[str, Any]
    development_metrics: dict[str, Any]
    validation_metrics: dict[str, Any]


app = FastAPI(title="TrendIQ Research API")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/reports/{symbol}", response_model=ReportResponse)
def get_report(symbol: str) -> ReportResponse:
    try:
        normalized_symbol = validate_symbol(symbol)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    try:
        return ReportResponse.model_validate(build_symbol_report(normalized_symbol))
    except Exception as error:
        # Details can include upstream internals; they must never be returned to
        # clients, particularly when a provider is configured with credentials.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="unable to build report from configured research providers",
        ) from error


@app.post("/api/research-runs", response_model=ResearchRunResponse, status_code=status.HTTP_201_CREATED)
def create_research_run(request: ResearchRunRequest) -> ResearchRunResponse:
    try:
        universe = tuple(validate_symbol(symbol) for symbol in request.universe)
        run = ResearchRun(
            version=request.version,
            universe=universe,
            window=ResearchWindow(),
            parameters=request.parameters,
            development_metrics=request.development_metrics,
            validation_metrics=request.validation_metrics,
        )
        ResearchRunStore(_runs_directory()).save(run)
        return ResearchRunResponse(**run.to_record())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _runs_directory() -> Path:
    return Path(os.getenv("RESEARCH_RUNS_DIR", "data/runs"))
