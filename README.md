# TrendIQ Research

TrendIQ 是一个美股策略研究和单股技术分析工作台。它生成带有技术指标、结构化事件证据、明确“未解释部分”和风险边界的研究报告；它不会自动交易。

## 本地运行

在仓库根目录复制环境变量模板，并只在本机填写 AI 服务配置。不要提交 `.env.local`。

```bash
cp .env.example .env.local
```

研究服务从进程环境读取变量；启动前在当前 shell 中加载根目录的 `.env.local`：

```bash
set -a && source .env.local && set +a
```

启动研究服务：

```bash
cd services/research && uv sync && uv run uvicorn app.main:app --reload --port 8000
```

另开一个终端，加载同一份 `.env.local` 后启动 Web 应用：

```bash
set -a && source .env.local && set +a
cd apps/web && npm install && npm run dev
```

浏览器访问 `http://localhost:3000`。如 Web 应用和研究服务不在默认地址运行，请在 `.env.local` 中修改 `RESEARCH_SERVICE_URL`。

## 研究版本与验证边界

首个冻结版本为 `research-v1`。它使用固定观察池，将 2020–2024 的数据用于开发和校准 K 线规则与事件权重；2025 年数据只用于冻结后的样本外验证，不能再用于调参。研究运行会记录这两个窗口及验证指标。

新增股票不会修改 `research-v1` 或重写其历史结果。新股票先进入观察池，并只能通过后续版本（例如 `research-v2`）重新研究、冻结和验证。

## 数据与归因限制

- 历史日线来自 yfinance，属于原型研究数据：可能延迟、修订、缺失或受上游限制，不能视为官方实时行情或交易执行依据。
- 财报、SEC 与宏观日历等结构化事件可以提供有时间戳的证据。新闻、政策、战争等历史覆盖不足时，报告会显示未覆盖状态和“未解释部分”，不会把事后新闻宣称为价格波动的确定原因。
- 影响权重是冻结规则下的证据支持度，不是因果证明，也不是预测保证。
- 本项目不连接券商、不下单、不提供自动交易功能；所有点位和报告仅供研究参考，不构成投资建议。

## 验证

```bash
cd services/research && uv run pytest && uv run ruff check .
cd apps/web && npm run test && npm run build && npm run test:e2e
```

端到端测试用本地固定夹具拦截报告请求，因此不依赖 yfinance、真实新闻源或研究服务。
