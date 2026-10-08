# SEO Tool

An AI-assisted SEO operations system. Phases 1–6 provide the runnable foundation, manual GSC imports, historical comparisons, evidence readiness, current metric provenance, explicit report scope, and observed-date coverage. Phase 7 detects four deterministic runtime opportunity signals. Phase 8 enables verified custom 28-day XLSX imports and adds transparent attention tiers to existing candidates, without scores or recommended actions.
由 AI 辅助的 SEO 运营系统。第一至六阶段提供可运行基础框架、手动 GSC 导入、历史对比、证据就绪度、当前指标来源、明确报告范围及已观察日期覆盖。第七阶段检测四种确定性的运行时机会信号。第八阶段支持经过校验的自定义 28 天 XLSX 导入，并为已有候选增加透明关注层级，不包含评分或建议行动。

Long-term workflow: `DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN`.
长期流程：`DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN`。

V1 scope: `DATA → ANALYZE → PRIORITIZE → RECOMMEND`.
V1 范围：`DATA → ANALYZE → PRIORITIZE → RECOMMEND`。

## MVP interface language / MVP 界面语言

The MVP interface uses Simplified Chinese (`zh-CN`) throughout imports, history, evidence, opportunities, priority tiers, and feedback. A small frontend presentation layer translates stable codes and structured evidence while retaining the Phase 1–8 API contracts, metrics, and analysis rules. Technical documentation and important code comments remain bilingual, English first and Chinese second. See [localization.md](docs/localization.md) for presentation boundaries, intentional technical terms, and validation scope.
MVP 界面在导入、历史、分析依据、SEO 机会、优先级及操作反馈中统一使用简体中文（`zh-CN`）。轻量前端展示层根据稳定代码与结构化证据生成中文内容，同时保留第一至八阶段的 API 契约、指标及分析规则。技术文档及重要代码注释仍使用英文在前、中文在后的双语形式。展示边界、保留的技术术语及验证范围详见 [localization.md](docs/localization.md)。

## Requirements / 环境要求

- Node.js 22.13+ on the 22.x line, or Node.js 24+, and npm for the frontend.
  前端需要 Node.js 22.x 中的 22.13+ 版本或 Node.js 24+，以及 npm。
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) for the FastAPI backend.
  FastAPI 后端需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。
- Docker with Compose, or a PostgreSQL 17 instance for local development.
  本地开发需要带 Compose 的 Docker，或 PostgreSQL 17 实例。

## Local setup / 本地设置

Run from the repository root. The example credentials are for local development only.
从仓库根目录开始执行。示例凭据仅用于本地开发。

```sh
cp .env.example .env
docker compose up -d --wait db
```

In a backend terminal, install the locked dependencies, configure the database connection, apply the migration, and start the API.
在后端终端中，安装锁定的依赖、配置数据库连接、执行迁移并启动 API。

```sh
cd backend
cp .env.example .env
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a separate frontend terminal, install the locked dependencies and start Next.js.
在独立的前端终端中，安装锁定的依赖并启动 Next.js。

```sh
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open <http://localhost:3000> for the development health page, <http://localhost:3000/imports/gsc> to preview and confirm a GSC import, <http://localhost:3000/imports/history> for successful imports, <http://localhost:3000/pages> for the read-only page list, and <http://localhost:3000/opportunities> for separate prioritized and neutral signal views. Open a page from the page list to see `/pages/[id]`, including current applied metrics, per-metric provenance, snapshots, comparison, data quality, and opportunity candidates or their evidence-gate reasons. API documentation is at <http://localhost:8000/docs>.
打开 <http://localhost:3000> 查看开发健康检查页面，打开 <http://localhost:3000/imports/gsc> 预览并确认 GSC 导入，打开 <http://localhost:3000/imports/history> 查看成功导入，打开 <http://localhost:3000/pages> 查看只读页面列表，打开 <http://localhost:3000/opportunities> 查看分开的优先级与中立信号视图。从页面列表打开页面可查看 `/pages/[id]`，包括当前应用指标、逐指标来源、快照、对比、数据质量，以及机会候选或证据门槛原因。API 文档位于 <http://localhost:8000/docs>。

```sh
curl http://localhost:8000/api/v1/health
```

The health endpoint checks application liveness only; it does not confirm database connectivity or migration readiness.
健康检查接口仅检查应用是否运行；它不确认数据库连接或迁移状态。

If you change the database credentials or port in the root `.env`, update `DATABASE_URL` in `backend/.env` to match. Configure allowed browser origins using the JSON array `CORS_ORIGINS`; the frontend uses `NEXT_PUBLIC_API_BASE_URL`. Compose binds PostgreSQL to the local machine only. Database credentials initialize a new volume; changing them does not update an existing database role.
如果修改根目录 `.env` 中的数据库凭据或端口，请同步修改 `backend/.env` 中的 `DATABASE_URL`。通过 JSON 数组 `CORS_ORIGINS` 配置允许的浏览器来源；前端使用 `NEXT_PUBLIC_API_BASE_URL`。Compose 仅在本机绑定 PostgreSQL 端口。数据库凭据用于初始化新数据卷；更改这些值不会更新已有数据库角色。

For an existing PostgreSQL instance, skip Compose, set `DATABASE_URL`, and apply the Alembic migrations. The applications run on the host. Phase 6 adds head revision `0004_report_scope`: run `uv run alembic upgrade head` before using the importer or history APIs. It creates minimal sites and additive scope/coverage fields, preserving all five existing tables, metric values, timestamps, and provenance links. Legacy site/scope/coverage remains unknown without backfill. Downgrade refuses safely if scoped records cannot satisfy the earlier global URL or file-hash uniqueness constraints.
使用已有 PostgreSQL 实例时，可跳过 Compose，设置 `DATABASE_URL` 并执行 Alembic 迁移。应用在宿主机上运行。第六阶段增加最新修订 `0004_report_scope`：使用导入器或历史 API 前，请运行 `uv run alembic upgrade head`。它创建最小站点表及附加范围与覆盖字段，保留已有五个表、指标值、时间戳与来源关联。旧站点、范围及覆盖保持未知，不回填。如果按范围存储的记录无法满足此前全局 URL 或文件哈希唯一性约束，降级会安全拒绝。

Data-quality observations, provenance observations, opportunity candidates, and priority tiers are calculated at request time and are not persisted. Only the current page-to-metric-to-snapshot links are stored for provenance. Phases 7–8 add no migration; Alembic head remains `0004_report_scope` and the reserved `SEOOpportunity` table stays untouched.
数据质量观察、来源观察、机会候选及优先级层级在请求时计算，不持久化。来源仅存储当前页面、指标及快照之间的关联。第七至八阶段不增加迁移；Alembic 最新修订仍为 `0004_report_scope`，预留 `SEOOpportunity` 表保持不变。

## GSC import / GSC 导入

Export the GSC Pages performance table for 28 days as CSV or XLSX. English and Chinese exports are supported, including the `Pages` / `网页` worksheet and localized headers. XLSX supports existing latest-28-day labels and narrowly recognized custom ranges of exactly 28 inclusive calendar days. CSV must use UTF-8 (an optional BOM is supported), and its exact dates/coverage remain unknown.
将 GSC 网页性能表的 28 天数据导出为 CSV 或 XLSX。支持英文与中文导出，包括 `Pages` / `网页` 工作表及本地化列名。XLSX 支持已有最近 28 天标签，以及严格识别且包含起止日恰为 28 个日历天的自定义范围。CSV 必须使用 UTF-8（支持可选的 BOM），其准确日期与覆盖仍保持未知。

Select the file at `/imports/gsc`, preview the detected mapping, counts, errors, and normalized samples, then explicitly confirm import. Preview does not write to the database. Correct every invalid or duplicate row before importing; imports are applied as one transaction. The `/pages` view displays the stored metrics with pagination.
在 `/imports/gsc` 选择文件，预览识别出的映射、行数、错误及标准化样本，再显式确认导入。预览不会写入数据库。导入前请修正每个无效或重复行；导入在一个事务内执行。`/pages` 视图分页显示已存储指标。

Only `clicks_28d`, `impressions_28d`, `ctr`, and `average_position` update the current page. Every supplied non-`NULL` metric, including zero or an unchanged value, points to this new import's snapshot. Blank inputs preserve both existing value and provenance. Optional Site creation, current pages, one `ImportRun`, snapshots, and provenance links commit together; any failure rolls back every write. Snapshots retain raw normalized `NULL` rather than carried-forward values. Other page fields are preserved. Real exports are not stored permanently or used as automated test fixtures.
仅 `clicks_28d`、`impressions_28d`、`ctr` 与 `average_position` 更新当前页面。每个提供的非 `NULL` 指标，包括零或未变化的值，都关联本次新导入的快照。空白输入同时保留已有值与来源。可选站点创建、当前页面、一个 `ImportRun`、快照及来源关联一起提交；任何失败回滚全部写入。快照保留原始标准化 `NULL`，不沿用此前值。其他页面字段保持不变。真实导出文件不会永久保存，也不会用作自动化测试数据。

XLSX date worksheets provide observed endpoints, distinct date count, and consecutiveness when reliable. Only 28 distinct consecutive dates spanning 28 days establish complete observed coverage; sparse endpoints do not. CSV coverage stays unknown. Enter explicit property/search/filter scope when the export omits it; preview distinguishes workbook-observed facts from user declarations and binds Apply to the same evidence. Matching bytes and canonical scope return the original run unchanged; the same bytes with another scope create separate history. Comparisons exclude explicitly conflicting scope; incomplete legacy scope stays visibly unknown.
可靠的 XLSX 日期工作表提供已观察起止日期、不同日期数量及连续性。只有跨度为 28 天的 28 个不同连续日期才能证明完整已观察覆盖；稀疏起止日期不能。CSV 覆盖保持未知。导出缺少属性、搜索类型或筛选范围时，可输入明确声明；预览区分工作簿观察事实与用户声明，并将应用绑定至相同证据。字节及规范范围均相同会返回原导入且不修改；相同字节配合另一范围会创建独立历史。对比排除明确冲突范围；不完整旧范围明确保持未知。

For independent before/after evidence, export two non-overlapping 28-day XLSX periods under the same full scope, then import the older period first. Weekly latest-28-day exports generally overlap and cannot produce opportunity candidates. Custom labels never fill missing daily observations. The unchanged `latest_28_days` identifier represents the existing 28-day metric family; actual dates come from observed rows. The private [TuffPlus acceptance procedure](docs/opportunity-prioritization.md#real-tuffplus-acceptance-procedure--真实-tuffplus-验收流程) explains the required evidence.
如需独立前后证据，请在相同完整范围下导出两个互不重叠的 28 天 XLSX 时间段，再先导入较早时间段。每周导出的最近 28 天报告通常重叠，不能生成机会候选。自定义标签绝不补充缺失每日观察。不变的 `latest_28_days` 标识表示已有 28 天指标类别；实际日期来自已观察行。私下执行的 [TuffPlus 验收流程](docs/opportunity-prioritization.md#real-tuffplus-acceptance-procedure--真实-tuffplus-验收流程) 说明所需证据。

Uploads are limited to 5 MiB and 10,000 data rows. This is a local development workflow with no authentication. See [the GSC import contract](docs/gsc-import.md) for supported headers, reporting-window behavior, normalization, API requests, and current limitations.
上传限制为 5 MiB 与 10,000 个数据行。这是没有身份认证的本地开发流程。支持的列名、报告窗口行为、标准化、API 请求及当前限制详见 [GSC 导入契约](docs/gsc-import.md)。

## Data quality / 数据质量

The page history view shows `insufficient`, `limited`, or `ready` data readiness with structured factual observations. Quality reuses the selected Phase 3 comparison; it does not recalculate changes, fill missing metrics, mutate history, or create `SEOOpportunity` records. Readiness describes the evidence available for descriptive comparison, without an SEO score or action.
页面历史视图显示 `insufficient`、`limited` 或 `ready` 数据就绪度及结构化事实观察。质量复用第三阶段选中的对比，不重新计算变化、不填补缺失指标、不修改历史，也不创建 `SEOOpportunity` 记录。就绪度描述可用于描述性对比的证据，不包含 SEO 评分或行动。

No eligible exact-period comparison means `insufficient`. A selected comparison is `limited` when scope compatibility is unknown, either report's coverage is partial/unknown, or existing overlap, missing-metric, zero-baseline, or relevant out-of-order checks apply. `ready` requires proven matching scope and complete observed coverage as well as the earlier checks. Historical caveats outside the selected pair remain visible without automatically lowering readiness; same-scope same-period revisions alone are informational.
没有合格准确时间段对比时为 `insufficient`。所选对比的范围兼容性未知、任一报告覆盖为部分或未知，或适用原有重叠、缺失指标、零基准及相关乱序检查时，为 `limited`。`ready` 除原有检查之外，还要求已证明范围相同及完整已观察覆盖。所选对之外的历史限制仍可见，不自动降低就绪度；仅有同范围同时间段修订属于信息提示。

Read-only APIs are `GET /api/v1/pages/{page_id}/quality` and `GET /api/v1/imports/{import_run_id}/quality`; the existing page-performance response also embeds page quality. Import quality reports facts without a page-readiness state. Stable codes, evidence fields, severity semantics, and provenance limits are in [data-quality.md](docs/data-quality.md).
只读 API 为 `GET /api/v1/pages/{page_id}/quality` 与 `GET /api/v1/imports/{import_run_id}/quality`；现有页面性能响应也内嵌页面质量。导入质量报告事实，不包含页面就绪度状态。稳定代码、证据字段、严重程度语义及来源追踪限制详见 [data-quality.md](docs/data-quality.md)。

## Report scope and observed coverage / 报告范围与已观察覆盖

A minimal `Site` identifies an explicitly observed or declared canonical GSC property; it does not verify account ownership. Pages are unique within `(site_id, url)`, including a separate unknown-site namespace. Existing unowned pages are never silently claimed. Runs store property/search/filter evidence once, with separate observed and declared origins. Unknown filters differ from an explicit complete empty filter list.
最小 `Site` 标识明确观察或声明的规范 GSC 属性，不验证账户归属。页面在 `(site_id, url)` 内唯一，其中包括独立未知站点命名空间。已有未知归属页面绝不被静默认领。导入仅存储一次属性、搜索与筛选证据，观察和声明来源保持独立。未知筛选不同于明确完整的空筛选列表。

The fingerprint excludes dates and evidence origin; equivalent canonical scope has the same identity. All essential dimensions known and matching means `compatible`; any explicit conflicting dimension means `incompatible`; otherwise compatibility is `unknown`. `GET /api/v1/imports/{import_run_id}` and history/page responses expose scope and coverage facts. See [report-scope.md](docs/report-scope.md) for declarations, exact canonicalization, comparison selection, migration safety, and limitations.
指纹排除日期与证据来源；等价规范范围具有相同身份。全部必要维度已知且匹配表示 `compatible`；任一明确维度冲突表示 `incompatible`；否则兼容性为 `unknown`。`GET /api/v1/imports/{import_run_id}` 及历史与页面响应公开范围和覆盖事实。声明、准确规范化、对比选择、迁移安全及限制详见 [report-scope.md](docs/report-scope.md)。

## Current metric provenance / 当前指标来源

`GET /api/v1/pages/{page_id}/provenance` returns four ordered metric entries with `known`, `unknown`, or `unavailable` status; the same object is embedded beside `quality` in the page-performance response. Known sources require a recorded link to the same page's snapshot with a supplied matching metric. Legacy non-`NULL` values without a valid link are `unknown`; current `NULL` values are `unavailable`. Equal historical values never establish missing provenance.
`GET /api/v1/pages/{page_id}/provenance` 返回四个按顺序排列的指标条目，状态为 `known`、`unknown` 或 `unavailable`；相同对象与 `quality` 并列内嵌在页面性能响应中。已知来源要求已记录关联指向同一页面且提供匹配指标的快照。没有有效关联的旧非 `NULL` 值为 `unknown`；当前 `NULL` 值为 `unavailable`。相等的历史值绝不建立缺失的来源。

Multiple validated known snapshot IDs produce the factual `current_state_not_single_snapshot` observation; unknown current sources produce `unknown_current_metric_provenance`. These observations leave comparison readiness unchanged because comparisons use historical snapshots; Phase 6 scope/coverage caveats independently refine readiness. Older reports applied later become current supplied sources; same-file/same-scope retries do not refresh values or links. See [current-provenance.md](docs/current-provenance.md) for the full rules, API summary semantics, and manual-edit limitations.
多个已验证的已知快照 ID 产生事实 `current_state_not_single_snapshot` 观察；未知当前来源产生 `unknown_current_metric_provenance`。这些观察不改变对比就绪度，因为对比使用历史快照；第六阶段范围与覆盖限制独立细化就绪度。后来应用的较早报告成为当前提供值的来源；同文件与同范围重试不刷新值或关联。完整规则、API 摘要语义及手动编辑限制详见 [current-provenance.md](docs/current-provenance.md)。

## Checks / 检查

Run each command block from the repository root in its own terminal.
在各自的终端中，从仓库根目录开始执行每组命令。

```sh
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic check
```

`alembic check` requires a running PostgreSQL database migrated to the latest revision. Unit tests do not require PostgreSQL.
`alembic check` 需要运行中的 PostgreSQL 数据库，且已迁移到最新版本。单元测试不需要 PostgreSQL。

To include the PostgreSQL integration tests, set `TEST_DATABASE_URL` to a local test database connection. These tests create and remove only a unique temporary schema; the database role must have permission to create schemas.
如需运行 PostgreSQL 集成测试，请将 `TEST_DATABASE_URL` 设置为本地测试数据库连接。这些测试仅创建和删除唯一的临时模式；数据库角色必须具备创建模式的权限。

```sh
cd backend
TEST_DATABASE_URL=postgresql+psycopg://seo_tool:seo_tool_dev@localhost:5432/seo_tool uv run pytest
```

```sh
cd frontend
npm run lint
npm run typecheck
npm run build
```

## Opportunity signals / 机会信号

`GET /api/v1/pages/{page_id}/opportunities` returns page eligibility, existing evidence-gate facts, and factual candidates. `GET /api/v1/opportunities` lists actual candidates with bounded pagination and optional `site_id` filtering, ordered neutrally by URL, opportunity type, and page ID. A ready page may return zero candidates or several different types. Neither endpoint creates `SEOOpportunity` records.
`GET /api/v1/pages/{page_id}/opportunities` 返回页面资格、已有证据门槛事实及事实候选。`GET /api/v1/opportunities` 对实际候选执行有界分页，可选按 `site_id` 筛选，并按 URL、机会类型及页面 ID 进行中立排序。就绪页面可返回零个候选，也可返回多个不同类型。两个接口均不创建 `SEOOpportunity` 记录。

The four v1 types are `traffic_decline`, `ctr_opportunity`, `ranking_decline`, and `impression_growth_gap`. They require the existing selected comparison and `ready` page readiness, explicitly compatible scopes, complete observed 28-day coverage on both reports, and valid rule metrics/baselines. `limited` or `insufficient` evidence generates zero candidates. Current applied metrics and their provenance do not replace historical snapshot evidence.
四种 V1 类型为 `traffic_decline`、`ctr_opportunity`、`ranking_decline` 及 `impression_growth_gap`。它们要求已有所选对比及 `ready` 页面就绪度、明确兼容范围、两个报告均有完整已观察 28 天覆盖，以及有效规则指标与基准。`limited` 或 `insufficient` 证据生成零个候选。当前应用指标及其来源不能替代历史快照证据。

These are transparent heuristic signals, not a claim about cause or the action to take. CTR deterioration alone does not establish a title/meta problem. Exact thresholds, inclusive/strict boundaries, evidence schema, examples, and scale limits are documented in [opportunity-engine.md](docs/opportunity-engine.md).
这些是透明的启发式信号，不声称变化原因或应该采取的行动。仅有 CTR 恶化不能证明标题或元描述问题。准确阈值、包含边界或严格边界、证据结构、示例及规模限制详见 [opportunity-engine.md](docs/opportunity-engine.md)。

## Opportunity prioritization / 机会优先级

`GET /api/v1/opportunities/prioritized` attaches `high`, `medium`, or `low` attention tiers to the same candidates using immutable `priority-v1` thresholds. It retains original evidence and exposes exact priority inputs, both high/medium threshold sets, a reason code, and a bilingual explanation. It orders candidates by tier, URL, type, and page ID, with candidate-based pagination and optional site/tier filtering. The original neutral endpoint is unchanged.
`GET /api/v1/opportunities/prioritized` 使用不可变 `priority-v1` 阈值，为相同候选添加 `high`、`medium` 或 `low` 关注层级。保留原始证据，并公开准确优先级输入、高与中两个阈值集合、原因代码及双语解释。按层级、URL、类型与页面 ID 排序候选，支持按候选分页及可选站点、层级筛选。原中立接口保持不变。

The workspace distinguishes no pages, unavailable history, scope/coverage limitations, ready evidence with no detected signal, and detected candidates. Priority is an attention heuristic, not commercial value, statistical confidence, predicted recovery, or a recommended action. An authorized real workbook was parsed read-only, but only one period with incomplete scope evidence was available. **Real-site calibration has not yet been performed.** See [opportunity-prioritization.md](docs/opportunity-prioritization.md) for every threshold, API contract, synthetic examples, limits, and real-data validation steps.
工作区区分没有页面、历史不可用、范围或覆盖限制、就绪但未检测到信号，以及已检测候选。优先级为关注启发式规则，不是商业价值、统计置信度、预计恢复或建议行动。已对授权真实工作簿进行只读解析，但只有一个时间段且范围证据不完整。**尚未进行真实站点校准。** 全部阈值、API 契约、合成示例、限制与真实数据验证步骤详见 [opportunity-prioritization.md](docs/opportunity-prioritization.md)。

## Structure and boundaries / 结构与边界

```text
backend/              FastAPI, GSC importer, SQLAlchemy, Alembic, tests / API、导入、数据层、迁移、测试
frontend/             Next.js import, history, evidence, priority workspace / 导入、历史、证据、优先级工作区
docs/architecture.md  Component boundaries and current scope / 模块边界与当前范围
docs/data-model.md    PostgreSQL fields and preservation rules / 字段与保留规则
docs/gsc-import.md    GSC formats, normalization, workflow, APIs / 格式、标准化、流程、API
docs/performance-history.md  History, dates, comparisons, limits / 历史、日期、对比、限制
docs/data-quality.md   Runtime observations and evidence readiness / 运行时观察与证据就绪度
docs/current-provenance.md  Per-field current sources and limits / 逐字段当前来源与限制
docs/report-scope.md   Property/search/filter evidence and date coverage / 属性、搜索、筛选证据及日期覆盖
docs/opportunity-engine.md  Runtime signals, evidence gate, exact v1 rules / 运行时信号、证据门槛、准确 V1 规则
docs/opportunity-prioritization.md  Attention tiers and real-data acceptance / 关注层级与真实数据验收
docs/localization.md   Simplified Chinese UI presentation boundaries / 简体中文界面展示边界
compose.yaml          Local PostgreSQL service only / 仅本地 PostgreSQL 服务
```

Imports and normalization implement the GSC file workflow. Separate deterministic modules handle comparison, data quality, current provenance, opportunity detection, and prioritization. Phase 8 extends supported date labels while preserving historical identity, scope, coverage, duplicates, and current provenance. Scoring, decisions, AI reasoning, and execution remain separate reserved boundaries. There are no recommendations, GSC/GA4 API integrations, AI calls, background jobs, autonomous actions, or production deployment.
导入与标准化模块实现 GSC 文件流程。独立确定性模块处理对比、数据质量、当前来源、机会检测及优先级。第八阶段扩展受支持日期标签，同时保留历史身份、范围、覆盖、重复及当前来源语义。评分、决策、AI 推理及执行仍为独立预留边界。没有建议、GSC/GA4 API 集成、AI 调用、后台任务、自主行动或生产部署。

Read [architecture](docs/architecture.md), [data model](docs/data-model.md), [GSC import](docs/gsc-import.md), [performance history](docs/performance-history.md), [data quality](docs/data-quality.md), [current provenance](docs/current-provenance.md), [report scope](docs/report-scope.md), [opportunity engine](docs/opportunity-engine.md), [prioritization](docs/opportunity-prioritization.md), and [agent instructions](AGENTS.md) before extending the application. Important documentation and non-trivial code comments/docstrings use English first, Chinese second.
扩展应用之前，请阅读[架构文档](docs/architecture.md)、[数据模型文档](docs/data-model.md)、[GSC 导入文档](docs/gsc-import.md)、[性能历史文档](docs/performance-history.md)、[数据质量文档](docs/data-quality.md)、[当前来源文档](docs/current-provenance.md)、[报告范围文档](docs/report-scope.md)、[机会引擎文档](docs/opportunity-engine.md)、[优先级文档](docs/opportunity-prioritization.md)和[代理开发指南](AGENTS.md)。重要文档及非简单代码注释、文档字符串使用英文在前、中文在后的双语形式。

The next milestone is **an MVP local trial using real TuffPlus GSC exports**, scoped and authorized separately. Neither Phase 8 nor the localization task starts Phase 9 or authorizes deployment or additional features. Real-site calibration has not been performed.
下一里程碑是另行定义范围并授权的 **使用真实 TuffPlus GSC 导出进行 MVP 本地试用**。第八阶段及本次本地化任务均不会启动第九阶段，也不授权部署或增加功能。尚未进行真实站点校准。

To stop the local database while retaining its data, run `docker compose down` from the repository root.
如需停止本地数据库并保留数据，请从仓库根目录运行 `docker compose down`。
