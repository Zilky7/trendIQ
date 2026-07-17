import json

import httpx
from fastapi.testclient import TestClient


def _rule_report(symbol: str = "MU") -> dict[str, object]:
    return {
        "symbol": symbol,
        "model_version": "research-v1",
        "report_source": "rules",
        "source_label": "yfinance historical prototype data",
        "event_coverage": [],
        "attributions": [{"kind": "unexplained", "weight": 100, "confidence": "low", "evidence": None}],
        "technical_context": {
            "close": 100,
            "sma_50": 95,
            "sma_200": 90,
            "rsi_14": 55,
            "atr_14": 2,
            "distance_from_20d_high": -1,
            "average_volume_20": 10,
            "latest_volume": 11,
            "volume_ratio": 1.1,
        },
        "chart_bars": [
            {
                "date": "2025-01-02",
                "open": 98.0,
                "high": 101.0,
                "low": 97.0,
                "close": 100.0,
                "volume": 1_000_000.0,
                "sma_50": 95.0,
                "sma_200": 90.0,
            },
            {
                "date": "2025-01-03",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1_100_000.0,
                "sma_50": 95.2,
                "sma_200": 90.1,
            },
        ],
        "summary": "规则分析",
        "reasoning_steps": ["仅使用已提供技术事实"],
        "risks": ["未解释部分仍然存在"],
        "execution_plan": {
            "side": "long",
            "entry": 100,
            "stop_loss": 97,
            "take_profit_1": 104,
            "take_profit_2": 106,
            "take_profit_3": 108,
            "invalidation": "跌破止损价位",
        },
        "disclaimer": "仅供研究参考，不构成投资建议",
    }


def test_health_route_is_available() -> None:
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_report_route_returns_rule_fallback_without_secret(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setattr("app.main.build_symbol_report", lambda symbol: _rule_report(symbol))

    response = TestClient(app).get("/api/reports/mu")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "MU"
    assert payload["report_source"] == "rules"
    assert payload["attributions"][-1]["kind"] == "unexplained"
    assert "AI_API_KEY" not in json.dumps(payload)
    assert "not-a-response-secret" not in json.dumps(payload)


def test_report_route_returns_bounded_chronological_chart_bars(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setattr("app.main.build_symbol_report", lambda symbol: _rule_report(symbol))

    response = TestClient(app).get("/api/reports/MU")

    assert response.status_code == 200
    bars = response.json()["chart_bars"]
    assert 1 <= len(bars) <= 260
    assert [bar["date"] for bar in bars] == sorted(bar["date"] for bar in bars)
    assert all(
        bar["low"] <= min(bar["open"], bar["close"])
        and bar["high"] >= max(bar["open"], bar["close"])
        and bar["volume"] >= 0
        for bar in bars
    )
    assert bars[-1]["sma_50"] == 95.2
    assert bars[-1]["sma_200"] == 90.1


def test_report_route_rejects_nonfinite_or_out_of_order_chart_bars(monkeypatch) -> None:
    from app.main import app

    report = _rule_report()
    report["chart_bars"] = [
        {**report["chart_bars"][0], "close": float("nan")},
        report["chart_bars"][0],
    ]
    monkeypatch.setattr("app.main.build_symbol_report", lambda _: report)

    response = TestClient(app).get("/api/reports/MU")

    assert response.status_code == 502
    assert response.json()["detail"] == "unable to build report from configured research providers"


def test_report_route_rejects_out_of_order_chart_bars(monkeypatch) -> None:
    from app.main import app

    report = _rule_report()
    report["chart_bars"] = list(reversed(report["chart_bars"]))
    monkeypatch.setattr("app.main.build_symbol_report", lambda _: report)

    response = TestClient(app).get("/api/reports/MU")

    assert response.status_code == 502
    assert response.json()["detail"] == "unable to build report from configured research providers"


def test_invalid_symbol_maps_to_bad_request(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setattr("app.main.build_symbol_report", lambda symbol: _rule_report(symbol))

    response = TestClient(app).get("/api/reports/%3Cscript%3E")

    assert response.status_code == 400
    assert response.json()["detail"] == "symbol must contain 1-10 uppercase letters, numbers, dots, or hyphens"


def test_valid_symbol_upstream_error_maps_to_safe_gateway_error(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setattr(
        "app.main.build_symbol_report",
        lambda _: (_ for _ in ()).throw(ValueError("provider secret: not-a-response-secret")),
    )

    response = TestClient(app).get("/api/reports/MU")

    assert response.status_code == 502
    assert response.json()["detail"] == "unable to build report from configured research providers"
    assert "not-a-response-secret" not in response.text


def test_ai_prose_with_unsupplied_facts_is_rejected_for_rule_fallback() -> None:
    from app.services.report import _merge_ai_explanation

    report = _rule_report()
    report["reasoning_steps"] = ["收盘价 100.00。"]
    report["risks"] = ["未解释部分仍然存在。"]
    result = _merge_ai_explanation(
        report,
        {
            "summary": "Earnings news caused a drop to 99.00.",
            "reasoning_steps": ["收盘价 100.00。", "Invented news."],
            "risks": ["未解释部分仍然存在。"],
            "execution_plan": report["execution_plan"],
        },
    )

    assert result["report_source"] == "rules"
    assert result["summary"] == "规则分析"


def test_compliant_ai_response_echoing_supplied_report_facts_is_accepted() -> None:
    from app.services.report import _ai_facts, _merge_ai_explanation

    report = _rule_report()
    facts = _ai_facts(report)
    result = _merge_ai_explanation(
        report,
        {
            "summary": facts["summary"],
            "reasoning_steps": facts["reasoning_steps"],
            "risks": facts["risks"],
            "execution_plan": facts["execution_plan"],
        },
    )

    assert result["report_source"] == "ai"


def test_research_run_route_persists_a_version(monkeypatch, tmp_path) -> None:
    from app.main import app

    monkeypatch.setattr("app.main.ResearchRunStore", lambda _: __import__("app.services.research_run", fromlist=["ResearchRunStore"]).ResearchRunStore(tmp_path))

    response = TestClient(app).post(
        "/api/research-runs",
        json={
            "version": "research-v1",
            "universe": ["MU", "MRVL"],
            "parameters": {"rsi_min": 50},
            "development_metrics": {"win_rate": 0.5},
            "validation_metrics": {"win_rate": 0.4},
        },
    )

    assert response.status_code == 201
    assert response.json()["version"] == "research-v1"
    assert (tmp_path / "research-v1.json").exists()


def test_research_run_does_not_fetch_chart_or_report_data(monkeypatch, tmp_path) -> None:
    from app.main import app

    monkeypatch.setattr("app.main.ResearchRunStore", lambda _: __import__("app.services.research_run", fromlist=["ResearchRunStore"]).ResearchRunStore(tmp_path))
    monkeypatch.setattr(
        "app.main.build_symbol_report",
        lambda _: (_ for _ in ()).throw(AssertionError("research runs must not fetch report data")),
    )

    response = TestClient(app).post(
        "/api/research-runs",
        json={"version": "research-v2", "universe": ["MU"]},
    )

    assert response.status_code == 201
    assert response.json()["window"]["validation_end"] == "2025-12-31"


def test_ai_client_uses_configured_model_and_chat_completions_request(monkeypatch) -> None:
    from app.providers.ai import AIClient

    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"summary": "Only supplied facts", "reasoning_steps": ["fact"], "risks": ["risk"], "execution_plan": {"side": "long"}})}}]},
        )

    monkeypatch.setenv("AI_BASE_URL", "https://ai.example/v1")
    monkeypatch.setenv("AI_API_KEY", "not-a-response-secret")
    monkeypatch.setenv("AI_MODEL", "gpt-5.6-terra")
    client = AIClient(transport=httpx.MockTransport(handler))

    result = client.generate({"close": 100})

    assert result is not None
    assert seen["url"] == "https://ai.example/v1/chat/completions"
    assert seen["json"]["model"] == "gpt-5.6-terra"
    assert seen["json"]["messages"][0]["content"].startswith("You explain only")
    assert seen["headers"]["authorization"] == "Bearer not-a-response-secret"


def test_ai_timeout_or_error_returns_none_for_rule_fallback(monkeypatch) -> None:
    from app.providers.ai import AIClient

    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    monkeypatch.setenv("AI_BASE_URL", "https://ai.example/v1")
    monkeypatch.setenv("AI_API_KEY", "configured")
    monkeypatch.setenv("AI_MODEL", "gpt-5.6-terra")

    assert AIClient(transport=httpx.MockTransport(handler)).generate({"close": 100}) is None


def test_ai_http_success_without_completion_content_returns_rule_fallback(monkeypatch) -> None:
    from app.providers.ai import AIClient

    monkeypatch.setenv("AI_BASE_URL", "https://ai.example/v1")
    monkeypatch.setenv("AI_API_KEY", "configured")
    monkeypatch.setenv("AI_MODEL", "gpt-5.6-terra")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    assert AIClient(transport=httpx.MockTransport(handler)).generate({"close": 100}) is None
