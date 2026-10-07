# Performance history / 性能历史

## Current state and observations / 当前状态与观察

`WebsitePage` keeps the latest successfully applied nonblank metrics, preserving Phase 2 behavior. A newer upload can omit a metric and leave its older value unchanged. Uploading an older report later can also update current state. Therefore, current metrics need not belong to one report or the latest reporting period.
`WebsitePage` 保留最近成功应用的非空白指标，沿用第二阶段行为。较新的上传可省略指标，使其较早值保持不变。后来上传较早报告也可更新当前状态。因此，当前指标不一定属于同一个报告或最新报告时间段。

`ImportRun` records a successful file import and its source, raw hash, canonical scope, evidence origins, site identity when known, reporting window, known dates, observed coverage, import time, and current-page outcome counts. `PagePerformanceSnapshot` records each imported page's normalized observations for that run. A snapshot's missing metric is `NULL`, even when the current page retains an older value. Use these snapshots for period comparison; never reconstruct history from the current page.
`ImportRun` 记录成功文件导入及其来源、原始哈希、规范范围、证据来源、已知站点身份、报告窗口、已知日期、已观察覆盖、导入时间与当前页面处理统计。`PagePerformanceSnapshot` 记录该导入中每个页面的标准化观察。快照的缺失指标为 `NULL`，即使当前页面保留了较早值。时间段对比使用这些快照；绝不从当前页面重建历史。

Historical source identifiers are `source="gsc"`, `source_type="pages_performance"`, and `reporting_window="latest_28_days"`. The preview retains `source="gsc_pages"`. Both use the existing English/Chinese GSC importer and deterministic normalization.
历史来源标识为 `source="gsc"`、`source_type="pages_performance"` 与 `reporting_window="latest_28_days"`。预览保留 `source="gsc_pages"`。两者使用现有英文与中文 GSC 导入器及确定性标准化。

## Successful-import lifecycle / 成功导入生命周期

1. Preview parses, validates, normalizes, and extracts available reporting scope, dates, and coverage without database access or history writes.
   预览解析、校验、标准化并提取可用报告范围、日期与覆盖，不访问数据库，也不写入历史。
2. Apply requires the retained file, the same normalized scope declaration, `confirmed=true`, and `preview_hash` binding raw bytes plus complete resolved scope evidence. Revalidation remains mandatory before database access.
   应用要求保留文件、相同标准化范围声明、`confirmed=true` 及绑定原始字节与完整解析范围证据的 `preview_hash`。数据库访问前重新校验仍为必需。
3. A new file/scope identity resolves optional Site, updates site-scoped pages, creates one completed run and one snapshot per validated page, and refreshes current provenance for every supplied non-`NULL` metric. Same-value pages still get snapshots and refreshed sources even when counted as skipped.
   新文件与范围身份解析可选站点，更新按站点区分的页面，创建一个已完成导入及每个已校验页面的一条快照，并为每个提供的非 `NULL` 指标刷新当前来源。相同值页面即使计为跳过，也会获得快照及刷新来源。
4. Optional Site creation and all four existing write targets commit in one transaction. A failure rolls back every write, including a newly created Site. Preview, invalid files, and failed attempts create no retained run; there is no separate failed-attempt lifecycle.
   可选站点创建与全部四个已有写入目标在一个事务内提交。失败会回滚全部写入，包括新创建站点。预览、无效文件及失败尝试不创建保留的导入；没有独立的失败尝试生命周期。

Only `status="completed"` runs are persisted by this workflow. Run row counts describe current-page creates, updates, and skips; they do not count snapshots. A new file with unchanged current-page metrics still creates history and snapshots. The service does not edit or delete historical records.
此流程仅持久化 `status="completed"` 的导入。导入行数描述当前页面新增、更新与跳过，不统计快照。新文件即使当前页面指标未变化，也会创建历史与快照。服务不编辑或删除历史记录。

## Identical-file handling / 相同文件处理

Phase 6 uniqueness on `(source, source_type, file_hash, scope_fingerprint)` replaces the earlier file-only key. Exact repeated bytes under the same canonical scope return `already_processed=true`, the original `import_run_id`, `created_count=0`, `updated_count=0`, `skipped_count=total_rows`, and `error_count=0`. No new run or snapshot is created, and current pages/provenance are not rewritten. This remains true if a different file updated those pages afterward; retrying the old file does not restore old metrics. The original run's filename and outcome counts remain unchanged. The same bytes under another explicit scope create separate history rather than resolving to an unrelated run.
第六阶段 `(source, source_type, file_hash, scope_fingerprint)` 唯一性替代此前仅按文件的键。同一规范范围下完全相同重复字节返回 `already_processed=true`、原 `import_run_id`、`created_count=0`、`updated_count=0`、`skipped_count=total_rows` 与 `error_count=0`。不创建新导入或快照，也不重写当前页面或来源。即使此后另一个文件更新了页面，此行为仍成立；重试旧文件不会恢复旧指标。原导入的文件名与处理统计保持不变。相同字节配合另一明确范围创建独立历史，不解析至无关导入。

The raw hash represents uploaded bytes, not the filename or semantic equality of rows. Same filename with changed contents creates a new run. Renaming identical bytes within the same scope does not. Different CSV formatting or XLSX packaging can produce a new hash even when metrics match. Multiple files with the same date bounds remain in history. Revisions are narrowed by canonical scope as well as page/source/type/window/exact period. Legacy runs retain unknown scope and their original raw hash; additional newly parsed scope evidence can create a distinct new run without backfilling the earlier one. Dates alone never prove the same property or filter scope.
原始哈希代表上传字节，不代表文件名或行的语义等价性。同名但内容变化会创建新导入。同一范围内重命名相同字节不会。CSV 格式或 XLSX 打包方式不同，即使指标相同，也可能产生新哈希。日期范围相同的多个文件保留在历史中。修订除页面、来源、类型、窗口及准确时间段外，还按规范范围限定。旧导入保留未知范围及原始哈希；新解析出的额外范围证据可创建独立新导入，不回填此前导入。仅有日期绝不证明相同属性或筛选范围。

## Reporting-period extraction / 报告时间段提取

The latest-28-day filter validation from Phase 2 remains unchanged. Separately, GSC-specific extraction examines normalized worksheet names `Chart`, `Date`, `Dates`, `图表`, and `日期`. The first nonblank row must contain exactly one recognized `Date`, `Dates`, or `日期` header. Sheets without recognized date headers provide no evidence.
第二阶段的最近 28 天筛选校验保持不变。另由 GSC 专用提取检查标准化工作表名称 `Chart`、`Date`、`Dates`、`图表` 与 `日期`。首个非空白行必须包含恰好一个已识别的 `Date`、`Dates` 或 `日期` 表头。没有已识别日期表头的工作表不提供证据。

Date cells accept native Excel dates/datetimes (use their calendar date) or trimmed strict `YYYY-MM-DD` text. Ignore fully blank rows. Every nonblank data row must contain a valid date; missing, malformed, formula, or non-date values make the period unknown rather than inventing a date. Unsorted dates and duplicate days are allowed. Use the earliest and latest observed dates without requiring 28 unique or consecutive days.
日期单元格接受原生 Excel 日期或日期时间（使用其日历日期），或去除前后空白的严格 `YYYY-MM-DD` 文本。忽略完全空白行。每个非空白数据行都必须包含有效日期；缺失、格式错误、公式或非日期值使时间段未知，不编造日期。允许未排序日期与重复天数。使用最早与最晚已观察日期，不要求 28 个唯一或连续日期。

When multiple usable recognized date worksheets exist, their distinct observed date sets must agree. Conflicting evidence, ambiguous date headers, or a malformed candidate yields an unknown period. Missing usable evidence, including CSV, also yields `period_start=null`, `period_end=null`, and `period_status="unknown"`. The valid page import may continue. Both endpoints present produce `period_status="exact"`; this means observed endpoints are known, not that complete 28-day coverage is certified.
存在多个可用的已识别日期工作表时，其不同的已观察日期集合必须一致。冲突证据、歧义日期表头或损坏的候选表会产生未知时间段。缺少可用证据时，包括 CSV，也会产生 `period_start=null`、`period_end=null` 与 `period_status="unknown"`。有效页面导入仍可继续。两个起止日期均存在时产生 `period_status="exact"`；这表示已观察起止日期已知，不表示完整的 28 天覆盖已获证明。

Phase 6 also stores distinct `observed_date_count`, `dates_consecutive`, and `coverage_status` on the run. Only 28 distinct consecutive observed dates spanning 28 inclusive days are `complete`; every other reliable nonempty set is `partial`. Missing/unreliable evidence is `unknown` with count/consecutiveness `null`. September 1, 10, and 28 give exact 28-day endpoints but count `3` and partial coverage. Duplicate dates do not inflate the count. Legacy exact dates remain intact with unknown coverage because endpoints cannot reconstruct the daily set.
第六阶段还在导入上存储不同的 `observed_date_count`、`dates_consecutive` 与 `coverage_status`。仅有跨度为 28 个包含起止日日历天的 28 个不同连续已观察日期，才为 `complete`；其他可靠非空集合均为 `partial`。缺失或不可靠证据为 `unknown`，数量与连续性为 `null`。9 月 1、10、28 日给出准确 28 天起止值，但数量为 `3` 且覆盖为部分。重复日期不增加数量。旧准确日期保持不变，同时覆盖未知，因为起止值无法重建每日集合。

Never derive dates from filenames, import timestamps, filter labels alone, or current metrics. Native reporting dates are calendar dates, not UTC instants. Date worksheets retain the physical-row bound of 10,000 even when evidence is invalid; exceeding it returns `413`. Unknown dates are visible in preview/history and excluded from comparison.
绝不从文件名、导入时间戳、单独的筛选标签或当前指标推导日期。原生报告日期是日历日期，不是 UTC 时间点。日期工作表即使证据无效，也保留 10,000 个物理行的限制；超出返回 `413`。未知日期在预览与历史中可见，并从对比中排除。

## Read-only APIs and UI / 只读 API 与界面

```sh
curl 'http://localhost:8000/api/v1/imports?page=1&page_size=50'
curl 'http://localhost:8000/api/v1/imports/IMPORT_UUID'
curl 'http://localhost:8000/api/v1/pages/PAGE_UUID/performance?page=1&page_size=50'
```

Replace `PAGE_UUID` with a page ID from `GET /api/v1/pages`. Both history endpoints return `items`, `page`, `page_size`, `total`, and `total_pages`; `page` starts at 1 and `page_size` defaults to 50 with a maximum of 100. Empty histories have zero total pages; a page beyond the end returns empty items. Invalid parameters return `422`, an unknown page returns `404`, and database errors return useful `503` responses without internal stack traces.
将 `PAGE_UUID` 替换为 `GET /api/v1/pages` 返回的页面 ID。两个历史接口返回 `items`、`page`、`page_size`、`total` 与 `total_pages`；`page` 从 1 开始，`page_size` 默认 50，最大 100。空历史的总页数为零；超出末页的页面返回空条目。无效参数返回 `422`，未知页面返回 `404`，数据库错误返回有用的 `503` 响应，不包含内部堆栈。

- `GET /api/v1/imports` lists runs newest import first. Items include `id`, `source`, `source_type`, `file_hash`, `filename`, `reporting_window`, `period_start`, `period_end`, `period_status`, `imported_at`, `total_rows`, `created_count`, `updated_count`, `skipped_count`, and `status`.
  `GET /api/v1/imports` 按最新导入在前列出记录。条目包含 `id`、`source`、`source_type`、`file_hash`、`filename`、`reporting_window`、`period_start`、`period_end`、`period_status`、`imported_at`、`total_rows`、`created_count`、`updated_count`、`skipped_count` 与 `status`。
- Phase 6 adds `site_id`, `report_scope`, `observed_date_count`, `dates_consecutive`, and `coverage_status` to each run. `GET /api/v1/imports/{import_run_id}` returns the same single-run contract without pagination or writes; unknown run IDs return `404`. Nested `report_scope` exposes `site_identifier`, `property_status`, search type, ordered non-date predicates, completeness, `fingerprint`, observed/declared origins, and unresolved issues. A `null` site ID retains unknown persisted ownership; there is no separate top-level site-status field.
  第六阶段为每个导入增加 `site_id`、`report_scope`、`observed_date_count`、`dates_consecutive` 与 `coverage_status`。`GET /api/v1/imports/{import_run_id}` 返回相同单导入契约，不分页、不写入；未知导入 ID 返回 `404`。嵌套 `report_scope` 公开 `site_identifier`、`property_status`、搜索类型、排序非日期谓词、完整性、`fingerprint`、观察与声明来源及未解决问题。站点 ID 为 `null` 保留未知持久化归属；没有单独顶层站点状态字段。
- `GET /api/v1/pages/{page_id}/performance` also returns `current_page`, `comparison`, `comparison_unavailable_reason`, and runtime `quality`. Snapshots are ordered by `imported_at`, then snapshot `id`, ascending. Items include snapshot/run/page IDs, URL, source/type/window, period dates/status, import/creation timestamps, and `clicks`, `impressions`, `ctr`, and `average_position`. This is chronological import order, which may differ from reporting-date order.
  `GET /api/v1/pages/{page_id}/performance` 还返回 `current_page`、`comparison`、`comparison_unavailable_reason` 与运行时 `quality`。快照按 `imported_at`、其次快照 `id` 升序排列。条目包含快照、导入、页面 ID、URL、来源与类型、窗口、时间段日期与状态、导入与创建时间戳，以及 `clicks`、`impressions`、`ctr` 与 `average_position`。这是导入时间顺序，可能与报告日期顺序不同。

Dates serialize as ISO calendar dates; timestamps retain offsets. Decimal metrics/changes serialize as strings and missing values as `null`. `period_status` is computed from the paired date fields, without a separate persisted flag. Pagination uses offsets and does not freeze history across concurrent imports.
日期序列化为 ISO 日历日期；时间戳保留偏移。小数指标与变化序列化为字符串，缺失值序列化为 `null`。`period_status` 根据成对日期字段计算，不另行持久化标记。分页使用偏移量，不会跨并发导入冻结历史。

Phase 5 also embeds `provenance` in the performance response and exposes the same object through `GET /api/v1/pages/{page_id}/provenance`. The shared loader uses full history and one current-link query, so provenance is independent of snapshot pagination and the browser needs no extra request. The UI labels current state as "Current applied metrics" and displays per-field sources separately from report-period comparison. See [current-provenance.md](current-provenance.md) for the exact status and summary contracts.
第五阶段还在性能响应中内嵌 `provenance`，并通过 `GET /api/v1/pages/{page_id}/provenance` 提供相同对象。共享读取流程使用完整历史及一个当前关联查询，因此来源独立于快照分页，浏览器不需要额外请求。界面将当前状态标为“当前已应用指标”，并将逐字段来源与报告时间段对比分开显示。准确状态及摘要契约详见 [current-provenance.md](current-provenance.md)。

The `/imports/history` development screen shows successful runs, dates or unknown status, counts, and import status. `/pages` links to `/pages/[id]`, which separates current stored metrics from historical snapshots, the selected period comparison, and its data-quality section. There are no editing/deletion controls or final SEO dashboard.
`/imports/history` 开发页面显示成功导入、日期或未知状态、计数及导入状态。`/pages` 链接到 `/pages/[id]`，后者将当前存储指标与历史快照、选中的时间段对比及其数据质量部分分开显示。没有编辑删除控制或最终 SEO 仪表盘。

History rows and joined page snapshots also show bilingual report scope, evidence origins, unknown dimensions, and observed coverage. Comparison shows both selected report scopes, compatibility (`compatible` or `unknown`), and each report's coverage/count/consecutiveness. Scope and coverage come from the existing run join, so no extra query per snapshot or new browser request is needed.
历史行及连接的页面快照还显示双语报告范围、证据来源、未知维度与已观察覆盖。对比显示两个所选报告范围、兼容性（`compatible` 或 `unknown`）及各报告的覆盖、数量与连续性。范围与覆盖来自已有导入连接，因此不需要每个快照额外查询或新浏览器请求。

## Compatible comparison selection / 兼容对比选择

Comparison belongs in `analysis/performance_comparison.py`, outside GSC parsing and persistence. Candidates must share page, source, source type, reporting window, and inclusive period length; both endpoints must be known. Group revisions by canonical scope identity and exact `(period_start, period_end)` and select the latest imported revision, with IDs as deterministic ties. Another scope's matching dates never replace that evidence. Revisions are not merged to fill missing metrics.
对比属于 `analysis/performance_comparison.py`，位于 GSC 解析与持久化之外。候选必须具有相同页面、来源、来源类型、报告窗口与包含起止日的时间段长度；两个起止日期均必须已知。按规范范围身份及准确 `(period_start, period_end)` 将修订分组，选择最近导入的修订，以 ID 确定性处理并列。另一范围的匹配日期绝不替换该证据。不合并修订以填补缺失指标。

Each canonical scope stream contributes its latest two distinct periods. Known scopes pair within the same canonical identity; unknown/partial streams can also contribute pairs with nonconflicting other streams using bounded recent candidates. Explicit property/search/filter conflicts are excluded. Choose the eligible pair with the newest current reporting end/start, then current import time/ID and previous end/start/import time/ID. If a newer singleton has no partner, an eligible pair in another stream can remain visible. Comparison uses full history to establish streams/revisions, independently of snapshot pagination and latest applied metrics, without exhaustively enumerating every historical pair.
每个规范范围流提供最近两个不同时间段。已知范围在相同规范身份内配对；未知或部分范围流还可使用有界近期候选，与其他不冲突范围流组成对。明确属性、搜索或筛选冲突排除在外。当前报告结束及起始日期最新的合格对优先，其次按当前导入时间与 ID，再按此前结束日期、起始日期、导入时间与 ID 排序。较新单条记录没有伙伴时，另一范围流内的合格对仍可显示。对比使用完整历史建立范围流与修订，与快照分页及最近应用指标独立，不穷举全部历史对。

Fully known matching property, search type, and complete filter ledgers give `scope_compatibility="compatible"`. Insufficient nonconflicting evidence gives `unknown`, preserving legacy descriptive comparisons with reduced readiness. Identical URLs, dates, file names, or metric values never prove scope equality. Rejected conflicts are exposed as bounded representative quality observations. See [report-scope.md](report-scope.md) for canonical rules and concrete examples.
完全已知且匹配的属性、搜索类型与完整筛选清单产生 `scope_compatibility="compatible"`。证据不足且不冲突时为 `unknown`，保留旧描述性对比并降低就绪度。相同 URL、日期、文件名或指标值绝不证明范围相等。被拒绝冲突通过有界代表性质量观察公开。规范规则及具体示例详见 [report-scope.md](report-scope.md)。

Periods need not be adjacent or nonoverlapping. Inclusive overlap is returned as `periods_overlap=true`; overlapping exports are not independent before/after cohorts. Two revisions of the same exact period do not form a comparison. Fewer than two compatible distinct dated periods return `comparison=null` with a human-readable `comparison_unavailable_reason`.
时间段不必相邻或互不重叠。包含起止日的重叠返回 `periods_overlap=true`；重叠导出不是独立的前后对照群体。同一准确时间段的两个修订不构成对比。少于两个兼容且不同的已知日期时间段时，返回 `comparison=null` 及易理解的 `comparison_unavailable_reason`。

## Calculation and missing-data rules / 计算与缺失数据规则

| Output / 输出 | Deterministic definition / 确定性定义 |
| --- | --- |
| `clicks.absolute_change`, `impressions.absolute_change` | `current - previous` if both exist; otherwise `null`.<br>两者均存在时为 `current - previous`；否则为 `null`。 |
| `clicks.percentage_change`, `impressions.percentage_change` | `(current - previous) / previous * 100`, when both exist and previous is nonzero; six decimal places, `ROUND_HALF_UP`.<br>两者均存在且此前值非零时为 `(current - previous) / previous * 100`；六位小数，`ROUND_HALF_UP`。 |
| `ctr_percentage_point_change` | `(current_ctr - previous_ctr) * 100`, using stored fractions; both must exist.<br>使用已存储比例计算 `(current_ctr - previous_ctr) * 100`；两者均须存在。 |
| `average_position_change` | `current_position - previous_position`; both must exist. Lower reported position numbers mean higher placement; no judgment label is generated.<br>`current_position - previous_position`；两者均须存在。较低报告排名数字表示更靠前位置；不生成判断标签。 |

If previous clicks are `NULL`, a known current value does not yield a change. If previous clicks are zero and current clicks are a measured nonzero value, absolute change is available but percentage change is `null`, never infinity. The same rules apply to impressions. Each metric is independent: missing CTR does not block a valid clicks comparison, and an eligible pair can have unavailable changes for several metrics. Do not replace missing values with zero, infer them from other metrics, or substitute carried-forward current values.
此前点击数为 `NULL` 时，已知当前值不会产生变化。此前点击数为零且当前点击数为测得的非零值时，绝对变化可用，但百分比变化为 `null`，绝不为无穷。展示数适用相同规则。各指标独立：缺失点击率不会阻止有效的点击数对比，合格对也可能有多个指标变化不可用。不要用零替代缺失值，不根据其他指标推导，也不代入沿用的当前值。

Changes are descriptive numbers. They do not establish causation, declare performance good/bad, assign opportunity scores, or generate recommendations. No AI is used for selection or arithmetic.
变化是描述性数值。它们不建立因果关系，不判断表现好坏，不分配机会评分，也不生成建议。选择与计算均不使用 AI。

## Phase 4 quality integration / 第四阶段质量集成

`analysis/data_quality.py` reuses the selected comparison and the same full history to report evidence limitations and page readiness. It does not duplicate arithmetic, change pair selection, modify records, or store observations. The embedded `quality` and dedicated quality endpoints are independent of snapshot pagination. See [data-quality.md](data-quality.md) for stable codes, severities, counts, and exact readiness rules.
`analysis/data_quality.py` 复用选中的对比及同一完整历史，报告证据限制与页面就绪度。它不重复计算、不改变对的选择、不修改记录，也不存储观察。内嵌 `quality` 与独立质量接口均独立于快照分页。稳定代码、严重程度、计数及准确就绪度规则详见 [data-quality.md](data-quality.md)。

An old report is provably imported out of order only when its stored `imported_at` is strictly later than newer-ended evidence in the same source/type/window/canonical-scope group. Equal timestamps do not establish ordering. Phase 6 makes selected unknown scope or partial/unknown coverage `limited`; no eligible pair remains `insufficient`. Current provenance follows explicit applied links, not newest reporting dates; older reports applied later can supply current values. Multiple validated known IDs prove `current_state_not_single_snapshot` only in the separate provenance result; unknown current origins are also separate and neither condition changes comparison readiness.
只有在同一来源、类型、窗口与规范范围组内，旧报告存储的 `imported_at` 严格晚于结束日期更新的证据时，才可证明乱序导入。相同时间戳不能确定顺序。第六阶段使所选未知范围或部分、未知覆盖为 `limited`；没有合格对仍为 `insufficient`。当前来源跟随明确已应用关联，不跟随最新报告日期；较早报告后来应用可提供当前值。多个已验证已知 ID 仅在独立来源结果中证明 `current_state_not_single_snapshot`；未知当前来源也单独报告，两种条件均不改变对比就绪度。

## Migration and limits / 迁移与限制

Upgrade with `uv run alembic upgrade head` from `backend/`. Phase 3 revision `0002_import_history` created run/snapshot history; Phase 5 `0003_current_metric_provenance` added empty source links without backfill. Phase 6 head `0004_report_scope` preserves every earlier page, run, snapshot, opportunity, provenance link, value, and timestamp while adding empty Sites and unknown legacy scope/coverage. Its downgrade refuses scoped URL/file collisions before changes; an allowed downgrade removes Phase 6 additions only. Older downgrades remove their own source/history tables after dependent revisions are removed. Model details are in [data-model.md](data-model.md).
在 `backend/` 中运行 `uv run alembic upgrade head` 升级。第三阶段修订 `0002_import_history` 创建导入与快照历史；第五阶段 `0003_current_metric_provenance` 增加空来源关联，不回填。第六阶段最新修订 `0004_report_scope` 保留每个此前页面、导入、快照、机会、来源关联、值与时间戳，同时增加空站点及未知旧范围与覆盖。其降级在修改前拒绝按范围存储的 URL 或文件冲突；允许的降级仅移除第六阶段新增内容。更早迁移在移除依赖修订后，移除各自来源或历史表。模型详情见 [data-model.md](data-model.md)。

This is a local development history interface. Explicit scope is recorded evidence, not authenticated property ownership, URL membership verification, or an automatic merger of domain/prefix properties into one physical website. Complete observed coverage certifies dates only, not all page rows. There is no authentication, permanent upload storage, failed-attempt log, full audit system, history edit/delete API, scheduling, or retention policy. Analysis loads full history in memory despite display pagination, and separate requests do not freeze concurrent imports. Legacy scope/coverage/provenance remain unknown; direct SQL can bypass controlled writers and equal-value edits remain undetectable. Scope/readiness do not prove source accuracy, independent periods, causation, or statistical significance. Tests use synthetic files; real exports stay outside Git. SEO opportunities, scoring, recommendations, Decision Engine, AI, integrations, execution, and production deployment remain outside Phase 6. Phase 7 has not started.
这是本地开发历史界面。明确范围是已记录证据，不是已认证属性归属、URL 成员关系验证，或自动将网域与前缀属性合并为一个物理网站。完整已观察覆盖仅证明日期，不证明全部页面行。没有身份认证、永久上传存储、失败尝试日志、完整审计系统、历史编辑删除 API、调度或保留策略。尽管显示分页，分析仍在内存中读取完整历史，独立请求不会冻结并发导入。旧范围、覆盖与来源保持未知；直接 SQL 可绕过受控写入器，相同值编辑仍无法检测。范围与就绪度不证明来源准确性、时间段独立性、因果关系或统计显著性。测试使用合成文件；真实导出保留在 Git 之外。SEO 机会、评分、建议、决策引擎、AI、集成、执行及生产部署仍不属于第六阶段。第七阶段尚未开始。
