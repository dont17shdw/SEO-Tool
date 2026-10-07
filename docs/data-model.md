# Data model / 数据模型

## Purpose / 目的

PostgreSQL stores four tables. `website_pages` holds the latest applied page state; `seo_opportunities` remains a future action contract. Phase 3 added `import_runs` and `page_performance_snapshots`. Phase 4 computes quality observations and readiness from these existing records without persisting them or changing the schema. SEO rules, scoring, opportunity generation, and recommendations remain unimplemented.

PostgreSQL 存储四个表。`website_pages` 保存最近应用的页面状态；`seo_opportunities` 仍为未来行动契约。第三阶段增加 `import_runs` 与 `page_performance_snapshots`。第四阶段根据这些已有记录计算质量观察与就绪度，不持久化它们，也不改变数据库结构。SEO 规则、评分、机会生成及建议仍未实现。

SQLAlchemy models define the schema and Alembic creates it through an explicit migration. Model changes require a corresponding migration. FastAPI startup and the health endpoint do not create tables or check database connectivity.

SQLAlchemy 模型定义数据库结构，Alembic 通过显式迁移创建结构。模型变化需要对应的迁移。FastAPI 启动与健康检查接口均不创建表，也不检查数据库连接。

## Shared conventions / 共同约定

- **IDs:** PostgreSQL `UUID` primary keys use an application-side `uuid4` default. No PostgreSQL UUID extension is required. Direct SQL inserts must supply IDs.
- **标识符：** PostgreSQL `UUID` 主键使用应用侧 `uuid4` 默认值，无需 PostgreSQL UUID 扩展。直接通过 SQL 插入时必须提供 ID。
- **Unknown values:** Nullable metrics use `NULL` for unknown or unobserved values. Zero means a measured zero. Imports must not convert missing metrics to zero.
- **未知值：** 可空指标以 `NULL` 表示未知或尚未观察的值。零表示已测量且结果为零。导入时不得将缺失指标转换为零。
- **Numeric values:** SQLAlchemy uses decimal values for `Numeric` fields. Store CTR and confidence as fractions from `0` to `1`; for example, `0.025` means 2.5%.
- **数值：** SQLAlchemy 为 `Numeric` 字段使用十进制值。点击率与置信度以 `0` 至 `1` 的比例存储；例如，`0.025` 表示 2.5%。
- **Time:** PostgreSQL `TIMESTAMP WITH TIME ZONE` represents instants; history APIs return offset-bearing timestamps. Reporting periods use calendar `DATE` values, not instants or inferred import dates.
- **时间：** PostgreSQL `TIMESTAMP WITH TIME ZONE` 表示时间点；历史 API 返回带偏移的时间戳。报告时间段使用日历 `DATE` 值，不是时间点或推导的导入日期。
- **Classification:** Page types, index statuses, opportunity types, severity, risk levels, and opportunity statuses are strings. No fixed SEO taxonomy or derived classification is implemented.
- **分类：** 页面类型、索引状态、机会类型、严重程度、风险级别及机会状态均使用字符串。不实现固定 SEO 分类体系或推导分类。

## WebsitePage / 网站页面

The `WebsitePage` model maps to `website_pages`. One row represents one unique stored URL. The URL uniqueness constraint uses the stored string; equivalent URLs differing by case, fragments, or other formatting can remain distinct. Phase 2 validates absolute HTTP(S) URLs and trims surrounding whitespace only. Broader canonicalization remains a future concern.

`WebsitePage` 模型对应 `website_pages` 表。一条记录表示一个唯一的已存储 URL。URL 唯一性约束使用实际存储的字符串；大小写、片段或其他格式不同的等价 URL 仍可能被视为不同值。第二阶段仅校验绝对 HTTP(S) URL 并去除前后空白。更广泛的规范化仍属于未来职责。

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

The `SEOOpportunity` model maps to `seo_opportunities`. Each opportunity belongs to exactly one page. The schema can store future recommendations, but Phase 4 has no opportunity writer API, opportunity generator, or scoring implementation. Quality requests create no opportunity records.

`SEOOpportunity` 模型对应 `seo_opportunities` 表。每个机会只能属于一个页面。数据库结构可存储未来的建议，但第四阶段没有机会写入 API、机会生成器或评分实现。质量请求不创建机会记录。

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

## ImportRun / 导入记录

`ImportRun` maps to `import_runs` and describes one successfully applied source file. The supported taxonomy is `source="gsc"`, `source_type="pages_performance"`, and `reporting_window="latest_28_days"`. These source identifiers differ from the preview's convenient `source="gsc_pages"` label.
`ImportRun` 对应 `import_runs`，描述一个成功应用的来源文件。支持的分类为 `source="gsc"`、`source_type="pages_performance"` 与 `reporting_window="latest_28_days"`。这些来源标识与预览中的便捷标签 `source="gsc_pages"` 不同。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning / 含义 |
| --- | --- | --- | --- |
| `id` | `UUID` | No / 否 | Application-generated primary key.<br>应用生成的主键。 |
| `source` | `VARCHAR(30)` | No / 否 | Defaults to `gsc`.<br>默认 `gsc`。 |
| `source_type` | `VARCHAR(50)` | No / 否 | Defaults to `pages_performance`.<br>默认 `pages_performance`。 |
| `file_hash` | `VARCHAR(64)` | No / 否 | Lowercase hexadecimal SHA-256 of source bytes.<br>来源字节的小写十六进制 SHA-256。 |
| `filename` | `TEXT` | No / 否 | Original successful upload's filename metadata; not a date source or file store.<br>原成功上传的文件名元数据；不是日期来源或文件存储。 |
| `reporting_window` | `VARCHAR(30)` | No / 否 | Defaults to `latest_28_days`.<br>默认 `latest_28_days`。 |
| `period_start`, `period_end` | `DATE` | Yes / 是 | Observed calendar-date endpoints, or both `NULL`.<br>已观察的日历日期起止值，或两者均为 `NULL`。 |
| `imported_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Successful import time; database default `now()`.<br>成功导入时间；数据库默认 `now()`。 |
| `total_rows` | `INTEGER` | No / 否 | Validated source row count.<br>已校验的来源行数。 |
| `created_count`, `updated_count`, `skipped_count` | `INTEGER` | No / 否 | Current-page outcomes, nonnegative, defaults `0`.<br>当前页面处理结果，非负，默认 `0`。 |
| `status` | `VARCHAR(30)` | No / 否 | Successful service writes use `completed`.<br>成功的服务写入使用 `completed`。 |

The database validates SHA-256 shape, nonnegative counts, `created_count + updated_count + skipped_count = total_rows`, paired dates, and `period_start <= period_end`. `(source, source_type, file_hash)` is unique. Indexes on `imported_at` and `(period_start, period_end)` support import history and period lookup. `period_status` is an API-derived `exact`/`unknown` value, not a separate database column.
数据库校验 SHA-256 格式、非负计数、`created_count + updated_count + skipped_count = total_rows`、成对日期及 `period_start <= period_end`。`(source, source_type, file_hash)` 唯一。`imported_at` 及 `(period_start, period_end)` 索引支持导入历史与时间段查询。`period_status` 是 API 推导的 `exact` 或 `unknown` 值，不是独立数据库列。

## PagePerformanceSnapshot / 页面性能快照

`PagePerformanceSnapshot` maps to `page_performance_snapshots`. One row records one imported page's normalized source observations within an import. It is not a copy of the page's preserved current state: blank incoming metrics remain `NULL` in the snapshot even if the current page retains older nonblank values. Each new file creates snapshots for unchanged pages too.
`PagePerformanceSnapshot` 对应 `page_performance_snapshots`。一行记录一次导入中一个页面的标准化来源观察。它不是保留下来的当前页面状态副本：即使当前页面保留了较早的非空白值，传入空白指标在快照中仍为 `NULL`。每个新文件也为未变化的页面创建快照。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning / 含义 |
| --- | --- | --- | --- |
| `id` | `UUID` | No / 否 | Application-generated primary key.<br>应用生成的主键。 |
| `import_run_id` | `UUID` | No / 否 | Foreign key to `import_runs.id`.<br>关联 `import_runs.id` 的外键。 |
| `page_id` | `UUID` | No / 否 | Foreign key to `website_pages.id`.<br>关联 `website_pages.id` 的外键。 |
| `url` | `TEXT` | No / 否 | Exact trimmed URL observed in this file.<br>本文件中观察到的去除前后空白的精确 URL。 |
| `clicks`, `impressions` | `BIGINT` | Yes / 是 | Nonnegative source counts; unknown remains `NULL`.<br>非负来源计数；未知保持 `NULL`。 |
| `ctr` | `NUMERIC(7,6)` | Yes / 是 | Fraction constrained to `[0, 1]`.<br>限制为 `[0, 1]` 的比例。 |
| `average_position` | `NUMERIC(10,4)` | Yes / 是 | Nonnegative source average position.<br>非负来源平均排名。 |
| `period_start`, `period_end` | `DATE` | Yes / 是 | Same observed endpoints as the import, or both `NULL`.<br>与导入相同的已观察起止日期，或两者均为 `NULL`。 |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Snapshot insertion time; database default `now()`.<br>快照插入时间；数据库默认 `now()`。 |

`(import_run_id, page_id)` is unique, preventing duplicate page snapshots within a run. Date pairs must be both known or both unknown and ascend when known. A composite index on `(page_id, period_end, period_start)` supports page history and reporting-date queries. Source, source type, reporting window, and import time are read from the parent run rather than duplicated on snapshots. Snapshots contain no SEO judgment or score.
`(import_run_id, page_id)` 唯一，防止同一次导入中的页面快照重复。日期对必须均已知或均未知，已知时按先后排序。`(page_id, period_end, period_start)` 复合索引支持页面历史与报告日期查询。来源、来源类型、报告窗口及导入时间从父导入记录读取，不在快照中重复。快照不包含 SEO 判断或评分。

## Relationships and indexes / 关联与索引

```text
website_pages.id (UUID)
  ├── seo_opportunities.page_id (UUID, NOT NULL)
  └── page_performance_snapshots.page_id (UUID, NOT NULL)
import_runs.id (UUID)
  └── page_performance_snapshots.import_run_id (UUID, NOT NULL)
```

Foreign keys use `ON DELETE RESTRICT`. PostgreSQL rejects deleting a page with opportunities or snapshots, or an import with snapshots. ORM relationships do not automatically delete children or clear required foreign keys; `passive_deletes="all"` leaves enforcement to the database. A future deletion flow must handle related records explicitly. Phase 4 provides no deletion API.

外键采用 `ON DELETE RESTRICT`。PostgreSQL 拒绝删除有机会或快照的页面，或有快照的导入。ORM 关联不会自动删除子项或清空必填外键；`passive_deletes="all"` 将约束执行交给数据库。未来删除流程必须明确处理关联记录。第四阶段不提供删除 API。

PostgreSQL automatically indexes primary keys and uniqueness constraints. Existing indexes on `seo_opportunities.page_id` and `seo_opportunities.status` remain. The new history indexes serve implemented read APIs and comparisons, without speculative SEO analytics indexes.

PostgreSQL 自动为主键与唯一性约束创建索引。原有的 `seo_opportunities.page_id` 与 `seo_opportunities.status` 索引保留。新的历史索引服务于已实现的读取 API 与对比，不增加预测性的 SEO 分析索引。

## Current-page write boundary / 当前页面写入边界

| GSC value / GSC 值 | Model field / 模型字段 | Stored representation / 存储形式 |
| --- | --- | --- |
| Clicks / 点击次数 | `clicks_28d` | Non-negative integer; missing is unknown.<br>非负整数；缺失表示未知。 |
| Impressions / 展示 | `impressions_28d` | Non-negative integer; missing is unknown.<br>非负整数；缺失表示未知。 |
| CTR / 点击率 | `ctr` | Fraction in `[0, 1]`, up to six decimal places.<br>`[0, 1]` 比例，最多六位小数。 |
| Position / 排名 | `average_position` | Non-negative decimal, up to four decimal places.<br>非负十进制数，最多四位小数。 |

Confirmed imports upsert by the exact trimmed URL within a transaction. A new row receives only the URL and supplied GSC values; unspecified nullable fields stay `NULL`. An existing row updates only supplied, non-blank GSC values. A blank incoming metric does not erase an existing value; an explicit measured zero does update it. An unchanged existing row counts as skipped. Unexpected persistence failures roll back the entire operation.
已确认导入在事务内按去除前后空白后的精确 URL 执行新增或更新。新行仅接收 URL 及提供的 GSC 值；未指定的可空字段保持 `NULL`。已有行仅更新已提供、非空白的 GSC 值。传入空白指标不会清除已有值；明确测得的零会更新该值。未变化的已有行计为跳过。意外持久化失败会回滚整个操作。

The import never populates the seven-day or previous-28-day fields, infers page type or keywords, or changes business value, backlinks, indexing, word count, content timestamps, titles, or opportunity records. Row creation/modification timestamps retain their normal model behavior. The import contract and numeric validation are in [gsc-import.md](gsc-import.md).
导入不会填充七天或前 28 天字段，不会推导页面类型或关键词，也不会修改业务价值、外链、索引、字词数、内容时间戳、标题或机会记录。行创建与修改时间戳保留模型的正常行为。导入契约及数值校验详见 [gsc-import.md](gsc-import.md)。

Phase 3 writes current pages, one completed run, and all snapshots atomically. Failure in any of these writes rolls back all of them; no failed run is retained. An already-successful identical hash returns the original run without writes. Snapshot `clicks`/`impressions` correspond to current-page `clicks_28d`/`impressions_28d`, but use only this file's observations. Comparison never writes calculated changes into the current page or `*_previous_28d` fields.
第三阶段原子写入当前页面、一个已完成导入及全部快照。任何写入失败都会回滚所有写入；不保留失败导入。已成功的相同哈希返回原导入，不执行写入。快照 `clicks` 与 `impressions` 对应当前页面的 `clicks_28d` 与 `impressions_28d`，但仅使用本文件的观察。对比绝不将计算出的变化写入当前页面或 `*_previous_28d` 字段。

Revision `0002_import_history` creates the new tables, checks, foreign keys, and indexes without altering existing page/opportunity data. Earlier imports are not backfilled because their source bytes, dates, and provenance cannot be reconstructed reliably. Downgrading this revision removes only the new history tables and their contents; current-page data remains. Normal use requires upgrading to head.
修订 `0002_import_history` 创建新表、检查、外键与索引，不改变已有页面及机会数据。不回填此前导入，因为其来源字节、日期与来源追踪无法可靠重建。降级此修订仅移除新历史表及其内容；当前页面数据保留。正常使用需要升级至最新修订。

## Runtime quality contract / 运行时质量契约

Phase 4 requires no migration; `0002_import_history` remains head. `analysis/data_quality.py` produces structured observations, counts, and page readiness from existing snapshots/imports and the selected Phase 3 comparison. These are response contracts, not database models. Quality requests do not mutate current metrics, history, or opportunities and do not backfill missing observations.
第四阶段无需迁移；`0002_import_history` 仍为最新修订。`analysis/data_quality.py` 根据已有快照与导入及第三阶段选中的对比，生成结构化观察、计数及页面就绪度。这些是响应契约，不是数据库模型。质量请求不修改当前指标、历史或机会，也不回填缺失观察。

Snapshot IDs and run IDs support factual evidence about dates, missing metrics, repeated date bounds, overlap, and strict import chronology. However, the schema has no per-metric source ID on `WebsitePage`, may lack pre-Phase-3 history, and cannot track manual/direct SQL edits. Matching current values to a snapshot does not prove their origin. Therefore `current_state_not_single_snapshot` is not emitted.
快照 ID 与导入 ID 支持关于日期、缺失指标、重复日期范围、重叠及严格导入时间顺序的事实证据。但是，数据库结构没有 `WebsitePage` 的逐指标来源 ID，可能缺少第三阶段之前的历史，也无法追踪手动或直接 SQL 编辑。当前值与快照匹配不能证明其来源。因此不生成 `current_state_not_single_snapshot`。

Import grouping by source/type/window and dates does not establish the same GSC property or identical filter scope. Page observations are scoped by actual `page_id`, but neither import nor page readiness proves export completeness, source accuracy, full 28-day coverage, or matching report filters. See [data-quality.md](data-quality.md) for the exact deterministic rules and their evidence boundaries.
按来源、类型、窗口与日期将导入分组，不能证明同一 GSC 属性或相同筛选范围。页面观察按实际 `page_id` 限定，但导入或页面就绪度都不能证明导出完整性、来源准确性、完整 28 天覆盖或报告筛选一致。明确的确定性规则及证据边界详见 [data-quality.md](data-quality.md)。

## Deliberate limits / 当前限制

`WebsitePage` remains the latest successfully applied nonblank state, not a dated historical record. Successive files can combine metrics or apply an older reporting period later. Use snapshots and their runs for dated comparison, never current-page fields as historical evidence. Unknown period dates stay `NULL`; known observed endpoints do not certify a complete or contiguous 28-day export. Identical-file protection uses bytes, not semantic row equivalence.

`WebsitePage` 仍为最近成功应用的非空白状态，不是带日期的历史记录。连续文件可组合指标，或后来应用较早报告时间段。带日期的对比使用快照及其导入记录，绝不将当前页面字段作为历史证据。未知时间段日期保持 `NULL`；已知的已观察起止日期不能证明完整或连续的 28 天导出。相同文件保护使用字节，不使用语义行等价性。

There is no multi-site ownership model, user authentication, full-text search, failed-attempt log, tamper-proof audit trail, recommendation versions, scoring formula, or SEO rule taxonomy. Successful-import history is a lightweight provenance record, not a complete audit system. See [performance-history.md](performance-history.md) for comparison selection and missing-data rules.

没有多站点归属模型、用户认证、全文搜索、失败尝试日志、防篡改审计记录、建议版本、评分公式或 SEO 规则分类。成功导入历史是轻量的来源追踪记录，不是完整审计系统。对比选择与缺失数据规则详见 [performance-history.md](performance-history.md)。
