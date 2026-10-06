# Architecture / 架构

## Scope / 范围

Phase 1 creates a runnable foundation for the SEO Tool: a development frontend, a versioned backend health API, PostgreSQL models, and a migration. It does not ingest data, analyze SEO performance, calculate opportunity scores, or generate recommendations.

第一阶段为 SEO Tool 建立可运行的基础：开发用前端、带版本的后端健康检查 API、PostgreSQL 模型及数据库迁移。此阶段不导入数据、不分析 SEO 表现、不计算机会评分，也不生成建议。

The long-term workflow is **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**. V1 narrows that workflow to **DATA → ANALYZE → PRIORITIZE → RECOMMEND**. Phase 1 provides the structure needed to build V1 incrementally; neither workflow is implemented yet.

长期工作流程为 **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**。V1 将其范围收敛为 **DATA → ANALYZE → PRIORITIZE → RECOMMEND**。第一阶段提供逐步构建 V1 所需的结构，尚未实现这些工作流程。

## Local runtime / 本地运行架构

```text
Browser / 浏览器
  ├── Next.js + React + TypeScript frontend / 前端
  └── GET /api/v1/health
        └── FastAPI backend / 后端

Alembic migration / 数据库迁移
  └── PostgreSQL

Future data APIs / 未来数据 API
  └── SQLAlchemy session / 数据库会话
        └── PostgreSQL
```

Run the frontend and backend as local development processes. Docker Compose runs PostgreSQL only. This keeps the foundation small while giving later data APIs a real relational database and explicit schema migrations.

前端和后端以本地开发进程运行。Docker Compose 仅运行 PostgreSQL。这样既保持基础架构精简，又为后续数据 API 提供实际的关系数据库与明确的数据库结构迁移。

The frontend uses the Next.js App Router, React, and TypeScript. Its development page confirms that the frontend is running and provides a manual backend connection check with a five-second timeout and response validation. It does not implement an SEO dashboard or read database records.

前端采用 Next.js App Router、React 和 TypeScript。开发页面确认前端已运行，并提供手动检查后端连接的入口，包括五秒超时与响应校验。它不实现 SEO 仪表盘，也不读取数据库记录。

The backend uses FastAPI with synchronous SQLAlchemy 2 sessions and the psycopg 3 PostgreSQL driver. The initial API is small; an asynchronous database layer would add complexity without helping a current use case.

后端采用 FastAPI、SQLAlchemy 2 同步会话及 psycopg 3 PostgreSQL 驱动。初始 API 范围很小，异步数据库层会增加复杂度，却无法满足当前尚不存在的需求。

## Repository boundaries / 仓库职责边界

```text
frontend/                   Next.js application / Next.js 应用
backend/
  app/
    api/                    HTTP routes and schemas / HTTP 路由与接口结构
    config/                 Environment settings / 环境配置
    db/                     Database sessions and base metadata / 数据库会话与基础元数据
    models/                 Persistent records / 持久化记录
    imports/                Future ingestion / 未来数据导入
    normalization/          Future validation and normalization / 未来校验与标准化
    analysis/               Future deterministic analysis / 未来确定性分析
    scoring/                Future opportunity calculations / 未来机会评分计算
    decision_engine/        Future prioritization and recommendations / 未来优先级与建议
    ai/                     Future semantic reasoning / 未来语义推理
    execution/              Reserved future execution boundary / 预留的未来执行边界
  alembic/                  Alembic schema migrations / Alembic 数据库结构迁移
  tests/                    Backend checks / 后端检查
docs/                       Architecture and data model / 架构与数据模型
```

The future pipeline packages are boundaries, not working features. They reserve clear homes for later code without introducing placeholder SEO rules or artificial interfaces. HTTP routes should delegate processing to these modules as functionality is added.

未来数据流程的各个包用于划分职责，并非已实现的功能。它们为后续代码保留明确位置，而不引入占位 SEO 规则或人为设计的接口。随着功能增加，HTTP 路由应将处理工作委托给相应模块。

- **Imports** receive source data and preserve source-specific handling; they should not decide SEO actions. **Normalization** validates and converts imported values into the shared model before persistence.
- **导入模块**接收源数据并处理数据源差异，不应决定 SEO 行动。**标准化模块**在持久化前校验导入值，并将其转换为统一模型。
- **Analysis** derives observations from normalized data. **Scoring** owns reproducible calculations and explicit scoring inputs. Neither module calls an AI model to perform arithmetic.
- **分析模块**从标准化数据中提取观察结果。**评分模块**负责可复现的计算及明确的评分输入。两者均不调用 AI 模型进行算术计算。
- **Decision engine** will choose priorities and explain recommendations using observations and scores. A persisted `SEOOpportunity` is a data contract, not an implemented decision algorithm.
- **决策引擎**未来将结合观察结果与评分选择优先级，并解释建议。持久化的 `SEOOpportunity` 是数据契约，并不代表已实现决策算法。
- **AI** will be used mainly for semantic analysis and reasoning when a concrete feature needs it. Keep model-provider details behind this boundary; Phase 1 has no provider SDK, model dependency, credentials, or calls.
- **AI 模块**主要用于未来具体功能所需的语义分析与推理。模型供应商细节应封装在此边界内；第一阶段不包含供应商 SDK、模型依赖、凭证或调用。
- **Execution** remains a separate future concern. A recommendation must not trigger publishing, outreach, emails, or other external actions. No execution service is implemented in Phase 1.
- **执行**属于独立的未来职责。建议不得触发发布、外链联系、邮件或其他外部操作。第一阶段不实现执行服务。

## API and browser connection / API 与浏览器连接

`GET /api/v1/health` is a liveness endpoint. It responds successfully when the backend process can serve requests and does not connect to PostgreSQL. A successful health response therefore confirms the API process, not database readiness. Check database connectivity by applying the migration during setup.

`GET /api/v1/health` 是存活检查接口。后端进程能够处理请求时，该接口返回成功，且不会连接 PostgreSQL。因此，健康检查成功只能确认 API 进程可用，不能证明数据库已就绪。配置时通过执行迁移检查数据库连接。

The response is `{"status":"ok","service":"seo-tool-api"}`. The frontend validates this response before showing a connected state and reports an error if the API cannot be reached or the response is invalid.

响应为 `{"status":"ok","service":"seo-tool-api"}`。前端在显示已连接状态前校验此响应；若无法连接 API 或响应无效，则显示错误。

The `/api/v1` prefix establishes the first API version. No page or opportunity CRUD routes are included. FastAPI's OpenAPI document describes the implemented health endpoint and provides a place for future typed API contracts.

`/api/v1` 前缀定义首个 API 版本。当前不包含页面或机会的增删改查路由。FastAPI 的 OpenAPI 文档描述已实现的健康检查接口，并为未来带类型的 API 契约提供位置。

The browser calls the backend directly using `NEXT_PUBLIC_API_BASE_URL`, which defaults to `http://localhost:8000`. The frontend development server uses port `3000`. The backend allows only explicitly configured frontend origins through `CORS_ORIGINS`, a JSON list. This configuration supports separate local development ports; it is not an authentication or authorization system.

浏览器通过 `NEXT_PUBLIC_API_BASE_URL` 直接调用后端，默认值为 `http://localhost:8000`。前端开发服务器使用 `3000` 端口。后端通过 JSON 列表 `CORS_ORIGINS` 仅允许明确配置的前端来源。此配置用于支持本地开发中的不同端口，并非身份认证或授权系统。

## Persistence and migrations / 持久化与迁移

PostgreSQL stores `website_pages` and `seo_opportunities`. SQLAlchemy defines shared model metadata and Alembic manages schema changes. Apply migrations explicitly; starting FastAPI must not create tables or alter the database automatically.

PostgreSQL 存储 `website_pages` 和 `seo_opportunities`。SQLAlchemy 定义共享模型元数据，Alembic 管理数据库结构变化。应显式执行迁移；启动 FastAPI 不应自动创建表或修改数据库。

A website page can have multiple opportunities. The initial schema stores normalized fields and enforces basic data integrity. It does not define SEO thresholds, opportunity taxonomies, scoring formulas, or automated recommendations. See [data-model.md](data-model.md) for field semantics and constraints.

一个网站页面可以对应多个机会。初始结构存储标准化字段并约束基本数据完整性，但不定义 SEO 阈值、机会分类、评分公式或自动建议。字段语义与约束详见 [data-model.md](data-model.md)。

## Configuration and operational limits / 配置与运行限制

Environment examples document local configuration. Keep real environment files and credentials outside Git. Backend settings own database connectivity and allowed browser origins; frontend public settings must contain only values safe to expose in browser code.

环境变量示例记录本地配置。真实环境文件及凭证不得提交到 Git。后端配置负责数据库连接与允许的浏览器来源；前端公开配置只能包含允许暴露在浏览器代码中的值。

`DATABASE_URL` must use the `postgresql+psycopg://` driver scheme. Next.js includes `NEXT_PUBLIC_API_BASE_URL` in browser code at build time, so restart the development server or rebuild after changing it. See the root [README.md](../README.md) for installation, migration, and startup commands.

`DATABASE_URL` 必须使用 `postgresql+psycopg://` 驱动协议。Next.js 在构建时将 `NEXT_PUBLIC_API_BASE_URL` 写入浏览器代码，因此修改后应重启开发服务器或重新构建。安装、迁移与启动命令详见根目录 [README.md](../README.md)。

There is no task queue, scheduler, cache, vector database, AI provider, production deployment configuration, authentication, or observability platform in Phase 1. Add infrastructure only when an implemented feature requires it. The current development setup is not a production deployment plan.

第一阶段不包含任务队列、调度器、缓存、向量数据库、AI 供应商、生产部署配置、身份认证或可观测平台。只有当已实现的功能确实需要时才增加基础设施。当前开发配置并非生产部署方案。

## Recommended Phase 2 / 建议的第二阶段范围

Implement one manually uploaded CSV format for website page metrics. Document its columns, units, and validation rules; validate and normalize it deterministically; persist the resulting `WebsitePage` records; and expose a paginated, read-only page list through the V1 API and a minimal frontend view.

实现一种手动上传的网站页面指标 CSV 格式。记录其列名、单位和校验规则；通过确定性代码进行校验与标准化；持久化生成的 `WebsitePage` 记录；通过 V1 API 提供分页的只读页面列表，并添加最小前端视图。

Decide the import contract for duplicate URLs, missing values, malformed rows, and the metric observation window before implementation. Test valid imports, invalid input, duplicate behavior, database persistence, and pagination. Do not include opportunity scoring, SEO recommendations, external integrations, AI calls, execution, or production deployment in that step.

实施前明确重复 URL、缺失值、格式错误行及指标观察时间窗口的导入契约。测试有效导入、无效输入、重复数据处理、数据库持久化及分页。该阶段不包含机会评分、SEO 建议、外部集成、AI 调用、执行或生产部署。
