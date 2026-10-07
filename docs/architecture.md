# Architecture / 架构

## Scope / 范围

Phases 1–4 established the runnable stack, manual Google Search Console (GSC) imports, historical snapshots, comparisons, and runtime data quality. Phase 5 records a current snapshot link for each supplied GSC metric in the existing import transaction and adds a separate read-only provenance view.
第一至四阶段建立可运行技术栈、手动 Google Search Console（GSC）导入、历史快照、对比及运行时数据质量。第五阶段在已有导入事务中，为每个提供的 GSC 指标记录当前快照关联，并增加独立的只读来源视图。

The long-term workflow is **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**. V1 is **DATA → ANALYZE → PRIORITIZE → RECOMMEND**. The current flow is **SOURCE FILE → IMPORT → SNAPSHOT → CURRENT VALUE + PROVENANCE**, alongside **HISTORY → COMPARISON → DATA QUALITY / EVIDENCE READINESS**. Current-state provenance and historical comparison remain separate. SEO judgments, scoring, recommendations, AI reasoning, and execution remain unimplemented.
长期流程为 **DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN**。V1 为 **DATA → ANALYZE → PRIORITIZE → RECOMMEND**。当前流程为 **SOURCE FILE → IMPORT → SNAPSHOT → CURRENT VALUE + PROVENANCE**，并列有 **HISTORY → COMPARISON → DATA QUALITY / EVIDENCE READINESS**。当前状态来源与历史对比保持独立。SEO 判断、评分、建议、AI 推理及执行仍未实现。

## Local runtime / 本地运行架构

```text
Browser / 浏览器
  └── Next.js + React + TypeScript
        ├── /                     Development and health page / 开发与健康检查页面
        ├── /imports/gsc          File preview and confirmation / 文件预览与确认
        ├── /imports/history      Successful import history / 成功导入历史
        ├── /pages                Paginated page metrics / 分页页面指标
        └── /pages/[id]           Current sources, history, quality / 当前来源、历史、质量
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
  imports/gsc/              GSC mapping, parsing, dates, persistence / GSC 映射、解析、日期、持久化
  normalization/            Deterministic URL and metric validation / 确定性 URL 与指标校验
  analysis/                 Comparison, quality, current provenance / 对比、质量、当前来源
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
- **Persistence:** One transaction upserts exact stored URLs, records the successful import, creates snapshots, and moves current provenance links for every supplied non-`NULL` metric. A blank input preserves both current value and link, while its new snapshot records `NULL`. Models define integrity without parsing files or making SEO judgments.
  **持久化：** 一个事务按精确存储的 URL 新增或更新、记录成功导入、创建快照，并为每个提供的非 `NULL` 指标移动当前来源关联。空白输入同时保留当前值与关联，新快照则记录 `NULL`。模型负责完整性，不解析文件，也不进行 SEO 判断。
- **Analysis:** `performance_comparison.py` selects compatible dated snapshots and calculates descriptive changes. `data_quality.py` consumes that output and existing history to explain evidence limitations. The quality module does not repeat comparison arithmetic, fill missing values, access the database, persist observations, or generate opportunities.
  **分析：** `performance_comparison.py` 选择具有兼容日期的快照并计算描述性变化。`data_quality.py` 使用该输出及已有历史解释证据限制。质量模块不重复对比计算、不填补缺失值、不访问数据库、不持久化观察，也不生成机会。
- **Current provenance:** `current_provenance.py` validates explicitly stored links against the same page's snapshot and current metric, then exposes known/unknown/unavailable statuses. Equality checks validate a recorded link; they never establish a missing link. Its observations are separate from comparison readiness.
  **当前来源：** `current_provenance.py` 根据同一页面的快照及当前指标校验明确存储的关联，再展示已知、未知或不可用状态。相等性检查校验已记录关联；绝不建立缺失关联。其观察与对比就绪度分离。
- **Future processing:** Scoring, decision-making, AI reasoning, and execution remain separate. Future AI provider details belong behind the AI boundary; recommendations must not cause external actions automatically.
  **未来处理：** 评分、决策、AI 推理与执行保持独立。未来 AI 供应商细节属于 AI 边界内部；建议不得自动触发外部行动。

## Preview and confirmation / 预览与确认

Preview parses and validates the upload without opening a database session or writing records. It reports source, worksheet, reporting endpoints/status, column mapping, row counts, errors, and normalized samples. Mapping, date extraction, and validation use deterministic code without AI.
预览解析并校验上传文件，不打开数据库会话，也不写入记录。它报告数据源、工作表、报告起止日期与状态、列映射、行数、错误及标准化样本。映射、日期提取与校验使用确定性代码，不使用 AI。

The browser retains the selected file. Confirmation submits that file again with `confirmed=true` and the returned `preview_hash`. The backend re-parses the entire upload and verifies its fingerprint before persistence; it does not trust client-provided normalized rows. Invalid rows or duplicate URLs block the entire import. No partial valid-row import is performed.
浏览器保留选中的文件。确认时再次提交该文件，并附带 `confirmed=true` 与返回的 `preview_hash`。后端在持久化前重新解析整个上传内容并校验指纹，不信任客户端提供的标准化行。无效行或重复 URL 会阻止整个导入；不会仅导入其中的有效行。

The hash binds confirmation to the previewed bytes and is also the unique identity of a successful `ImportRun`. Applying already-imported identical bytes returns the original import ID and skips every row without updating pages or creating history again. Different bytes are a new import even when the filename is unchanged. The fingerprint is not authentication, authorization, or a server-side preview session.
哈希将确认绑定到已预览的字节，也是成功 `ImportRun` 的唯一标识。应用已导入的相同字节会返回原导入 ID 并跳过每行，不更新页面，也不再次创建历史。字节不同即为新导入，即使文件名不变。指纹不是身份认证、权限控制或服务端预览会话。

See [gsc-import.md](gsc-import.md) for aliases, reporting-window checks, normalization, limits, request examples, and duplicate semantics.
列名别名、报告窗口检查、标准化、限制、请求示例与重复数据语义详见 [gsc-import.md](gsc-import.md)。

## Versioned API / 带版本的 API

| Endpoint / 接口 | Behavior / 行为 |
| --- | --- |
| `GET /api/v1/health` | Application liveness; no database access.<br>应用存活检查；不访问数据库。 |
| `POST /api/v1/imports/gsc/pages/preview` | Validate a CSV/XLSX upload; no persistence.<br>校验 CSV/XLSX 上传；不持久化。 |
| `POST /api/v1/imports/gsc/pages/apply` | Revalidate and atomically persist an explicitly confirmed file.<br>重新校验并原子持久化已显式确认的文件。 |
| `GET /api/v1/pages` | Read-only page metrics with basic pagination.<br>提供基本分页的只读页面指标。 |
| `GET /api/v1/imports` | Successful import history with pagination.<br>提供分页的成功导入历史。 |
| `GET /api/v1/pages/{page_id}/performance` | Current page, snapshots, comparison, quality, and sibling current provenance.<br>当前页面、快照、对比、质量及并列的当前来源。 |
| `GET /api/v1/pages/{page_id}/quality` | Page evidence readiness and factual observations.<br>页面证据就绪度及事实观察。 |
| `GET /api/v1/imports/{import_run_id}/quality` | Factual import-period observations; no page readiness.<br>导入时间段事实观察；不包含页面就绪度。 |
| `GET /api/v1/pages/{page_id}/provenance` | Four current-metric source entries and factual provenance observations.<br>四个当前指标来源条目及事实来源观察。 |

The health response remains `{"status":"ok","service":"seo-tool-api"}`. It confirms the API process can serve requests, not that PostgreSQL is ready. FastAPI's `/docs` describes the implemented request and response contracts. There are no page editing/deletion endpoints or opportunity APIs.
健康检查响应仍为 `{"status":"ok","service":"seo-tool-api"}`。它确认 API 进程能处理请求，不能证明 PostgreSQL 已就绪。FastAPI 的 `/docs` 描述已实现的请求与响应契约。当前没有页面编辑、删除接口或机会 API。

The browser calls the backend directly through `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`. `CORS_ORIGINS` is an explicit JSON list of frontend origins. CORS supports the separate local ports; it is not an access-control system.
浏览器通过 `NEXT_PUBLIC_API_BASE_URL` 直接调用后端，默认值为 `http://localhost:8000`。`CORS_ORIGINS` 是明确的前端来源 JSON 列表。CORS 支持本地不同端口；它不是访问控制系统。

## Schema and reporting windows / 数据库结构与报告窗口

Revision `0002_import_history` added import history and snapshots. Phase 5 head `0003_current_metric_provenance` creates the empty `page_metric_provenance` table, keyed by `(page_id, metric_name)` with one snapshot reference. Its check constraint permits only the four current GSC metrics. Existing pages, runs, snapshots, and opportunities are preserved without backfill. Schema changes remain explicit Alembic migrations, never automatic application-startup changes.
修订 `0002_import_history` 增加导入历史与快照。第五阶段最新修订 `0003_current_metric_provenance` 创建空 `page_metric_provenance` 表，以 `(page_id, metric_name)` 为键，并具有一个快照引用。其检查约束仅允许四个当前 GSC 指标。已有页面、导入、快照及机会保留，不回填。数据库结构变化仍由显式 Alembic 迁移管理，不能在应用启动时自动变更。

The supported import window remains latest 28 days. XLSX date worksheets can provide observed period endpoints; missing, malformed, or conflicting evidence produces `NULL` endpoints and `period_status="unknown"` while still allowing the page import. Dates are never inferred from filenames or import timestamps. Observed endpoints do not certify full 28-day coverage. See [performance-history.md](performance-history.md) for extraction, comparison selection, and missing-data semantics.
支持的导入窗口仍为最近 28 天。XLSX 日期工作表可提供已观察的时间段起止日期；缺失、损坏或冲突的证据会产生 `NULL` 起止日期及 `period_status="unknown"`，仍允许导入页面。绝不从文件名或导入时间推导日期。已观察的起止日期不能证明完整的 28 天覆盖。提取、对比选择及缺失数据语义详见 [performance-history.md](performance-history.md)。

The four write targets commit atomically: current pages, completed run, snapshots, and provenance links. Failure in any target rolls back all of them. A non-`NULL` same-value observation still moves its link to the new snapshot even when the page counts as skipped; zero is supplied data. Blank input and identical-file retries preserve existing links. `WebsitePage` remains latest successfully applied nonblank state, including older reports applied later. Comparison uses compatible report dates and raw snapshot metrics independently of these links.
四个写入目标原子提交：当前页面、已完成导入、快照及来源关联。任一目标失败均回滚全部写入。非 `NULL` 的相同值观察仍将关联移动到新快照，即使页面计为跳过；零是已提供数据。空白输入及相同文件重试保留已有关联。`WebsitePage` 仍为最近成功应用的非空白状态，包括后来应用的较早报告。对比独立于这些关联，使用兼容报告日期及原始快照指标。

Quality and provenance summaries are runtime, read-only responses; their observations are not stored. The shared page loader loads history once and calculates the Phase 3 comparison once. Performance/provenance requests add one provenance query for three SELECTs total; the dedicated quality route retains its two-query path. Both quality and provenance summaries are independent of the displayed snapshot page.
质量及来源摘要是运行时只读响应；其观察不存储。共享页面加载器仅加载一次历史并计算一次第三阶段对比。性能及来源请求增加一次来源查询，总计三个 SELECT；独立质量路由保留两次查询路径。质量与来源摘要均独立于显示的快照页。

## Evidence readiness / 证据就绪度

Observations have stable machine-readable codes, `info`/`warning`/`blocking` severity, page/import scope, bilingual messages, affected IDs, and structured evidence. Blocking describes missing comparison evidence and does not reject an otherwise valid import. Page readiness is `insufficient` when Phase 3 finds no compatible exact pair; `limited` when the selected pair has overlap, missing metrics, a known zero percentage baseline, or relevant out-of-order import evidence; otherwise `ready`.
观察包含稳定的机器可读代码、`info`、`warning` 或 `blocking` 严重程度、页面或导入范围、双语消息、受影响 ID 及结构化证据。阻断表示对比证据不足，不拒绝其他条件有效的导入。第三阶段未找到兼容准确时间段对时，页面就绪度为 `insufficient`；所选对存在重叠、缺失指标、已知零百分比基准或相关乱序导入证据时为 `limited`；否则为 `ready`。

Historical caveats outside the selected pair remain observations without automatically lowering readiness; same-period revisions alone are informational. Phase 5 provenance separately reports `current_state_not_single_snapshot` only for multiple validated known source IDs, and `unknown_current_metric_provenance` for non-`NULL` values without a valid recorded source. Neither alters Phase 4 readiness. Full contracts and provenance limitations are in [data-quality.md](data-quality.md) and [current-provenance.md](current-provenance.md).
所选对之外的历史限制保留为观察，不自动降低就绪度；仅有同时间段修订属于信息提示。第五阶段来源仅在多个已验证已知来源 ID 时单独报告 `current_state_not_single_snapshot`，并为没有有效已记录来源的非 `NULL` 值报告 `unknown_current_metric_provenance`。两者均不改变第四阶段就绪度。完整契约及来源限制详见 [data-quality.md](data-quality.md) 与 [current-provenance.md](current-provenance.md)。

## Configuration and limits / 配置与限制

Keep real credentials and environment files outside Git. `DATABASE_URL` uses `postgresql+psycopg://`. Next.js includes `NEXT_PUBLIC_API_BASE_URL` in browser code at build time; changing it requires restarting development or rebuilding. Installation and local commands are in [README.md](../README.md).
真实凭据与环境文件不得提交到 Git。`DATABASE_URL` 使用 `postgresql+psycopg://`。Next.js 在构建时将 `NEXT_PUBLIC_API_BASE_URL` 写入浏览器代码；修改后需要重启开发服务器或重新构建。安装与本地命令位于 [README.md](../README.md)。

Uploads are bounded to 5 MiB and 10,000 data rows. Preview returns at most 100 validation errors and 10 normalized samples while retaining full row counts. Source uploads are processed ephemerally and must not be committed; automated tests generate synthetic files. This is a local development interface without authentication or a production deployment plan.
上传限制为 5 MiB 与 10,000 个数据行。预览最多返回 100 个校验错误与 10 个标准化样本，同时保留完整行数统计。源上传文件仅作临时处理，不得提交；自动化测试生成合成文件。这是没有身份认证或生产部署方案的本地开发界面。

Phase 5 does not include GSC/GA4 APIs, query-level imports, indexing reports, SEO judgments, scoring, opportunity generation, a Decision Engine, AI calls, content generation, WordPress, outreach, background jobs, or autonomous actions.
第五阶段不包含 GSC/GA4 API、查询级导入、索引报告、SEO 判断、评分、机会生成、决策引擎、AI 调用、内容生成、WordPress、外链联系、后台任务或自主行动。

## Suggested Phase 6 / 建议的第六阶段

Define a small source-scope and reporting-coverage evidence contract for GSC imports: preserve only directly supplied property/filter metadata and observed date coverage, keep missing evidence unknown, and expose it read-only. Test matching and conflicting evidence before using it in descriptive comparisons. Avoid broader multi-site architecture, SEO scores, a Decision Engine, AI, or execution. Phase 6 has not started.
为 GSC 导入定义小型来源范围与报告覆盖证据契约：仅保留直接提供的属性、筛选元数据及已观察日期覆盖，缺失证据保持未知，并以只读方式展示。在描述性对比使用前，测试匹配及冲突证据。避免更广泛的多站点架构、SEO 评分、决策引擎、AI 或执行。第六阶段尚未开始。
