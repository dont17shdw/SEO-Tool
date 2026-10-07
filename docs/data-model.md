# Data model / 数据模型

## Purpose / 目的

PostgreSQL stores six tables. `sites` minimally identifies explicit GSC properties; `website_pages` holds current applied state within a site or unknown-site namespace. `import_runs` stores report-level scope/coverage and successful history; `page_performance_snapshots` retains page observations; `page_metric_provenance` links four current metrics to their supplying snapshots. `seo_opportunities` remains a future contract without a generator. Comparison, quality, and provenance observations remain runtime responses.

PostgreSQL 存储六个表。`sites` 最小化标识明确 GSC 属性；`website_pages` 在站点或未知站点命名空间内保存当前应用状态。`import_runs` 存储报告级范围、覆盖及成功历史；`page_performance_snapshots` 保留页面观察；`page_metric_provenance` 将四个当前指标关联至提供值的快照。`seo_opportunities` 仍为未来契约，没有生成器。对比、质量及来源观察仍为运行时响应。

SQLAlchemy models define the schema and Alembic creates it through an explicit migration. Model changes require a corresponding migration. FastAPI startup and the health endpoint do not create tables or check database connectivity.

SQLAlchemy 模型定义数据库结构，Alembic 通过显式迁移创建结构。模型变化需要对应的迁移。FastAPI 启动与健康检查接口均不创建表，也不检查数据库连接。

## Shared conventions / 共同约定

- **IDs:** Entity `id` columns use PostgreSQL `UUID` with an application-side `uuid4` default. Provenance instead keys existing page IDs with metric names. No PostgreSQL UUID extension is required. Direct SQL inserts must supply IDs.
- **标识符：** 实体 `id` 字段使用 PostgreSQL `UUID` 与应用侧 `uuid4` 默认值。来源表则使用已有页面 ID 与指标名称作为键。无需 PostgreSQL UUID 扩展。直接通过 SQL 插入时必须提供 ID。
- **Unknown values:** Nullable metrics use `NULL` for unknown or unobserved values. Zero means a measured zero. Imports must not convert missing metrics to zero.
- **未知值：** 可空指标以 `NULL` 表示未知或尚未观察的值。零表示已测量且结果为零。导入时不得将缺失指标转换为零。
- **Numeric values:** SQLAlchemy uses decimal values for `Numeric` fields. Store CTR and confidence as fractions from `0` to `1`; for example, `0.025` means 2.5%.
- **数值：** SQLAlchemy 为 `Numeric` 字段使用十进制值。点击率与置信度以 `0` 至 `1` 的比例存储；例如，`0.025` 表示 2.5%。
- **Time:** PostgreSQL `TIMESTAMP WITH TIME ZONE` represents instants; history APIs return offset-bearing timestamps. Reporting periods use calendar `DATE` values, not instants or inferred import dates.
- **时间：** PostgreSQL `TIMESTAMP WITH TIME ZONE` 表示时间点；历史 API 返回带偏移的时间戳。报告时间段使用日历 `DATE` 值，不是时间点或推导的导入日期。
- **Classification:** Page types, index statuses, opportunity types, severity, risk levels, and opportunity statuses are strings. No fixed SEO taxonomy or derived classification is implemented.
- **分类：** 页面类型、索引状态、机会类型、严重程度、风险级别及机会状态均使用字符串。不实现固定 SEO 分类体系或推导分类。

## Site / 站点

`Site` maps to `sites`. Its unique `identifier` is the canonical explicitly observed or user-declared GSC property identifier: a domain property such as `sc-domain:example.com` or URL-prefix property such as `https://example.com/shop/`. These are distinct identities; the application does not merge properties because hosts or page URLs overlap. `display_name` currently uses that identifier. This is a property-bound namespace, not proof of authenticated ownership or a customer/account model.
`Site` 对应 `sites`。唯一 `identifier` 为明确观察或用户声明的规范 GSC 属性标识：例如网域属性 `sc-domain:example.com` 或 URL 前缀属性 `https://example.com/shop/`。它们为不同身份；应用不因主机或页面 URL 重叠而合并属性。`display_name` 当前使用该标识。这是属性绑定命名空间，不是已认证归属证明或客户账户模型。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning / 含义 |
| --- | --- | --- | --- |
| `id` | `UUID` | No / 否 | Application-generated primary key.<br>应用生成主键。 |
| `identifier` | `TEXT` | No / 否 | Unique nonblank canonical property identity.<br>唯一非空规范属性身份。 |
| `display_name` | `TEXT` | No / 否 | Minimal display label, currently the property identifier.<br>最小显示标签，当前为属性标识。 |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Database default `now()`.<br>数据库默认 `now()`。 |

A site is created/resolved only while applying explicit property evidence. Its creation is part of the same transaction as the import; preview never creates a Site. Missing property evidence leaves `site_id=NULL`. Existing unknown ownership is never inferred or assigned during migration or import.
仅在应用明确属性证据时创建或解析站点。创建与导入处于同一事务；预览绝不创建站点。缺失属性证据使 `site_id=NULL`。迁移或导入绝不推断或分配已有未知归属。

## WebsitePage / 网站页面

`WebsitePage` maps to `website_pages`. The unique key is `(site_id, url)` with PostgreSQL `NULLS NOT DISTINCT`: known properties have separate URL namespaces, while all unknown-site rows retain unique URLs within the unknown namespace. An explicitly scoped import never claims or rewrites an existing unknown-site page merely because its URL matches. Different filter scopes within one Site share the same current page, while their histories retain distinct report scope.

`WebsitePage` 对应 `website_pages`。唯一键为 `(site_id, url)`，使用 PostgreSQL `NULLS NOT DISTINCT`：已知属性具有独立 URL 命名空间，全部未知站点行在未知命名空间内继续保持 URL 唯一。明确范围导入绝不因 URL 匹配而认领或重写已有未知站点页面。同一站点内不同筛选范围共享当前页面，历史则保留不同报告范围。

URL identity still uses exact stored strings. Validation trims surrounding whitespace and checks absolute HTTP(S) syntax; it does not broadly canonicalize page URLs, infer property membership, or fetch pages.
URL 身份仍使用精确存储字符串。校验去除前后空白并检查绝对 HTTP(S) 语法；不广泛规范化页面 URL、不推断属性成员关系，也不访问页面。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning and constraints / 含义与约束 |
| --- | --- | --- | --- |
| `id` | `UUID` | No / 否 | Primary key; application-generated UUID.<br>主键；由应用生成的 UUID。 |
| `site_id` | `UUID` | Yes / 是 | Indexed foreign key to `sites.id`, `ON DELETE RESTRICT`; `NULL` means unproven ownership.<br>带索引外键关联 `sites.id`，`ON DELETE RESTRICT`；`NULL` 表示归属未获证明。 |
| `url` | `TEXT` | No / 否 | Unique within the site/unknown-site namespace; exact stored string.<br>在站点或未知站点命名空间内唯一；精确存储字符串。 |
| `page_type` | `VARCHAR(50)` | Yes / 是 | Optional page classification.<br>可选的页面分类。 |
| `title` | `TEXT` | Yes / 是 | Last known page title.<br>最新已知的页面标题。 |
| `primary_keyword` | `TEXT` | Yes / 是 | Optional primary target keyword.<br>可选的主要目标关键词。 |
| `clicks_7d` | `BIGINT` | Yes / 是 | Clicks over the latest 7-day window; ≥ 0.<br>最近 7 天窗口的点击数；≥ 0。 |
| `clicks_28d` | `BIGINT` | Yes / 是 | Latest applied clicks from a supplied 28-day report; ≥ 0. Its period may be older.<br>已提供 28 天报告最近应用的点击数；≥ 0。其时间段可能较早。 |
| `clicks_previous_28d` | `BIGINT` | Yes / 是 | Clicks over the preceding 28-day comparison window; ≥ 0.<br>此前 28 天对比窗口的点击数；≥ 0。 |
| `impressions_7d` | `BIGINT` | Yes / 是 | Impressions over the latest 7-day window; ≥ 0.<br>最近 7 天窗口的展示数；≥ 0。 |
| `impressions_28d` | `BIGINT` | Yes / 是 | Latest applied impressions from a supplied 28-day report; ≥ 0. Its period may be older.<br>已提供 28 天报告最近应用的展示数；≥ 0。其时间段可能较早。 |
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

The `SEOOpportunity` model maps to `seo_opportunities`. Each opportunity belongs to exactly one page. Phase 6 has no opportunity writer API, generator, or scoring implementation. Quality and provenance requests create no opportunity records.

`SEOOpportunity` 模型对应 `seo_opportunities` 表。每个机会只能属于一个页面。第六阶段没有机会写入 API、生成器或评分实现。质量及来源请求不创建机会记录。

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
| `site_id` | `UUID` | Yes / 是 | Indexed foreign key to `sites.id`, `ON DELETE RESTRICT`; legacy ownership stays unknown.<br>带索引外键关联 `sites.id`，`ON DELETE RESTRICT`；旧归属保持未知。 |
| `source` | `VARCHAR(30)` | No / 否 | Defaults to `gsc`.<br>默认 `gsc`。 |
| `source_type` | `VARCHAR(50)` | No / 否 | Defaults to `pages_performance`.<br>默认 `pages_performance`。 |
| `file_hash` | `VARCHAR(64)` | No / 否 | Lowercase hexadecimal SHA-256 of raw source bytes, separate from preview binding.<br>原始来源字节的小写十六进制 SHA-256，与预览绑定分离。 |
| `report_scope` | `JSONB` | Yes / 是 | Normalized report-level identity and observed/declared origins; SQL `NULL` for legacy unknown evidence.<br>标准化报告级身份及观察与声明来源；旧未知证据为 SQL `NULL`。 |
| `scope_fingerprint` | `VARCHAR(64)` | No / 否 | Canonical semantic SHA-256, excluding dates and evidence origin; legacy default represents unknown, not inferred scope.<br>规范语义 SHA-256，排除日期与证据来源；旧默认值表示未知，不是推断范围。 |
| `filename` | `TEXT` | No / 否 | Original successful upload's filename metadata; not a date source or file store.<br>原成功上传的文件名元数据；不是日期来源或文件存储。 |
| `reporting_window` | `VARCHAR(30)` | No / 否 | Defaults to `latest_28_days`.<br>默认 `latest_28_days`。 |
| `period_start`, `period_end` | `DATE` | Yes / 是 | Observed calendar-date endpoints, or both `NULL`.<br>已观察的日历日期起止值，或两者均为 `NULL`。 |
| `observed_date_count` | `INTEGER` | Yes / 是 | Distinct reliably observed daily dates; unknown evidence remains `NULL`.<br>可靠观察的不同每日日期数量；未知证据保持 `NULL`。 |
| `dates_consecutive` | `BOOLEAN` | Yes / 是 | Count equals inclusive endpoint span when evidence is reliable; otherwise `NULL`.<br>证据可靠时，数量是否等于包含起止日的跨度；否则为 `NULL`。 |
| `coverage_status` | `VARCHAR(10)` | No / 否 | `complete`, `partial`, or `unknown`; legacy default `unknown`.<br>`complete`、`partial` 或 `unknown`；旧默认 `unknown`。 |
| `imported_at` | `TIMESTAMP WITH TIME ZONE` | No / 否 | Successful import time; database default `now()`.<br>成功导入时间；数据库默认 `now()`。 |
| `total_rows` | `INTEGER` | No / 否 | Validated source row count.<br>已校验的来源行数。 |
| `created_count`, `updated_count`, `skipped_count` | `INTEGER` | No / 否 | Current-page outcomes, nonnegative, defaults `0`.<br>当前页面处理结果，非负，默认 `0`。 |
| `status` | `VARCHAR(30)` | No / 否 | Successful service writes use `completed`.<br>成功的服务写入使用 `completed`。 |

The database validates both SHA-256 shapes, JSON object shape, nonnegative row counts, count sum, paired dates, and ascending endpoints. Unique constraint `uq_import_runs_source_type_file_scope` covers `(source, source_type, file_hash, scope_fingerprint)`. Coverage checks require unknown count/consecutiveness to be `NULL`; reliable counts must be positive and no greater than the inclusive span, and `dates_consecutive` must equal `count == span`. Complete coverage requires exactly 28 distinct consecutive dates spanning 28 days; every other reliable set is partial. Unknown legacy coverage may coexist with preserved exact endpoints.
数据库校验两个 SHA-256 格式、JSON 对象形状、非负行数、计数之和、成对日期及升序起止值。唯一约束 `uq_import_runs_source_type_file_scope` 包含 `(source, source_type, file_hash, scope_fingerprint)`。覆盖检查要求未知数量与连续性为 `NULL`；可靠数量必须为正且不大于包含起止日的跨度，`dates_consecutive` 必须等于 `count == span`。完整覆盖要求恰好 28 个不同连续日期，跨越 28 天；其他可靠集合均为部分覆盖。未知旧覆盖可与保留的准确起止日期并存。

Indexes on `site_id`, `imported_at`, and `(period_start, period_end)` support implemented reads. `period_status`, scope status, property status, and canonical fingerprint presentation are derived API facts; source scope values and origins reside in `report_scope`. Scope/coverage are reused through the run join for snapshot responses rather than copied into every snapshot. See [report-scope.md](report-scope.md).
`site_id`、`imported_at` 及 `(period_start, period_end)` 索引支持已实现读取。`period_status`、范围状态、属性状态及规范指纹展示为派生 API 事实；来源范围值及来源存放在 `report_scope`。快照响应通过导入连接复用范围与覆盖，不复制到每个快照。详见 [report-scope.md](report-scope.md)。

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

## PageMetricProvenance / 当前指标来源关联

`PageMetricProvenance` maps to `page_metric_provenance`. One current row per page and metric points to the snapshot that explicitly supplied that metric. The snapshot already identifies its import and normalized value, so the link stores neither copied values nor import IDs. Historical snapshots remain unchanged when a current link moves.
`PageMetricProvenance` 对应 `page_metric_provenance`。每个页面与指标的一条当前行，指向明确提供该指标的快照。快照已有导入及标准化值，因此关联不存储复制值或导入 ID。当前关联移动时，历史快照保持不变。

| Field / 字段 | PostgreSQL type / PostgreSQL 类型 | Nullable / 可空 | Meaning / 含义 |
| --- | --- | --- | --- |
| `page_id` | `UUID` | No / 否 | Part of the primary key; foreign key to `website_pages.id`, `ON DELETE RESTRICT`.<br>主键组成部分；关联 `website_pages.id` 的外键，`ON DELETE RESTRICT`。 |
| `metric_name` | `VARCHAR(30)` | No / 否 | Part of the primary key; limited to `clicks_28d`, `impressions_28d`, `ctr`, `average_position`.<br>主键组成部分；仅限 `clicks_28d`、`impressions_28d`、`ctr`、`average_position`。 |
| `snapshot_id` | `UUID` | No / 否 | Indexed foreign key to `page_performance_snapshots.id`, `ON DELETE RESTRICT`.<br>带索引的外键，关联 `page_performance_snapshots.id`，`ON DELETE RESTRICT`。 |

The composite primary key enforces at most one link per page/metric; a check constraint enforces the four names. There is no separate row ID, copied metric, copied import ID, or update timestamp. Simple foreign keys enforce that the page and snapshot exist, but not that they are the same page. The import writer constructs links from the exact page/snapshot row, and read analysis rejects cross-page, missing, `NULL`-metric, or mismatched links. Direct SQL can bypass that application-level association check; no composite foreign key or database audit layer is introduced.
复合主键约束每个页面与指标至多一个关联；检查约束限定四个名称。没有独立行 ID、复制指标、复制导入 ID 或更新时间戳。简单外键约束页面与快照存在，但不约束它们属于同一页面。导入写入器根据准确的页面与快照行构建关联，读取分析拒绝跨页面、缺失、指标为 `NULL` 或值不匹配的关联。直接 SQL 可绕过该应用级关联检查；不引入复合外键或数据库审计层。

Revision `0003_current_metric_provenance` creates this empty table and its index without changing any existing page, run, snapshot, or opportunity. No provenance is backfilled from equality or replayed history. Existing non-`NULL` current values initially have unknown provenance. Its downgrade removes only current links, preserving metric values and all historical records. Phase 6 head `0004_report_scope` preserves all these existing links and changes none of their meanings.
修订 `0003_current_metric_provenance` 创建此空表及索引，不改变任何已有页面、导入、快照或机会。不根据相等值或重放历史回填来源。已有非 `NULL` 当前值最初具有未知来源。其降级仅移除当前关联，保留指标值及全部历史记录。第六阶段最新修订 `0004_report_scope` 保留全部已有来源关联，不改变其含义。

## Relationships and indexes / 关联与索引

```text
sites.id (UUID)
  ├── website_pages.site_id (UUID, nullable / 可空)
  └── import_runs.site_id (UUID, nullable / 可空)
website_pages.id (UUID)
  ├── seo_opportunities.page_id (UUID, NOT NULL)
  ├── page_performance_snapshots.page_id (UUID, NOT NULL)
  └── page_metric_provenance.page_id (UUID, PRIMARY KEY part)
import_runs.id (UUID)
  └── page_performance_snapshots.import_run_id (UUID, NOT NULL)
page_performance_snapshots.id (UUID)
  └── page_metric_provenance.snapshot_id (UUID, NOT NULL)
```

Foreign keys use `ON DELETE RESTRICT`. PostgreSQL rejects deleting referenced pages, imports, and snapshots, including provenance-linked snapshots. Existing history ORM relationships do not automatically delete children or clear required foreign keys; `passive_deletes="all"` leaves enforcement to the database. A future deletion flow must handle related records explicitly. Phase 6 provides no deletion API.

外键采用 `ON DELETE RESTRICT`。PostgreSQL 拒绝删除被引用的页面、导入及快照，包括来源关联的快照。已有历史 ORM 关联不会自动删除子项或清空必填外键；`passive_deletes="all"` 将约束执行交给数据库。未来删除流程必须明确处理关联记录。第六阶段不提供删除 API。

PostgreSQL automatically indexes primary keys and uniqueness constraints. Existing indexes on `seo_opportunities.page_id` and `seo_opportunities.status` remain. The new history indexes serve implemented read APIs and comparisons, without speculative SEO analytics indexes.

PostgreSQL 自动为主键与唯一性约束创建索引。原有的 `seo_opportunities.page_id` 与 `seo_opportunities.status` 索引保留。新的历史索引服务于已实现的读取 API 与对比，不增加预测性的 SEO 分析索引。

## Current-page write boundary / 当前页面写入边界

| GSC value / GSC 值 | Model field / 模型字段 | Stored representation / 存储形式 |
| --- | --- | --- |
| Clicks / 点击次数 | `clicks_28d` | Non-negative integer; missing is unknown.<br>非负整数；缺失表示未知。 |
| Impressions / 展示 | `impressions_28d` | Non-negative integer; missing is unknown.<br>非负整数；缺失表示未知。 |
| CTR / 点击率 | `ctr` | Fraction in `[0, 1]`, up to six decimal places.<br>`[0, 1]` 比例，最多六位小数。 |
| Position / 排名 | `average_position` | Non-negative decimal, up to four decimal places.<br>非负十进制数，最多四位小数。 |

Confirmed imports resolve explicit site identity and upsert by `(site_id, exact trimmed URL)` within one transaction. A new row receives that ownership, URL, and supplied GSC values; unspecified nullable fields stay `NULL`. An existing row updates only supplied, non-blank GSC values. A blank incoming metric does not erase an existing value; an explicit measured zero does update it. An unchanged existing row counts as skipped. Unexpected persistence failures roll back the entire operation.
已确认导入在同一事务内解析明确站点身份，按 `(site_id, 去除前后空白后的精确 URL)` 执行新增或更新。新行接收该归属、URL 及提供的 GSC 值；未指定的可空字段保持 `NULL`。已有行仅更新已提供、非空白的 GSC 值。传入空白指标不会清除已有值；明确测得的零会更新该值。未变化的已有行计为跳过。意外持久化失败会回滚整个操作。

The import never populates the seven-day or previous-28-day fields, infers page type or keywords, or changes business value, backlinks, indexing, word count, content timestamps, titles, or opportunity records. Row creation/modification timestamps retain their normal model behavior. The import contract and numeric validation are in [gsc-import.md](gsc-import.md).
导入不会填充七天或前 28 天字段，不会推导页面类型或关键词，也不会修改业务价值、外链、索引、字词数、内容时间戳、标题或机会记录。行创建与修改时间戳保留模型的正常行为。导入契约及数值校验详见 [gsc-import.md](gsc-import.md)。

Phase 6 includes optional Site creation with the same atomic current-page, completed-run, snapshot, and provenance transaction. Any failure rolls back all changes, including a newly created Site. Every supplied non-`NULL` metric refreshes its link, including zero and an unchanged numeric value. Blanks preserve the current value and existing link; unknown legacy links remain absent. An already-successful identical file hash plus canonical scope returns the original run with no writes. Current-page outcome counts and `updated_at` behavior remain based on metric changes, so a same-value page can count as skipped while its provenance refreshes. Comparison writes neither current metrics nor `*_previous_28d` fields.
第六阶段将可选站点创建纳入同一原子当前页面、已完成导入、快照及来源事务。任何失败回滚全部变化，包括新创建站点。每个提供的非 `NULL` 指标刷新关联，包括零及未变化的数值。空白保留当前值及已有关联；未知旧关联保持缺失。已成功的相同文件哈希及规范范围返回原导入，不执行写入。当前页面处理统计及 `updated_at` 行为仍根据指标变化，因此相同值页面可计为跳过，同时刷新来源。对比不写入当前指标或 `*_previous_28d` 字段。

Revision `0002_import_history` created history without altering existing page/opportunity data or fabricating earlier imports. Its own downgrade removes history tables; the dependent provenance revision must be downgraded first. Phase 5 `0003_current_metric_provenance` adds links without backfill. Phase 6 head `0004_report_scope` preserves all five earlier tables and every value/timestamp/link, creates empty `sites`, adds unknown legacy evidence, and safely replaces uniqueness constraints. Its downgrade refuses before mutation if scoped duplicate URLs or same-file runs would violate earlier global uniqueness; it never deletes retained rows or changes hashes.
修订 `0002_import_history` 创建历史，不改变已有页面及机会数据，也不编造此前导入。其自身降级移除历史表；须先降级依赖它的来源修订。第五阶段 `0003_current_metric_provenance` 增加关联，不回填。第六阶段最新修订 `0004_report_scope` 保留此前五个表及每个值、时间戳与关联，创建空 `sites`，增加未知旧证据，安全替换唯一约束。如果按范围存储的重复 URL 或相同文件导入违反此前全局唯一性，其降级会在修改之前拒绝；绝不删除保留行或改变哈希。

## Runtime quality contract / 运行时质量契约

`analysis/data_quality.py` continues to produce structured observations, counts, and page readiness from historical snapshots/imports and the Phase 3 comparison. `analysis/current_provenance.py` separately validates recorded current links and reports current provenance. Both return runtime contracts rather than persisted observations. Quality and provenance requests perform no writes; current provenance does not alter comparison readiness.
`analysis/data_quality.py` 继续根据历史快照与导入及第三阶段对比，生成结构化观察、计数与页面就绪度。`analysis/current_provenance.py` 单独校验已记录当前关联并报告当前来源。两者均返回运行时契约，不持久化观察。质量及来源请求不执行写入；当前来源不改变对比就绪度。

Current provenance is known only when a recorded link resolves to the same page's snapshot and import, its source metric is non-`NULL`, and that metric matches the current value. Missing or inconsistent links produce unknown provenance for a non-`NULL` current metric; current `NULL` means unavailable. Equality validates a stored link but never finds a missing origin. Multiple validated known snapshot IDs can now prove `current_state_not_single_snapshot`, emitted separately from quality readiness. Manual edits that leave the same value can remain undetectable because this is a controlled-write provenance contract, not an audit system.
仅当已记录关联解析到同一页面的快照及导入、来源指标非 `NULL` 且与当前值匹配时，当前来源才为已知。缺失或不一致关联使非 `NULL` 当前指标来源未知；当前 `NULL` 表示不可用。相等性校验存储关联，但绝不寻找缺失来源。多个已验证已知快照 ID 现可证明 `current_state_not_single_snapshot`，与质量就绪度分开生成。保持相同值的手动编辑可能仍无法检测，因为这是受控写入来源契约，不是审计系统。

Phase 6 comparison groups revisions by canonical scope identity before selecting date-compatible nonconflicting partners. Proven matching scope requires known property, search type, and a complete matching filter ledger. Legacy/partial scope stays unknown and reduces selected-pair readiness. Complete observed-date coverage certifies only the daily dates supplied, not complete page exports, source accuracy, or authenticated ownership. See [data-quality.md](data-quality.md) and [report-scope.md](report-scope.md).
第六阶段对比先按规范范围身份将修订分组，再选择日期兼容且范围不冲突伙伴。已证明范围匹配要求已知属性、搜索类型及完整匹配筛选清单。旧或部分范围保持未知，并降低所选对就绪度。完整已观察日期覆盖仅证明提供的每日日期，不证明完整页面导出、来源准确性或已认证归属。详见 [data-quality.md](data-quality.md) 与 [report-scope.md](report-scope.md)。

## Deliberate limits / 当前限制

`WebsitePage` remains the latest successfully applied nonblank state, not a dated historical record. Successive files can combine metrics or apply an older reporting period later. Use snapshots and their runs for dated comparison, never current-page fields as historical evidence. Unknown period dates stay `NULL`; known observed endpoints do not certify a complete or contiguous 28-day export. Observed coverage is stored separately; raw bytes plus canonical scope, not semantic row equivalence, define duplicate imports.

`WebsitePage` 仍为最近成功应用的非空白状态，不是带日期的历史记录。连续文件可组合指标，或后来应用较早报告时间段。带日期的对比使用快照及其导入记录，绝不将当前页面字段作为历史证据。未知时间段日期保持 `NULL`；已知的已观察起止日期不能证明完整或连续的 28 天导出。已观察覆盖独立存储；原始字节及规范范围定义重复导入，不使用语义行等价性。

The minimal multi-property namespace verifies no user/account access and performs no property membership fetch. There is no production authentication, account/team management, full-text search, failed-attempt log, tamper-proof audit trail, scoring formula, or opportunity engine. Successful-import history is a lightweight evidence record; direct SQL may bypass controlled writers. See [performance-history.md](performance-history.md) for comparison selection and missing-data rules. Phase 7 has not started.

最小多属性命名空间不验证用户或账户访问，也不获取属性成员关系。没有生产身份认证、账户或团队管理、全文搜索、失败尝试日志、防篡改审计记录、评分公式或机会引擎。成功导入历史为轻量证据记录；直接 SQL 可绕过受控写入器。对比选择与缺失数据规则详见 [performance-history.md](performance-history.md)。第七阶段尚未开始。
