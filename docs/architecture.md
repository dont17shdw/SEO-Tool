# Architecture / 架构

## Scope / 范围

Phases 1–5 established the runnable stack, manual GSC Pages imports, historical snapshots, deterministic comparisons, runtime data quality, and per-field current provenance. Phase 6 adds explicit site/report-scope evidence and observed-date coverage, completing the planned data foundation without an SEO Opportunity Engine.
第一至五阶段建立可运行技术栈、手动 GSC 网页导入、历史快照、确定性对比、运行时数据质量及逐字段当前来源。第六阶段增加明确站点与报告范围证据及已观察日期覆盖，完成计划中的数据基础，不包含 SEO 机会引擎。

The long-term workflow is **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**; V1 is **DATA → ANALYZE → PRIORITIZE → RECOMMEND**. The implemented flow is **GSC SOURCE → IMPORT → REPORT SCOPE → SNAPSHOT → CURRENT PROVENANCE → COMPARISON → DATA QUALITY**. Current applied state remains distinct from historical comparison evidence.
长期流程为 **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**；V1 为 **DATA → ANALYZE → PRIORITIZE → RECOMMEND**。已实现流程为 **GSC SOURCE → IMPORT → REPORT SCOPE → SNAPSHOT → CURRENT PROVENANCE → COMPARISON → DATA QUALITY**。当前应用状态与历史对比证据保持独立。

## Local runtime / 本地运行架构

```text
Browser / 浏览器
  └── Next.js + React + TypeScript
        ├── /                     Development health page / 开发健康检查页
        ├── /imports/gsc          Scope declaration, preview, apply / 范围声明、预览、应用
        ├── /imports/history      Import scope and coverage / 导入范围与覆盖
        ├── /pages                Paginated current page list / 分页当前页面列表
        └── /pages/[id]           History, scope, quality, sources / 历史、范围、质量、来源
              └── FastAPI /api/v1
                    └── SQLAlchemy → PostgreSQL
Alembic → Explicit migrations / 显式迁移
```

Applications run as local processes; Docker Compose runs PostgreSQL only. The backend uses synchronous SQLAlchemy 2 sessions and psycopg 3. There is no task queue, server-side preview session, permanent upload store, production authentication, or account-management system.
应用以本地进程运行；Docker Compose 仅运行 PostgreSQL。后端使用 SQLAlchemy 2 同步会话与 psycopg 3。没有任务队列、服务端预览会话、永久上传存储、生产身份认证或账户管理系统。

## Module boundaries / 模块边界

```text
backend/app/
  api/v1/                   HTTP requests and response schemas / HTTP 请求与响应结构
  config/                   Environment settings / 环境配置
  db/                       Sessions and base metadata / 会话与基础元数据
  models/                   Sites, pages, history, current links / 站点、页面、历史、当前关联
  imports/gsc/              Source parsing, metadata, persistence / 来源解析、元数据、持久化
  normalization/            URL/metric/scope canonicalization / URL、指标、范围规范化
  analysis/                 Scope compatibility, comparison, quality, provenance / 范围兼容、对比、质量、来源
  scoring/                  Reserved calculation boundary / 预留计算边界
  decision_engine/          Reserved decision boundary / 预留决策边界
  ai/                       Reserved semantic reasoning boundary / 预留语义推理边界
  execution/                Reserved future actions boundary / 预留未来行动边界
backend/alembic/            Explicit schema migrations / 显式数据库结构迁移
backend/tests/              Synthetic and PostgreSQL tests / 合成与 PostgreSQL 测试
frontend/src/               Development routes and typed client / 开发路由与带类型客户端
docs/                       Bilingual contracts and setup / 双语契约与设置
```

- **Ingestion:** The existing standard-library CSV reader and lightweight `openpyxl` reader detect English/Chinese Pages semantics. Separate source-specific metadata parsing extracts only supported Filters facts and reliable daily dates. Unsupported or absent scope remains unknown; the parser never calls a GSC API or infers identity from page URLs or filenames.
  **导入：** 现有标准库 CSV 读取器及轻量 `openpyxl` 读取器识别英文与中文网页语义。独立的数据源元数据解析仅提取受支持的筛选事实与可靠每日日期。不支持或缺失范围保持未知；解析器绝不调用 GSC API，也不从页面 URL 或文件名推导身份。
- **Normalization:** Validate URLs/metrics as before; canonicalize supported property, search, and structured filter values deterministically. The canonical identity excludes date range and evidence origin. Preserve observed and declared evidence separately, rather than storing arbitrary filter prose as an identity.
  **标准化：** 沿用 URL 与指标校验；确定性规范化受支持属性、搜索及结构化筛选值。规范身份排除日期范围与证据来源。分别保留观察及声明证据，不将任意筛选描述作为身份。
- **Persistence:** Resolve a minimal property-bound Site and upsert pages within `(site_id, url)`. Unknown site ownership is a separate namespace and never automatically assigned. Site creation, page updates, completed run, snapshots, and supplied metric links share one transaction. Report-level scope/coverage belongs on `ImportRun`, not copied into every snapshot.
  **持久化：** 解析最小属性绑定站点，在 `(site_id, url)` 内新增或更新页面。未知站点归属为独立命名空间，绝不自动分配。站点创建、页面更新、已完成导入、快照及已提供指标关联共用一个事务。报告级范围与覆盖存储在 `ImportRun`，不复制到每个快照。
- **Analysis:** Scope compatibility returns `compatible`, `incompatible`, or `unknown` using explicit facts. Comparison excludes conflicting scope and reuses established date/duration arithmetic. Quality consumes that selected pair and full history; it does not repeat calculations, write judgments, or generate opportunities.
  **分析：** 范围兼容性根据明确事实返回 `compatible`、`incompatible` 或 `unknown`。对比排除冲突范围，复用已有日期、时长与数值计算。质量使用该所选对及完整历史；不重复计算、不写入判断，也不生成机会。
- **Current provenance:** Recorded page/metric/snapshot links retain Phase 5 meaning. A supplied same value or measured zero refreshes a link; blanks preserve value and link. An older period applied later can remain current. Scope neither rewrites provenance nor establishes missing legacy links.
  **当前来源：** 已记录页面、指标与快照关联保留第五阶段含义。提供的相同值或测得零刷新关联；空白保留值与关联。后来应用的较早时间段仍可成为当前来源。范围不重写来源，也不建立缺失旧关联。
- **Future processing:** Calculations remain deterministic. Scoring, decisions, model-independent semantic AI reasoning, and execution remain separate reserved modules. No implemented read view triggers external actions.
  **未来处理：** 计算保持确定性。评分、决策、独立于模型的语义 AI 推理及执行仍为独立预留模块。已实现读取视图不触发外部行动。

## Preview, evidence, and duplicate identity / 预览、证据与重复身份

Preview parses the file and optional explicit declaration without a database session. It shows detected and declared scope, unresolved fields, canonical identity, period endpoints, distinct observed date count, consecutiveness, and coverage, alongside existing row mapping/validation. The retained file and declaration are resubmitted on Apply.
预览解析文件及可选明确声明，不使用数据库会话。它在已有行映射与校验之外，显示识别及声明范围、未解决字段、规范身份、时间段起止值、不同已观察日期数量、连续性及覆盖。应用时重新提交保留的文件与声明。

`file_hash` is the SHA-256 of raw bytes. `preview_hash` separately binds those bytes and the normalized declaration/evidence. Apply re-parses and verifies that binding before database writes; changing scope requires another preview. The successful-import unique key is `(source, source_type, file_hash, scope_fingerprint)`. Equal bytes and equal canonical scope return the original run with no page/history/provenance updates. Another explicit scope creates another run; evidence origin and dates do not change canonical scope identity. Hashes provide consistency and duplicate identity, not authentication.
`file_hash` 是原始字节的 SHA-256。`preview_hash` 单独绑定这些字节及标准化声明与证据。应用在数据库写入前重新解析并验证该绑定；范围改变需要再次预览。成功导入唯一键为 `(source, source_type, file_hash, scope_fingerprint)`。相同字节与相同规范范围返回原导入，不更新页面、历史或来源。另一明确范围创建另一导入；证据来源与日期不改变规范范围身份。哈希提供一致性及重复身份，不提供身份认证。

Workbook metadata is not an exhaustive scope certificate. The previously inspected localized export provided Web search type and the past-28-days filter but no property or complete non-date filter ledger. Supported observed facts can be supplemented by explicit declarations, preserving their origins. Unsupported metadata cannot be promoted to proven scope. See [report-scope.md](report-scope.md) and [gsc-import.md](gsc-import.md).
工作簿元数据不是穷尽范围证明。此前检查的本地化导出提供网络搜索类型及过去 28 天筛选，但没有属性或完整非日期筛选清单。受支持观察事实可通过明确声明补充，同时保留来源。不支持元数据不能提升为已证明范围。详见 [report-scope.md](report-scope.md) 与 [gsc-import.md](gsc-import.md)。

## Versioned API / 带版本 API

| Endpoint / 接口 | Behavior / 行为 |
| --- | --- |
| `GET /api/v1/health` | Process liveness without database access.<br>不访问数据库的进程存活检查。 |
| `POST /api/v1/imports/gsc/pages/preview` | File and scope preview without writes.<br>不写入的文件与范围预览。 |
| `POST /api/v1/imports/gsc/pages/apply` | Revalidate explicit confirmation and commit atomically.<br>重新校验明确确认，原子提交。 |
| `GET /api/v1/pages` | Paginated current pages with nullable site IDs.<br>含可空站点 ID 的分页当前页面。 |
| `GET /api/v1/imports` | Paginated successful runs with scope/coverage facts.<br>含范围与覆盖事实的分页成功导入。 |
| `GET /api/v1/imports/{import_run_id}` | Read one run's metadata, scope, and coverage.<br>读取一个导入的元数据、范围及覆盖。 |
| `GET /api/v1/pages/{page_id}/performance` | Current page, snapshots, selected comparison facts, quality, and provenance.<br>当前页面、快照、所选对比事实、质量及来源。 |
| `GET /api/v1/pages/{page_id}/quality` | Runtime evidence readiness and observations.<br>运行时证据就绪度与观察。 |
| `GET /api/v1/imports/{import_run_id}/quality` | Runtime import facts without page readiness.<br>不包含页面就绪度的运行时导入事实。 |
| `GET /api/v1/pages/{page_id}/provenance` | Four current-metric source entries, unchanged semantics.<br>四个当前指标来源条目，语义不变。 |

The browser calls `NEXT_PUBLIC_API_BASE_URL` directly, defaulting to `http://localhost:8000`; `CORS_ORIGINS` lists allowed browser origins. `/docs` describes typed contracts. There are no editing/deletion, opportunity, site-management, or account-management endpoints.
浏览器直接调用 `NEXT_PUBLIC_API_BASE_URL`，默认 `http://localhost:8000`；`CORS_ORIGINS` 列出允许浏览器来源。`/docs` 描述带类型契约。没有编辑删除、机会、站点管理或账户管理接口。

## Comparison and evidence readiness / 对比与证据就绪度

Revisions are grouped by exact scope identity as well as page/source/window/dates before selecting their latest imported revision. Equal dates alone cannot replace another scope's evidence. Each canonical scope stream contributes its newest two distinct periods; explicit conflicts are excluded and an eligible pair in another stream can remain selected when a newer singleton has no partner. Partial/legacy unknown-scope pairs remain descriptive and explicitly labeled `unknown`; they never become proven compatible because URLs or metrics match. Conflict evidence uses bounded representative witnesses, without enumerating every historical pair.
在选择最近导入修订之前，修订按准确范围身份及页面、来源、窗口与日期分组。仅有日期相同不能替换另一范围的证据。每个规范范围流提供最近两个不同时间段；明确冲突被排除，较新单条记录没有伙伴时，另一范围流中的合格对仍可被选中。部分或旧未知范围对仍为描述性结果，明确标为 `unknown`；不会因 URL 或指标匹配而成为已证明兼容。冲突证据使用有界代表记录，不枚举全部历史对。

Reliable date sets establish `complete` only for 28 distinct consecutive dates spanning exactly 28 calendar days. Other reliable sets are `partial`; unavailable, malformed, conflicting, and CSV evidence is `unknown`. Endpoints alone do not establish full coverage. Coverage describes observed daily dates, not the completeness of all page rows.
可靠日期集合仅在 28 个不同连续日期恰好跨越 28 个日历天时建立 `complete`。其他可靠集合为 `partial`；不可用、损坏、冲突及 CSV 证据为 `unknown`。仅有起止日期不建立完整覆盖。覆盖描述已观察每日日期，不描述全部页面行的完整性。

No eligible pair means `insufficient`. A selected unknown-scope pair or either selected report's partial/unknown coverage means `limited`, alongside prior overlap, missing metrics, zero baselines, and relevant out-of-order checks. `ready` additionally requires proven compatible scope and complete observed coverage. Stable new observations are `unknown_report_scope`, `incompatible_report_scope`, `incomplete_date_coverage`, and `unknown_date_coverage`. Historical caveats outside the selected pair stay visible without automatically lowering readiness. Current-provenance observations remain separate. See [performance-history.md](performance-history.md) and [data-quality.md](data-quality.md).
没有合格对时为 `insufficient`。所选未知范围对或任一所选报告的部分、未知覆盖表示 `limited`，并保留此前重叠、缺失指标、零基准与相关乱序检查。`ready` 另外要求已证明范围兼容与完整已观察覆盖。稳定新增观察为 `unknown_report_scope`、`incompatible_report_scope`、`incomplete_date_coverage` 及 `unknown_date_coverage`。所选对之外的历史限制保持可见，不自动降低就绪度。当前来源观察保持独立。详见 [performance-history.md](performance-history.md) 与 [data-quality.md](data-quality.md)。

The shared page loader reads complete history once and computes comparison once for quality and provenance. Run-level scope and coverage are reused from the existing join; snapshot pagination cannot alter the selected comparison or evidence summaries. Full history remains in memory for development-scale data.
共享页面读取流程仅读取一次完整历史，计算一次对比并复用于质量与来源。导入级范围与覆盖从已有连接复用；快照分页不能改变所选对比或证据摘要。完整历史仍在内存中处理，适用于开发规模数据。

## Migration and limits / 迁移与限制

Head revision `0004_report_scope` creates `sites`, adds nullable ownership and report evidence, and changes URL/duplicate-import uniqueness. All five legacy tables, every original value/timestamp, and current links are preserved. Unknown legacy site, scope, and coverage remain unknown. No production property or prior evidence is fabricated. Downgrade checks whether the old global constraints can be restored and refuses atomically if duplicate scoped URLs or file identities would violate them; it never deletes history or rewrites hashes. See [data-model.md](data-model.md).
最新修订 `0004_report_scope` 创建 `sites`，增加可空归属及报告证据，并改变 URL 与重复导入唯一性。已有五个表、每个原始值与时间戳及当前关联均保留。未知旧站点、范围及覆盖保持未知。不编造生产属性或此前证据。降级检查能否恢复旧全局约束；如果按范围存储的重复 URL 或文件身份违反约束，则原子拒绝，绝不删除历史或重写哈希。详见 [data-model.md](data-model.md)。

Uploads retain existing 5 MiB/10,000-row limits, ephemeral processing, and synthetic tests. Site identifiers are explicit evidence, not authenticated property ownership. Unknown/unsupported source metadata, source accuracy, complete page exports, statistical significance, and unobserved changes cannot be certified. Real exports, credentials, and scratch data stay outside Git. The application still excludes SEO opportunities, scoring, recommendations, Decision Engine logic, AI calls, GSC/GA4 APIs, WordPress, outreach, scheduling, and execution.
上传沿用 5 MiB 与 10,000 行限制、临时处理及合成测试。站点标识是明确证据，不是已认证属性归属。未知或不支持来源元数据、来源准确性、完整页面导出、统计显著性与未观察变化不能获证明。真实导出、凭据及临时数据保留在 Git 之外。应用仍不包含 SEO 机会、评分、建议、决策引擎逻辑、AI 调用、GSC/GA4 API、WordPress、外链联系、调度及执行。

## Suggested Phase 7 / 建议的第七阶段

The next bounded step is an evidence-first SEO Opportunity Engine: define a small deterministic opportunity taxonomy and explicit evidence requirements, generate reviewable page-level candidates only when scope/coverage/readiness supports the rule, and preserve source IDs and explanations. Keep insufficient evidence explicit. Defer opportunity scoring, prioritization, AI, recommendations that execute changes, and integrations until separately specified. Phase 7 has not started.
下一项有界步骤为证据优先的 SEO 机会引擎：定义小型确定性机会分类及明确证据要求，仅在范围、覆盖与就绪度支持规则时，生成可审阅页面级候选，并保留来源 ID 与解释。明确保留证据不足。机会评分、优先级、AI、执行修改的建议及集成延后至分别定义范围。第七阶段尚未开始。
