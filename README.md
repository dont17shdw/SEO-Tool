# SEO Tool

An AI-assisted SEO operations system. Phase 1 provides the foundation; Phase 2 adds manual GSC Pages imports; Phase 3 adds history and reporting-period comparisons; Phase 4 adds deterministic, read-only data-quality observations and evidence readiness.
由 AI 辅助的 SEO 运营系统。第一阶段提供基础框架；第二阶段增加手动 GSC 网页导入；第三阶段增加历史与报告时间段对比；第四阶段增加确定性的只读数据质量观察及证据就绪度。

Long-term workflow: `DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN`.
长期流程：`DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN`。

V1 scope: `DATA → ANALYZE → PRIORITIZE → RECOMMEND`.
V1 范围：`DATA → ANALYZE → PRIORITIZE → RECOMMEND`。

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

Open <http://localhost:3000> for the development health page, <http://localhost:3000/imports/gsc> to preview and confirm a GSC import, <http://localhost:3000/imports/history> for successful imports, and <http://localhost:3000/pages> for the read-only page list. Open a page from that list to see `/pages/[id]`, including current metrics, snapshots, comparison, and data-quality observations. API documentation is at <http://localhost:8000/docs>.
打开 <http://localhost:3000> 查看开发健康检查页面，打开 <http://localhost:3000/imports/gsc> 预览并确认 GSC 导入，打开 <http://localhost:3000/imports/history> 查看成功导入，打开 <http://localhost:3000/pages> 查看只读页面列表。从列表打开页面可查看 `/pages/[id]`，包括当前指标、快照、对比及数据质量观察。API 文档位于 <http://localhost:8000/docs>。

```sh
curl http://localhost:8000/api/v1/health
```

The health endpoint checks application liveness only; it does not confirm database connectivity or migration readiness.
健康检查接口仅检查应用是否运行；它不确认数据库连接或迁移状态。

If you change the database credentials or port in the root `.env`, update `DATABASE_URL` in `backend/.env` to match. Configure allowed browser origins using the JSON array `CORS_ORIGINS`; the frontend uses `NEXT_PUBLIC_API_BASE_URL`. Compose binds PostgreSQL to the local machine only. Database credentials initialize a new volume; changing them does not update an existing database role.
如果修改根目录 `.env` 中的数据库凭据或端口，请同步修改 `backend/.env` 中的 `DATABASE_URL`。通过 JSON 数组 `CORS_ORIGINS` 配置允许的浏览器来源；前端使用 `NEXT_PUBLIC_API_BASE_URL`。Compose 仅在本机绑定 PostgreSQL 端口。数据库凭据用于初始化新数据卷；更改这些值不会更新已有数据库角色。

For an existing PostgreSQL instance, skip Compose, set `DATABASE_URL`, and apply the Alembic migrations. The applications run on the host. Phase 3 adds revision `0002_import_history`: run `uv run alembic upgrade head` before using apply or history APIs. It adds history tables without changing existing page data or inventing history for earlier imports.
使用已有 PostgreSQL 实例时，可跳过 Compose，设置 `DATABASE_URL` 并执行 Alembic 迁移。应用在宿主机上运行。第三阶段增加修订 `0002_import_history`：使用应用或历史 API 前，请运行 `uv run alembic upgrade head`。它增加历史表，不改变已有页面数据，也不为此前导入编造历史。

Phase 4 requires no new migration: `0002_import_history` remains the schema head. Quality observations are calculated at request time from existing history and are not persisted.
第四阶段无需新增迁移：`0002_import_history` 仍为数据库结构最新修订。质量观察在请求时根据已有历史计算，不持久化。

## GSC import / GSC 导入

Export the GSC Pages performance table for the latest 28 days as CSV or XLSX. English and Chinese exports are supported, including the `Pages` / `网页` worksheet and localized headers. CSV must use UTF-8 (an optional BOM is supported).
将 GSC 网页性能表的最近 28 天数据导出为 CSV 或 XLSX。支持英文与中文导出，包括 `Pages` / `网页` 工作表及本地化列名。CSV 必须使用 UTF-8（支持可选的 BOM）。

Select the file at `/imports/gsc`, preview the detected mapping, counts, errors, and normalized samples, then explicitly confirm import. Preview does not write to the database. Correct every invalid or duplicate row before importing; imports are applied as one transaction. The `/pages` view displays the stored metrics with pagination.
在 `/imports/gsc` 选择文件，预览识别出的映射、行数、错误及标准化样本，再显式确认导入。预览不会写入数据库。导入前请修正每个无效或重复行；导入在一个事务内执行。`/pages` 视图分页显示已存储指标。

Only `clicks_28d`, `impressions_28d`, `ctr`, and `average_position` update the current page. Unknown metrics remain `NULL` on new pages; blank incoming values preserve existing metrics. Each new successful file also creates one `ImportRun` and one snapshot per imported page in the same transaction. Snapshots keep the upload's normalized values, including `NULL`, rather than copying preserved current-page values. Other page fields are preserved. Real exports are not stored permanently or used as automated test fixtures.
仅 `clicks_28d`、`impressions_28d`、`ctr` 与 `average_position` 更新当前页面。新页面的未知指标保持 `NULL`；传入的空值会保留已有指标。每个新的成功文件还会在同一事务中创建一个 `ImportRun` 及每个导入页面的一条快照。快照保留上传内容的标准化值，包括 `NULL`，不复制保留下来的当前页面值。其他页面字段保持不变。真实导出文件不会永久保存，也不会用作自动化测试数据。

XLSX date worksheets can provide exact observed reporting endpoints; unavailable or unreliable dates stay `NULL`. Identical successful file bytes are recognized by SHA-256 and return the original import ID without rewriting pages or duplicating history. Same filename with different bytes is a new import. Comparisons require two compatible, distinct exact periods and describe numeric changes without SEO judgments; missing values and zero baselines do not produce invented percentages.
XLSX 日期工作表可提供准确的已观察报告起止日期；不可用或不可靠的日期保持 `NULL`。相同的成功文件字节通过 SHA-256 识别，返回原导入 ID，不重写页面，也不重复创建历史。同名但字节不同的文件是新导入。对比需要两个兼容、不同且日期准确的时间段，只描述数值变化，不进行 SEO 判断；缺失值与零基准不会产生编造的百分比。

Uploads are limited to 5 MiB and 10,000 data rows. This is a local development workflow with no authentication. See [the GSC import contract](docs/gsc-import.md) for supported headers, reporting-window behavior, normalization, API requests, and current limitations.
上传限制为 5 MiB 与 10,000 个数据行。这是没有身份认证的本地开发流程。支持的列名、报告窗口行为、标准化、API 请求及当前限制详见 [GSC 导入契约](docs/gsc-import.md)。

## Data quality / 数据质量

The page history view shows `insufficient`, `limited`, or `ready` data readiness with structured factual observations. Quality reuses the selected Phase 3 comparison; it does not recalculate changes, fill missing metrics, mutate history, or create `SEOOpportunity` records. Readiness describes the evidence available for descriptive comparison, without an SEO score or action.
页面历史视图显示 `insufficient`、`limited` 或 `ready` 数据就绪度及结构化事实观察。质量复用第三阶段选中的对比，不重新计算变化、不填补缺失指标、不修改历史，也不创建 `SEOOpportunity` 记录。就绪度描述可用于描述性对比的证据，不包含 SEO 评分或行动。

No compatible exact-period comparison means `insufficient`. A selected comparison with overlap, missing metrics, a known zero count baseline, or relevant out-of-order import evidence is `limited`; otherwise it is `ready`. Caveats outside the selected pair remain visible without automatically lowering readiness. Same-period revisions alone are informational.
没有兼容准确时间段对比时为 `insufficient`。选中的对比存在重叠、缺失指标、已知零计数基准或相关乱序导入证据时为 `limited`；否则为 `ready`。所选对之外的限制仍可见，但不会自动降低就绪度。仅有同时间段修订属于信息提示。

Read-only APIs are `GET /api/v1/pages/{page_id}/quality` and `GET /api/v1/imports/{import_run_id}/quality`; the existing page-performance response also embeds page quality. Import quality reports facts without a page-readiness state. Stable codes, evidence fields, severity semantics, and provenance limits are in [data-quality.md](docs/data-quality.md).
只读 API 为 `GET /api/v1/pages/{page_id}/quality` 与 `GET /api/v1/imports/{import_run_id}/quality`；现有页面性能响应也内嵌页面质量。导入质量报告事实，不包含页面就绪度状态。稳定代码、证据字段、严重程度语义及来源追踪限制详见 [data-quality.md](docs/data-quality.md)。

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

## Structure and boundaries / 结构与边界

```text
backend/              FastAPI, GSC importer, SQLAlchemy, Alembic, tests / API、导入、数据层、迁移、测试
frontend/             Next.js import, current-page, history views / 导入、当前页面、历史视图
docs/architecture.md  Component boundaries and current scope / 模块边界与当前范围
docs/data-model.md    PostgreSQL fields and preservation rules / 字段与保留规则
docs/gsc-import.md    GSC formats, normalization, workflow, APIs / 格式、标准化、流程、API
docs/performance-history.md  History, dates, comparisons, limits / 历史、日期、对比、限制
docs/data-quality.md   Runtime observations and evidence readiness / 运行时观察与证据就绪度
compose.yaml          Local PostgreSQL service only / 仅本地 PostgreSQL 服务
```

Imports and normalization implement the GSC file workflow. The analysis boundary contains separate deterministic performance-comparison and data-quality modules, independent of source parsing. Scoring, decisions, AI reasoning, and execution remain reserved modules. Phase 4 does not implement SEO judgments or recommendations, GSC/GA4 API integrations, AI calls, background jobs, autonomous actions, or production deployment.
导入与标准化模块实现 GSC 文件流程。分析边界包含独立的确定性性能对比与数据质量模块，与来源解析分离。评分、决策、AI 推理及执行仍为预留模块。第四阶段不实现 SEO 判断或建议、GSC/GA4 API 集成、AI 调用、后台任务、自主行动或生产部署。

Read [architecture](docs/architecture.md), [data model](docs/data-model.md), [GSC import](docs/gsc-import.md), [performance history](docs/performance-history.md), [data quality](docs/data-quality.md), and [agent instructions](AGENTS.md) before extending the application. Important documentation and non-trivial code comments/docstrings use English first, Chinese second.
扩展应用之前，请阅读[架构文档](docs/architecture.md)、[数据模型文档](docs/data-model.md)、[GSC 导入文档](docs/gsc-import.md)、[性能历史文档](docs/performance-history.md)、[数据质量文档](docs/data-quality.md)和[代理开发指南](AGENTS.md)。重要文档及非简单代码注释、文档字符串使用英文在前、中文在后的双语形式。

To stop the local database while retaining its data, run `docker compose down` from the repository root.
如需停止本地数据库并保留数据，请从仓库根目录运行 `docker compose down`。
