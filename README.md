# SEO Tool

An AI-assisted SEO operations system. Phase 1 provides a runnable foundation only.
由 AI 辅助的 SEO 运营系统。Phase 1 仅提供可运行的基础框架。

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

Open <http://localhost:3000>. The development page confirms that the frontend runs and offers a backend connection check. API documentation is at <http://localhost:8000/docs>.
打开 <http://localhost:3000>。开发页面确认前端已运行，并提供后端连接检查。API 文档位于 <http://localhost:8000/docs>。

```sh
curl http://localhost:8000/api/v1/health
```

The health endpoint checks application liveness only; it does not confirm database connectivity or migration readiness.
健康检查接口仅检查应用是否运行；它不确认数据库连接或迁移状态。

If you change the database credentials or port in the root `.env`, update `DATABASE_URL` in `backend/.env` to match. Configure allowed browser origins using the JSON array `CORS_ORIGINS`; the frontend uses `NEXT_PUBLIC_API_BASE_URL`. Compose binds PostgreSQL to the local machine only. Database credentials initialize a new volume; changing them does not update an existing database role.
如果修改根目录 `.env` 中的数据库凭据或端口，请同步修改 `backend/.env` 中的 `DATABASE_URL`。通过 JSON 数组 `CORS_ORIGINS` 配置允许的浏览器来源；前端使用 `NEXT_PUBLIC_API_BASE_URL`。Compose 仅在本机绑定 PostgreSQL 端口。数据库凭据用于初始化新数据卷；更改这些值不会更新已有数据库角色。

For an existing PostgreSQL instance, skip Compose, set `DATABASE_URL`, and apply the Alembic migration. The applications run on the host; Phase 1 does not containerize them.
使用已有 PostgreSQL 实例时，可跳过 Compose，设置 `DATABASE_URL` 并执行 Alembic 迁移。应用在宿主机上运行；Phase 1 不对应用进行容器化。

## Checks / 检查

Run each command block from the repository root in its own terminal.
在各自的终端中，从仓库根目录开始执行每组命令。

```sh
cd backend
uv run ruff check .
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
backend/              FastAPI, database models, Alembic migrations, tests
frontend/             Next.js, React, TypeScript development page
docs/architecture.md  Component boundaries and Phase 1 scope
docs/data-model.md    Initial PostgreSQL schema and field semantics
compose.yaml          Local PostgreSQL service only
```

The backend reserves separate modules for imports, normalization, analysis, scoring, decisions, AI reasoning, and future execution. Their business logic is not implemented. There are no SEO rules, integrations, AI provider calls, background jobs, or autonomous actions in Phase 1.
后端为导入、标准化、分析、评分、决策、AI 推理和未来执行预留独立模块，尚未实现其业务逻辑。Phase 1 不包含 SEO 规则、集成、AI 提供商调用、后台任务或自主行动。

Read [architecture](docs/architecture.md), [data model](docs/data-model.md), and [agent instructions](AGENTS.md) before extending the foundation.
扩展基础框架之前，请阅读[架构文档](docs/architecture.md)、[数据模型文档](docs/data-model.md)和[代理开发指南](AGENTS.md)。

To stop the local database while retaining its data, run `docker compose down` from the repository root.
如需停止本地数据库并保留数据，请从仓库根目录运行 `docker compose down`。
