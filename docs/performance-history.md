# Performance history / 性能历史

## Current state and observations / 当前状态与观察

`WebsitePage` keeps the latest successfully applied nonblank metrics, preserving Phase 2 behavior. A newer upload can omit a metric and leave its older value unchanged. Uploading an older report later can also update current state. Therefore, current metrics need not belong to one report or the latest reporting period.
`WebsitePage` 保留最近成功应用的非空白指标，沿用第二阶段行为。较新的上传可省略指标，使其较早值保持不变。后来上传较早报告也可更新当前状态。因此，当前指标不一定属于同一个报告或最新报告时间段。

`ImportRun` records a successful file import and its source, hash, filename, reporting window, known dates, import time, and current-page outcome counts. `PagePerformanceSnapshot` records each imported page's normalized observations for that run. A snapshot's missing metric is `NULL`, even when the current page retains an older value. Use these snapshots for period comparison; never reconstruct history from the current page.
`ImportRun` 记录成功文件导入及其来源、哈希、文件名、报告窗口、已知日期、导入时间与当前页面处理统计。`PagePerformanceSnapshot` 记录该导入中每个页面的标准化观察。快照的缺失指标为 `NULL`，即使当前页面保留了较早值。时间段对比使用这些快照；绝不从当前页面重建历史。

Historical source identifiers are `source="gsc"`, `source_type="pages_performance"`, and `reporting_window="latest_28_days"`. The preview retains `source="gsc_pages"`. Both use the existing English/Chinese GSC importer and deterministic normalization.
历史来源标识为 `source="gsc"`、`source_type="pages_performance"` 与 `reporting_window="latest_28_days"`。预览保留 `source="gsc_pages"`。两者使用现有英文与中文 GSC 导入器及确定性标准化。

## Successful-import lifecycle / 成功导入生命周期

1. Preview parses, validates, normalizes, and extracts available period dates without any database access or history writes.
   预览解析、校验、标准化并提取可用时间段日期，不访问数据库，也不写入历史。
2. Apply requires the file again, `confirmed=true`, and its preview SHA-256 hash. Revalidation remains mandatory.
   应用要求再次提交文件、`confirmed=true` 及其预览 SHA-256 哈希。重新校验仍为必需。
3. A new file hash updates current pages, creates one completed run and one snapshot per validated page, and refreshes current provenance for every supplied non-`NULL` metric. Same-value pages still get snapshots and refreshed sources even when counted as skipped.
   新文件哈希更新当前页面、创建一个已完成导入及每个已校验页面的一条快照，并为每个提供的非 `NULL` 指标刷新当前来源。相同值页面即使计为跳过，也会获得快照及刷新来源。
4. All four write targets commit in one transaction. Failure in a page, run, snapshot, or provenance write rolls back every write. Preview, invalid files, and failed attempts create no retained run; there is no separate failed-attempt lifecycle.
   全部四个写入目标在一个事务内提交。页面、导入、快照或来源写入失败会回滚全部写入。预览、无效文件及失败尝试不创建保留的导入；没有独立的失败尝试生命周期。

Only `status="completed"` runs are persisted by this workflow. Run row counts describe current-page creates, updates, and skips; they do not count snapshots. A new file with unchanged current-page metrics still creates history and snapshots. The service does not edit or delete historical records.
此流程仅持久化 `status="completed"` 的导入。导入行数描述当前页面新增、更新与跳过，不统计快照。新文件即使当前页面指标未变化，也会创建历史与快照。服务不编辑或删除历史记录。

## Identical-file handling / 相同文件处理

Uniqueness on `(source, source_type, file_hash)` prevents duplicate successful imports. Exact repeated bytes return `already_processed=true`, the original `import_run_id`, `created_count=0`, `updated_count=0`, `skipped_count=total_rows`, and `error_count=0`. No new run or snapshot is created, and current pages are not rewritten. This remains true if a different file updated those pages after the original import; retrying the old file does not restore old metrics. The original run's filename and outcome counts remain unchanged.
`(source, source_type, file_hash)` 唯一性防止成功导入重复。完全相同的重复字节返回 `already_processed=true`、原 `import_run_id`、`created_count=0`、`updated_count=0`、`skipped_count=total_rows` 与 `error_count=0`。不创建新的导入或快照，也不重写当前页面。即使原导入之后另一个文件更新了这些页面，此行为仍成立；重试旧文件不会恢复旧指标。原导入的文件名与处理统计保持不变。

The hash represents uploaded bytes, not the filename or semantic equality of rows. Same filename with changed contents creates a new run. Renaming identical bytes does not. Different CSV formatting or XLSX packaging can produce a new hash even when metrics match. Multiple different files with the same date bounds remain in history. For one page/source/type/window and exact period, comparison chooses its latest imported snapshot revision. Matching import-level dates alone do not prove the same GSC property or filter scope.
哈希代表上传字节，不代表文件名或行的语义等价性。同名但内容变化会创建新导入。重命名相同字节不会。CSV 格式或 XLSX 打包方式不同，即使指标相同，也可能产生新哈希。日期范围相同的多个不同文件保留在历史中。对于同一页面、来源、类型、窗口及准确时间段，对比选择其最近导入的快照修订。仅有导入级日期匹配，不能证明同一 GSC 属性或筛选范围。

## Reporting-period extraction / 报告时间段提取

The latest-28-day filter validation from Phase 2 remains unchanged. Separately, GSC-specific extraction examines normalized worksheet names `Chart`, `Date`, `Dates`, `图表`, and `日期`. The first nonblank row must contain exactly one recognized `Date`, `Dates`, or `日期` header. Sheets without recognized date headers provide no evidence.
第二阶段的最近 28 天筛选校验保持不变。另由 GSC 专用提取检查标准化工作表名称 `Chart`、`Date`、`Dates`、`图表` 与 `日期`。首个非空白行必须包含恰好一个已识别的 `Date`、`Dates` 或 `日期` 表头。没有已识别日期表头的工作表不提供证据。

Date cells accept native Excel dates/datetimes (use their calendar date) or trimmed strict `YYYY-MM-DD` text. Ignore fully blank rows. Every nonblank data row must contain a valid date; missing, malformed, formula, or non-date values make the period unknown rather than inventing a date. Unsorted dates and duplicate days are allowed. Use the earliest and latest observed dates without requiring 28 unique or consecutive days.
日期单元格接受原生 Excel 日期或日期时间（使用其日历日期），或去除前后空白的严格 `YYYY-MM-DD` 文本。忽略完全空白行。每个非空白数据行都必须包含有效日期；缺失、格式错误、公式或非日期值使时间段未知，不编造日期。允许未排序日期与重复天数。使用最早与最晚已观察日期，不要求 28 个唯一或连续日期。

When multiple usable recognized date worksheets exist, their distinct observed date sets must agree. Conflicting evidence, ambiguous date headers, or a malformed candidate yields an unknown period. Missing usable evidence, including CSV, also yields `period_start=null`, `period_end=null`, and `period_status="unknown"`. The valid page import may continue. Both endpoints present produce `period_status="exact"`; this means observed endpoints are known, not that complete 28-day coverage is certified.
存在多个可用的已识别日期工作表时，其不同的已观察日期集合必须一致。冲突证据、歧义日期表头或损坏的候选表会产生未知时间段。缺少可用证据时，包括 CSV，也会产生 `period_start=null`、`period_end=null` 与 `period_status="unknown"`。有效页面导入仍可继续。两个起止日期均存在时产生 `period_status="exact"`；这表示已观察起止日期已知，不表示完整的 28 天覆盖已获证明。

Never derive dates from filenames, import timestamps, filter labels alone, or current metrics. Native reporting dates are calendar dates, not UTC instants. Date worksheets retain the physical-row bound of 10,000 even when evidence is invalid; exceeding it returns `413`. Unknown dates are visible in preview/history and excluded from comparison.
绝不从文件名、导入时间戳、单独的筛选标签或当前指标推导日期。原生报告日期是日历日期，不是 UTC 时间点。日期工作表即使证据无效，也保留 10,000 个物理行的限制；超出返回 `413`。未知日期在预览与历史中可见，并从对比中排除。

## Read-only APIs and UI / 只读 API 与界面

```sh
curl 'http://localhost:8000/api/v1/imports?page=1&page_size=50'
curl 'http://localhost:8000/api/v1/pages/PAGE_UUID/performance?page=1&page_size=50'
```

Replace `PAGE_UUID` with a page ID from `GET /api/v1/pages`. Both history endpoints return `items`, `page`, `page_size`, `total`, and `total_pages`; `page` starts at 1 and `page_size` defaults to 50 with a maximum of 100. Empty histories have zero total pages; a page beyond the end returns empty items. Invalid parameters return `422`, an unknown page returns `404`, and database errors return useful `503` responses without internal stack traces.
将 `PAGE_UUID` 替换为 `GET /api/v1/pages` 返回的页面 ID。两个历史接口返回 `items`、`page`、`page_size`、`total` 与 `total_pages`；`page` 从 1 开始，`page_size` 默认 50，最大 100。空历史的总页数为零；超出末页的页面返回空条目。无效参数返回 `422`，未知页面返回 `404`，数据库错误返回有用的 `503` 响应，不包含内部堆栈。

- `GET /api/v1/imports` lists runs newest import first. Items include `id`, `source`, `source_type`, `file_hash`, `filename`, `reporting_window`, `period_start`, `period_end`, `period_status`, `imported_at`, `total_rows`, `created_count`, `updated_count`, `skipped_count`, and `status`.
  `GET /api/v1/imports` 按最新导入在前列出记录。条目包含 `id`、`source`、`source_type`、`file_hash`、`filename`、`reporting_window`、`period_start`、`period_end`、`period_status`、`imported_at`、`total_rows`、`created_count`、`updated_count`、`skipped_count` 与 `status`。
- `GET /api/v1/pages/{page_id}/performance` also returns `current_page`, `comparison`, `comparison_unavailable_reason`, and runtime `quality`. Snapshots are ordered by `imported_at`, then snapshot `id`, ascending. Items include snapshot/run/page IDs, URL, source/type/window, period dates/status, import/creation timestamps, and `clicks`, `impressions`, `ctr`, and `average_position`. This is chronological import order, which may differ from reporting-date order.
  `GET /api/v1/pages/{page_id}/performance` 还返回 `current_page`、`comparison`、`comparison_unavailable_reason` 与运行时 `quality`。快照按 `imported_at`、其次快照 `id` 升序排列。条目包含快照、导入、页面 ID、URL、来源与类型、窗口、时间段日期与状态、导入与创建时间戳，以及 `clicks`、`impressions`、`ctr` 与 `average_position`。这是导入时间顺序，可能与报告日期顺序不同。

Dates serialize as ISO calendar dates; timestamps retain offsets. Decimal metrics/changes serialize as strings and missing values as `null`. `period_status` is computed from the paired date fields, without a separate persisted flag. Pagination uses offsets and does not freeze history across concurrent imports.
日期序列化为 ISO 日历日期；时间戳保留偏移。小数指标与变化序列化为字符串，缺失值序列化为 `null`。`period_status` 根据成对日期字段计算，不另行持久化标记。分页使用偏移量，不会跨并发导入冻结历史。

Phase 5 also embeds `provenance` in the performance response and exposes the same object through `GET /api/v1/pages/{page_id}/provenance`. The shared loader uses full history and one current-link query, so provenance is independent of snapshot pagination and the browser needs no extra request. The UI labels current state as "Current applied metrics" and displays per-field sources separately from report-period comparison. See [current-provenance.md](current-provenance.md) for the exact status and summary contracts.
第五阶段还在性能响应中内嵌 `provenance`，并通过 `GET /api/v1/pages/{page_id}/provenance` 提供相同对象。共享读取流程使用完整历史及一个当前关联查询，因此来源独立于快照分页，浏览器不需要额外请求。界面将当前状态标为“当前已应用指标”，并将逐字段来源与报告时间段对比分开显示。准确状态及摘要契约详见 [current-provenance.md](current-provenance.md)。

The `/imports/history` development screen shows successful runs, dates or unknown status, counts, and import status. `/pages` links to `/pages/[id]`, which separates current stored metrics from historical snapshots, the selected period comparison, and its data-quality section. There are no editing/deletion controls or final SEO dashboard.
`/imports/history` 开发页面显示成功导入、日期或未知状态、计数及导入状态。`/pages` 链接到 `/pages/[id]`，后者将当前存储指标与历史快照、选中的时间段对比及其数据质量部分分开显示。没有编辑删除控制或最终 SEO 仪表盘。

## Compatible comparison selection / 兼容对比选择

Comparison belongs in `analysis/performance_comparison.py`, outside GSC parsing and persistence. Candidates must share the page, source, source type, reporting window, and inclusive period length; both endpoints must be known. Group revisions by exact `(period_start, period_end)` and select the latest imported revision, with IDs as deterministic ties. Revisions are not merged to fill missing metrics.
对比属于 `analysis/performance_comparison.py`，位于 GSC 解析与持久化之外。候选必须具有相同页面、来源、来源类型、报告窗口与包含起止日的时间段长度；两个起止日期均必须已知。按准确的 `(period_start, period_end)` 将修订分组，选择最近导入的修订，以 ID 确定性处理并列。不合并修订以填补缺失指标。

Within each compatible group, select its latest two distinct reporting periods. Choose the eligible pair with the newest current reporting period, using deterministic import/ID ties. If a newer snapshot has no compatible partner, an older compatible pair can still be shown. Comparison uses all history, independently of the requested snapshot pagination page and latest applied current metrics. The response names both snapshot IDs and both actual periods so the selection is explicit.
在每个兼容组内选择其最近两个不同报告时间段。选择当前报告时间段最新的合格对，使用导入及 ID 确定性处理并列。如果较新快照没有兼容伙伴，仍可显示较早的兼容对。对比使用全部历史，与请求的快照分页页码及最近应用的当前指标独立。响应标明两个快照 ID 及两个实际时间段，使选择明确。

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

An old report is provably imported out of order only when its stored `imported_at` is strictly later than evidence with a newer `period_end` in the same source/type/window group. Equal timestamps do not establish this ordering. Current provenance follows explicit applied source links, not the newest reporting date; older reports applied later can supply current values. Multiple validated known source IDs now prove `current_state_not_single_snapshot` in the separate provenance result. Unknown current origins are reported separately, and neither condition changes historical comparison readiness.
只有在同一来源、类型、窗口组内，旧报告存储的 `imported_at` 严格晚于具有更新 `period_end` 的证据时，才可证明其乱序导入。相同时间戳不能确定该顺序。当前来源跟随明确已应用来源关联，不跟随最新报告日期；较早报告后来应用可提供当前值。多个已验证已知来源 ID 现在可在独立来源结果中证明 `current_state_not_single_snapshot`。未知当前来源单独报告，两种条件均不改变历史对比就绪度。

## Migration and limits / 迁移与限制

Upgrade with `uv run alembic upgrade head` from `backend/`. Phase 3 revision `0002_import_history` created run/snapshot history; Phase 5 head `0003_current_metric_provenance` adds only an empty source-link table, preserving all existing values and history without backfill. Downgrading Phase 5 removes links only. Downgrading Phase 3 after its dependent revision removes history tables while retaining current pages. Model details are in [data-model.md](data-model.md).
在 `backend/` 中运行 `uv run alembic upgrade head` 升级。第三阶段修订 `0002_import_history` 创建导入与快照历史；第五阶段最新修订 `0003_current_metric_provenance` 仅增加空来源关联表，保留所有已有值及历史，不回填。降级第五阶段仅移除关联。在依赖修订之后降级第三阶段，会移除历史表，同时保留当前页面。模型详情见 [data-model.md](data-model.md)。

This is a local development history interface. There is no authentication, per-site ownership/filter provenance, permanent upload storage, failed-attempt log, full audit system, history edit/delete API, scheduling, or retention policy. Comparison, quality, and provenance load full page history in memory despite display pagination. Known dates and readiness do not certify complete coverage, matching filters, source accuracy, independent periods, or statistical significance. Legacy origins stay unknown, and direct SQL can bypass source-link protection; equal-value manual changes remain undetectable. Tests use synthetic files; real exports stay outside Git. Scoring, recommendations, Decision Engine, AI, integrations, execution, and production deployment remain outside Phase 5. Phase 6 has not started.
这是本地开发历史界面。没有身份认证、站点归属与筛选来源追踪、永久上传存储、失败尝试日志、完整审计系统、历史编辑删除 API、调度或保留策略。尽管显示分页，对比、质量及来源仍在内存中读取完整页面历史。已知日期及就绪度不证明完整覆盖、筛选一致、来源准确性、时间段独立或统计显著性。旧来源保持未知，直接 SQL 可绕过关联保护；相同值手动变化仍无法检测。测试使用合成文件；真实导出保留在 Git 之外。评分、建议、决策引擎、AI、集成、执行及生产部署仍不属于第五阶段。第六阶段尚未开始。
