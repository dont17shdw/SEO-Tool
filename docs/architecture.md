# Architecture / 架构

## Scope / 范围

Phase 1 established the Next.js frontend, FastAPI backend, PostgreSQL models, and Alembic migration. Phase 2 adds one complete manual Google Search Console (GSC) Pages import flow and a paginated, read-only page view.
第一阶段建立 Next.js 前端、FastAPI 后端、PostgreSQL 模型及 Alembic 迁移。第二阶段增加一条完整的手动 Google Search Console（GSC）网页导入流程，以及分页的只读页面视图。

The long-term workflow is **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**. V1 is **DATA → ANALYZE → PRIORITIZE → RECOMMEND**. Phase 2 implements only **GSC FILE → PARSE → VALIDATE → NORMALIZE → PREVIEW → PERSIST → VIEW**. Analysis, scoring, recommendations, AI reasoning, and execution remain unimplemented.
长期流程为 **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**。V1 为 **DATA → ANALYZE → PRIORITIZE → RECOMMEND**。第二阶段仅实现 **GSC FILE → PARSE → VALIDATE → NORMALIZE → PREVIEW → PERSIST → VIEW**。分析、评分、建议、AI 推理及执行仍未实现。

## Local runtime / 本地运行架构

```text
Browser / 浏览器
  └── Next.js + React + TypeScript
        ├── /                     Development and health page / 开发与健康检查页面
        ├── /imports/gsc          File preview and confirmation / 文件预览与确认
        └── /pages                Paginated page metrics / 分页页面指标
              └── FastAPI /api/v1
                    ├── Health / 健康检查
                    ├── GSC parsing and normalization / GSC 解析与标准化
                    └── SQLAlchemy → PostgreSQL

Alembic → Explicit database migrations / 显式数据库迁移
```

The frontend and backend run as local processes; Docker Compose runs PostgreSQL only. The backend retains synchronous SQLAlchemy 2 sessions and psycopg 3. There is no task queue, server-side preview session, or permanent upload store.
前端与后端以本地进程运行；Docker Compose 仅运行 PostgreSQL。后端沿用 SQLAlchemy 2 同步会话与 psycopg 3。当前没有任务队列、服务端预览会话或永久上传存储。

## Module boundaries / 模块边界

```text
backend/app/
  api/v1/                   HTTP requests and response schemas / HTTP 请求与响应结构
  config/                   Environment settings / 环境配置
  db/                       SQLAlchemy sessions and base metadata / 会话与基础元数据
  models/                   Persistent records / 持久化记录
  imports/gsc/              GSC mapping, parsing, preview, persistence / GSC 映射、解析、预览、持久化
  normalization/            Deterministic URL and metric validation / 确定性 URL 与指标校验
  analysis/                 Reserved observations boundary / 预留观察结果边界
  scoring/                  Reserved calculations boundary / 预留评分计算边界
  decision_engine/          Reserved prioritization boundary / 预留优先级边界
  ai/                       Reserved semantic reasoning boundary / 预留语义推理边界
  execution/                Reserved future actions boundary / 预留未来行动边界
backend/alembic/            Explicit schema migrations / 显式数据库结构迁移
backend/tests/              Synthetic parser and database tests / 合成解析与数据库测试
frontend/src/               Development routes and typed API client / 开发路由与带类型 API 客户端
docs/                       Bilingual contracts and setup guidance / 双语契约与设置指南
```

- **Imports:** Source-specific mapping accepts English and Chinese GSC page headers. The standard-library CSV reader and lightweight `openpyxl` reader handle source formats. Worksheet selection checks page semantics and URL dimensions, rather than selecting any sheet with similar performance columns.
  **导入：** 数据源映射支持英文及中文 GSC 网页列名。标准库 CSV 读取器及轻量的 `openpyxl` 读取器负责文件格式。工作表选择检查网页语义与 URL 维度，不根据相似的性能指标列随意选择工作表。
- **Normalization:** Validate absolute HTTP(S) URLs and metric values, trim surrounding whitespace, and produce the existing model's four GSC fields. Missing metrics remain unknown; normalization does not infer SEO classifications or rewrite URLs.
  **标准化：** 校验绝对 HTTP(S) URL 与指标值，去除前后空白，并生成现有模型的四个 GSC 字段。缺失指标保持未知；标准化不推导 SEO 分类，也不重写 URL。
- **API:** Routes handle bounded multipart uploads, typed responses, explicit confirmation, and useful public errors. They delegate source processing and database persistence to the import modules.
  **API：** 路由处理有大小限制的 multipart 上传、带类型响应、显式确认及易理解的公开错误。它们将数据源处理与数据库持久化委托给导入模块。
- **Persistence:** The import service upserts exact stored URL strings within one transaction. The models define database integrity without parsing files or making SEO judgments.
  **持久化：** 导入服务在一个事务内按实际存储的 URL 字符串执行新增或更新。模型负责数据库完整性，不解析文件，也不进行 SEO 判断。
- **Future processing:** Analysis, scoring, decision-making, AI reasoning, and execution remain separate. Deterministic code should perform calculations. Future AI provider details belong behind the AI boundary; recommendations must not cause external actions automatically.
  **未来处理：** 分析、评分、决策、AI 推理与执行保持独立。计算应使用确定性代码。未来 AI 供应商细节属于 AI 边界内部；建议不得自动触发外部行动。

## Preview and confirmation / 预览与确认

Preview parses and validates the upload without opening a database session or writing records. It reports source, worksheet, column mapping, row counts, errors, and normalized samples. Mapping and validation use deterministic code without AI.
预览解析并校验上传文件，不打开数据库会话，也不写入记录。它报告数据源、工作表、列映射、行数、错误及标准化样本。映射与校验使用确定性代码，不使用 AI。

The browser retains the selected file. Confirmation submits that file again with `confirmed=true` and the returned `preview_hash`. The backend re-parses the entire upload and verifies its fingerprint before persistence; it does not trust client-provided normalized rows. Invalid rows or duplicate URLs block the entire import. No partial valid-row import is performed.
浏览器保留选中的文件。确认时再次提交该文件，并附带 `confirmed=true` 与返回的 `preview_hash`。后端在持久化前重新解析整个上传内容并校验指纹，不信任客户端提供的标准化行。无效行或重复 URL 会阻止整个导入；不会仅导入其中的有效行。

The hash binds confirmation to the previewed file; it is not authentication, authorization, an import history, or a persistent server-side token. Re-submitting an unchanged file is safe: existing unchanged records are reported as skipped.
哈希将确认绑定到已预览的文件；它不是身份认证、权限控制、导入历史或持久化的服务端令牌。重新提交相同文件是安全的：未发生变化的已有记录会计为跳过。

See [gsc-import.md](gsc-import.md) for aliases, reporting-window checks, normalization, limits, request examples, and duplicate semantics.
列名别名、报告窗口检查、标准化、限制、请求示例与重复数据语义详见 [gsc-import.md](gsc-import.md)。

## Versioned API / 带版本的 API

| Endpoint / 接口 | Behavior / 行为 |
| --- | --- |
| `GET /api/v1/health` | Application liveness; no database access.<br>应用存活检查；不访问数据库。 |
| `POST /api/v1/imports/gsc/pages/preview` | Validate a CSV/XLSX upload; no persistence.<br>校验 CSV/XLSX 上传；不持久化。 |
| `POST /api/v1/imports/gsc/pages/apply` | Revalidate and atomically persist an explicitly confirmed file.<br>重新校验并原子持久化已显式确认的文件。 |
| `GET /api/v1/pages` | Read-only page metrics with basic pagination.<br>提供基本分页的只读页面指标。 |

The health response remains `{"status":"ok","service":"seo-tool-api"}`. It confirms the API process can serve requests, not that PostgreSQL is ready. FastAPI's `/docs` describes the implemented request and response contracts. There are no page editing/deletion endpoints or opportunity APIs.
健康检查响应仍为 `{"status":"ok","service":"seo-tool-api"}`。它确认 API 进程能处理请求，不能证明 PostgreSQL 已就绪。FastAPI 的 `/docs` 描述已实现的请求与响应契约。当前没有页面编辑、删除接口或机会 API。

The browser calls the backend directly through `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`. `CORS_ORIGINS` is an explicit JSON list of frontend origins. CORS supports the separate local ports; it is not an access-control system.
浏览器通过 `NEXT_PUBLIC_API_BASE_URL` 直接调用后端，默认值为 `http://localhost:8000`。`CORS_ORIGINS` 是明确的前端来源 JSON 列表。CORS 支持本地不同端口；它不是访问控制系统。

## Schema and reporting windows / 数据库结构与报告窗口

Phase 2 needs no new migration: the Phase 1 `WebsitePage` model already contains `clicks_28d`, `impressions_28d`, `ctr`, and `average_position`. PostgreSQL still stores `website_pages` and `seo_opportunities`; Phase 2 does not create opportunities. Schema changes remain explicit Alembic migrations, never automatic application-startup changes.
第二阶段无需新增迁移：第一阶段的 `WebsitePage` 模型已包含 `clicks_28d`、`impressions_28d`、`ctr` 与 `average_position`。PostgreSQL 仍存储 `website_pages` 与 `seo_opportunities`；第二阶段不创建机会。数据库结构变化仍由显式 Alembic 迁移管理，不能在应用启动时自动变更。

The supported import window is the latest 28 days. CSV has no workbook filter metadata, so the user must select that period before exporting. Supported XLSX filter metadata is validated when present. The database stores the latest supplied values, without observation-date anchors, import history, or dated snapshots; repeatedly uploading different files can replace prior metrics. See [data-model.md](data-model.md) for the exact write boundary and preservation rules.
支持的导入窗口为最近 28 天。CSV 不包含工作簿筛选元数据，因此用户必须在导出前选择该时间段。XLSX 存在受支持的筛选元数据时会进行校验。数据库存储最新提供的指标，没有观察日期基准、导入历史或带日期的快照；多次上传不同文件可能替换此前指标。明确的写入边界与保留规则详见 [data-model.md](data-model.md)。

## Configuration and limits / 配置与限制

Keep real credentials and environment files outside Git. `DATABASE_URL` uses `postgresql+psycopg://`. Next.js includes `NEXT_PUBLIC_API_BASE_URL` in browser code at build time; changing it requires restarting development or rebuilding. Installation and local commands are in [README.md](../README.md).
真实凭据与环境文件不得提交到 Git。`DATABASE_URL` 使用 `postgresql+psycopg://`。Next.js 在构建时将 `NEXT_PUBLIC_API_BASE_URL` 写入浏览器代码；修改后需要重启开发服务器或重新构建。安装与本地命令位于 [README.md](../README.md)。

Uploads are bounded to 5 MiB and 10,000 data rows. Preview returns at most 100 validation errors and 10 normalized samples while retaining full row counts. Source uploads are processed ephemerally and must not be committed; automated tests generate synthetic files. This is a local development interface without authentication or a production deployment plan.
上传限制为 5 MiB 与 10,000 个数据行。预览最多返回 100 个校验错误与 10 个标准化样本，同时保留完整行数统计。源上传文件仅作临时处理，不得提交；自动化测试生成合成文件。这是没有身份认证或生产部署方案的本地开发界面。

Phase 2 does not include GSC/GA4 APIs, query-level imports, indexing reports, analysis, scoring, opportunity generation, a Decision Engine, AI calls, content generation, WordPress, outreach, background jobs, or autonomous actions.
第二阶段不包含 GSC/GA4 API、查询级导入、索引报告、分析、评分、机会生成、决策引擎、AI 调用、内容生成、WordPress、外链联系、后台任务或自主行动。

## Suggested Phase 3 / 建议的第三阶段

Add deterministic, read-only data-quality and latest-28-day observations with explicit evidence and missing-data handling. Define the evidence required for any later recommendation rules before implementing them. Current imports do not provide previous-period or seven-day metrics, so they cannot support reliable trend comparisons. Do not expand this into a full Decision Engine, scoring system, AI integration, or execution. Phase 3 has not started.
增加确定性的只读数据质量检查与最近 28 天观察结果，明确证据及缺失数据的处理方式。在实现后续建议规则之前，先定义其所需证据。当前导入不提供前一时间段或七天指标，因此无法支持可靠的趋势对比。不要将其扩展为完整的决策引擎、评分系统、AI 集成或执行功能。第三阶段尚未开始。
