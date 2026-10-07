# Data model / 数据模型

## Purpose / 目的

Phase 1 defines two PostgreSQL tables: `website_pages` stores a page and its latest known SEO metrics; `seo_opportunities` stores potential actions related to that page. These are persistence contracts only. No ingestion, SEO rule, scoring algorithm, or recommendation process is implemented yet.

第一阶段定义两个 PostgreSQL 表：`website_pages` 存储页面及其最新已知 SEO 指标；`seo_opportunities` 存储与该页面相关的潜在行动。这些仅是持久化契约，尚未实现数据导入、SEO 规则、评分算法或建议流程。

SQLAlchemy models define the schema and Alembic creates it through an explicit migration. Model changes require a corresponding migration. FastAPI startup and the health endpoint do not create tables or check database connectivity.

SQLAlchemy 模型定义数据库结构，Alembic 通过显式迁移创建结构。模型变化需要对应的迁移。FastAPI 启动与健康检查接口均不创建表，也不检查数据库连接。

## Shared conventions / 共同约定

- **IDs:** PostgreSQL `UUID` primary keys use an application-side `uuid4` default. No PostgreSQL UUID extension is required. Direct SQL inserts must supply IDs.
- **标识符：** PostgreSQL `UUID` 主键使用应用侧 `uuid4` 默认值，无需 PostgreSQL UUID 扩展。直接通过 SQL 插入时必须提供 ID。
- **Unknown values:** Nullable metrics use `NULL` for unknown or unobserved values. Zero means a measured zero. Do not convert missing metrics to zero during future imports.
- **未知值：** 可空指标以 `NULL` 表示未知或尚未观察的值。零表示已测量且结果为零。未来导入时不得将缺失指标转换为零。
- **Numeric values:** SQLAlchemy uses decimal values for `Numeric` fields. Store CTR and confidence as fractions from `0` to `1`; for example, `0.025` means 2.5%.
- **数值：** SQLAlchemy 为 `Numeric` 字段使用十进制值。点击率与置信度以 `0` 至 `1` 的比例存储；例如，`0.025` 表示 2.5%。
- **Time:** PostgreSQL `TIMESTAMP WITH TIME ZONE` represents instants. Application code and documentation use UTC; display and input/output offsets must be handled explicitly by future APIs.
- **时间：** PostgreSQL `TIMESTAMP WITH TIME ZONE` 表示时间点。应用代码及文档采用 UTC；未来 API 必须明确处理显示及输入输出中的时区偏移。
- **Classification:** Page types, index statuses, opportunity types, severity, risk levels, and opportunity statuses are strings. Phase 1 does not establish a fixed taxonomy or derive classifications.
- **分类：** 页面类型、索引状态、机会类型、严重程度、风险级别及机会状态均使用字符串。第一阶段不定义固定分类体系，也不推导分类。

## WebsitePage / 网站页面

The `WebsitePage` model maps to `website_pages`. One row represents one unique stored URL. The URL uniqueness constraint uses the stored string; equivalent URLs differing by case, fragments, or other formatting can remain distinct. URL normalization belongs to the future normalization layer.

`WebsitePage` 模型对应 `website_pages` 表。一条记录表示一个唯一的已存储 URL。URL 唯一性约束使用实际存储的字符串；大小写、片段或其他格式不同的等价 URL 仍可能被视为不同值。URL 标准化属于未来标准化层的职责。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning and constraints / 含义与约束 |
| --- | --- | --- | --- |
| `id` | `UUID` | No / 否 | Primary key; application-generated UUID.<br>主键；由应用生成的 UUID。 |
| `url` | `TEXT` | No / 否 | Unique stored page URL; no automatic normalization.<br>唯一的已存储页面 URL；不自动标准化。 |
| `page_type` | `VARCHAR(50)` | Yes / 是 | Optional page classification.<br>可选的页面分类。 |
| `title` | `TEXT` | Yes / 是 | Last known page title.<br>最新已知的页面标题。 |
| `primary_keyword` | `TEXT` | Yes / 是 | Optional primary target keyword.<br>可选的主要目标关键词。 |
| `clicks_7d` | `BIGINT` | Yes / 是 | Clicks over the latest 7-day window; ≥ 0.<br>最近 7 天窗口的点击数；≥ 0。 |
| `clicks_28d` | `BIGINT` | Yes / 是 | Clicks over the latest 28-day window; ≥ 0.<br>最近 28 天窗口的点击数；≥ 0。 |
| `clicks_previous_28d` | `BIGINT` | Yes / 是 | Clicks over the preceding 28-day comparison window; ≥ 0.<br>此前 28 天对比窗口的点击数；≥ 0。 |
| `impressions_7d` | `BIGINT` | Yes / 是 | Impressions over the latest 7-day window; ≥ 0.<br>最近 7 天窗口的展示数；≥ 0。 |
| `impressions_28d` | `BIGINT` | Yes / 是 | Impressions over the latest 28-day window; ≥ 0.<br>最近 28 天窗口的展示数；≥ 0。 |
| `impressions_previous_28d` | `BIGINT` | Yes / 是 | Impressions over the preceding 28-day comparison window; ≥ 0.<br>此前 28 天对比窗口的展示数；≥ 0。 |
| `ctr` | `NUMERIC(7,6)` | Yes / 是 | Click-through-rate fraction; 0 ≤ value ≤ 1.<br>点击率比例；0 ≤ 值 ≤ 1。 |
| `average_position` | `NUMERIC(10,4)` | Yes / 是 | Reported average search position; ≥ 0.<br>数据源报告的平均搜索排名；≥ 0。 |
| `indexed` | `BOOLEAN` | Yes / 是 | Latest known indexing flag; `NULL` means unknown.<br>最新已知的索引标记；`NULL` 表示未知。 |
| `index_status` | `VARCHAR(50)` | Yes / 是 | Optional descriptive indexing classification.<br>可选的索引状态分类描述。 |
| `word_count` | `INTEGER` | Yes / 是 | Observed word count; ≥ 0.<br>已观察到的字词数；≥ 0。 |
| `internal_links_in` | `INTEGER` | Yes / 是 | Observed incoming internal links; ≥ 0.<br>已观察到的站内入链数；≥ 0。 |
| `internal_links_out` | `INTEGER` | Yes / 是 | Observed outgoing internal links; ≥ 0.<br>已观察到的站内出链数；≥ 0。 |
| `backlinks` | `INTEGER` | Yes / 是 | Observed backlink count; ≥ 0.<br>已观察到的外链数；≥ 0。 |
| `business_value` | `NUMERIC(12,4)` | Yes / 是 | Optional non-negative business value; no scale or unit is defined yet.<br>可选的非负业务价值；尚未定义量表或单位。 |
| `last_updated` | `TIMESTAMP WITH TIME ZONE` | Yes / 是 | Last known update to page content; supplied by future data ingestion.<br>最新已知的页面内容更新时间；由未来的数据导入提供。 |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Record insertion time; database default `now()`.<br>记录插入时间；数据库默认值为 `now()`。 |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Record modification time; database insert default `now()`, SQLAlchemy update behavior below.<br>记录修改时间；插入时数据库默认值为 `now()`，SQLAlchemy 更新行为见下文。 |

The six click/impression fields, word count, link counts, and backlinks have non-negative database check constraints. CTR is constrained to `[0, 1]`; average position and business value are non-negative. These constraints prevent invalid basic values; they do not establish SEO thresholds, verify source accuracy, or calculate derived metrics.

六个点击与展示字段、字词数、链接数及外链数具有非负数据库检查约束。点击率限制在 `[0, 1]`，平均排名与业务价值要求非负。这些约束防止基本无效值，但不定义 SEO 阈值、不验证数据源准确性，也不计算派生指标。

`last_updated` describes the page content, while `updated_at` describes the database record. SQLAlchemy supplies `now()` when it emits an update without an explicit `updated_at` value. This is an ORM-side update default, not a PostgreSQL trigger: direct SQL updates and updates outside this metadata must maintain `updated_at` explicitly.

`last_updated` 描述页面内容的更新时间，而 `updated_at` 描述数据库记录的更新时间。当 SQLAlchemy 发出未显式设置 `updated_at` 的更新时，它会提供 `now()`。这是 ORM 侧更新默认行为，并非 PostgreSQL 触发器：直接 SQL 更新及不经过此元数据的更新必须显式维护 `updated_at`。

## SEOOpportunity / SEO 机会

The `SEOOpportunity` model maps to `seo_opportunities`. Each opportunity belongs to exactly one page. The schema can store future recommendations, but Phase 1 has no writer API, opportunity generator, or scoring implementation.

`SEOOpportunity` 模型对应 `seo_opportunities` 表。每个机会只能属于一个页面。数据库结构可存储未来的建议，但第一阶段没有写入 API、机会生成器或评分实现。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning and constraints / 含义与约束 |
| --- | --- | --- | --- |
| `id` | `UUID` | No / 否 | Primary key; application-generated UUID.<br>主键；由应用生成的 UUID。 |
| `page_id` | `UUID` | No / 否 | Foreign key to `website_pages.id`.<br>关联 `website_pages.id` 的外键。 |
| `opportunity_type` | `VARCHAR(80)` | No / 否 | Future opportunity classification; no fixed taxonomy.<br>未来的机会分类；无固定分类体系。 |
| `severity` | `VARCHAR(30)` | Yes / 是 | Optional severity classification; no rules yet.<br>可选的严重程度分类；尚无规则。 |
| `opportunity_score` | `NUMERIC(12,4)` | Yes / 是 | Non-negative score; formula and scale remain undefined.<br>非负评分；公式与量表尚未定义。 |
| `confidence` | `NUMERIC(7,6)` | Yes / 是 | Confidence fraction; 0 ≤ value ≤ 1.<br>置信度比例；0 ≤ 值 ≤ 1。 |
| `recommended_action` | `TEXT` | No / 否 | Proposed action text; does not execute the action.<br>建议行动文本；不会执行该行动。 |
| `reason` | `TEXT` | No / 否 | Explanation supporting the proposed action.<br>支持建议行动的解释。 |
| `expected_impact` | `TEXT` | Yes / 是 | Descriptive impact estimate; no enforced quantitative unit.<br>描述性的预期影响；不约束量化单位。 |
| `estimated_effort` | `TEXT` | Yes / 是 | Descriptive effort estimate; no enforced quantitative unit.<br>描述性的预计工作量；不约束量化单位。 |
| `risk_level` | `VARCHAR(30)` | Yes / 是 | Optional risk classification.<br>可选的风险分类。 |
| `status` | `VARCHAR(30)` | No / 否 | Record status; database default `'pending'`; no state machine yet.<br>记录状态；数据库默认值为 `'pending'`；尚无状态机。 |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Record insertion time; database default `now()`.<br>记录插入时间；数据库默认值为 `now()`。 |

The database constrains `opportunity_score` to non-negative values and `confidence` to `[0, 1]`. It deliberately does not impose a maximum score, severity ordering, allowed status transitions, or AI-derived meaning. Future scoring must document its scale and inputs before populating scores.

数据库约束 `opportunity_score` 为非负值，`confidence` 位于 `[0, 1]`。它不规定评分上限、严重程度排序、允许的状态变化或 AI 推导含义。未来评分功能必须在写入评分前记录量表及输入。

## Relationships and indexes / 关联与索引

```text
website_pages.id (UUID)
  └── seo_opportunities.page_id (UUID, NOT NULL)
      One page → zero or more opportunities
      一个页面 → 零个或多个机会
```

The foreign key uses `ON DELETE RESTRICT`. Deleting a page with existing opportunities is rejected by PostgreSQL. The ORM relationship does not automatically delete child opportunities or set their foreign keys to `NULL`; `passive_deletes="all"` leaves enforcement to the database. A future deletion flow must handle related records explicitly. Phase 1 provides no deletion API.

外键采用 `ON DELETE RESTRICT`。PostgreSQL 会拒绝删除仍有关联机会的页面。ORM 关联不会自动删除子机会，也不会将其外键设为 `NULL`；`passive_deletes="all"` 将约束执行交给数据库。未来删除流程必须明确处理关联记录。第一阶段不提供删除 API。

PostgreSQL automatically indexes both primary keys and the unique `website_pages.url` constraint. Explicit indexes on `seo_opportunities.page_id` and `seo_opportunities.status` support future per-page and status-filtered queries. No speculative analytics indexes are added.

PostgreSQL 自动为两个主键及 `website_pages.url` 唯一性约束创建索引。`seo_opportunities.page_id` 和 `seo_opportunities.status` 的显式索引支持未来按页面及状态筛选的查询。当前不添加预测性的分析索引。

## Deliberate limits / 当前限制

The page model stores one latest set of metrics; it is not a time-series snapshot table. The 7-day and 28-day fields do not store an observation-date anchor, source, or refresh history. Phase 2 must document a consistent reporting window for its single import format before populating these fields. Add provenance or dated snapshots only when an implemented feature requires them.

页面模型仅存储一组最新指标，并非时间序列快照表。7 天与 28 天字段不存储观察日期基准、数据来源或刷新历史。第二阶段在写入这些字段前，必须为其单一导入格式记录一致的报告时间窗口。只有已实现的功能确实需要时，才增加来源追踪或带日期的快照。

The foundation has no multi-site ownership model, user authentication, full-text search, audit trail, recommendation versions, scoring formula, or SEO rule taxonomy. These remain separate design decisions for later phases rather than implicit promises of this schema.

此基础架构不包含多站点归属模型、用户认证、全文搜索、审计记录、建议版本、评分公式或 SEO 规则分类。这些将作为后续阶段的独立设计决策，而非当前数据库结构的隐含承诺。
