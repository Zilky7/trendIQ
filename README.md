# TrendIQ

## Local development

```bash
cd services/research && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd apps/web && npm install && npm run dev
```
