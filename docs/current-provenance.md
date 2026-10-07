# Current metric provenance / 当前指标来源

## Scope and boundary / 范围与边界

Phase 5 answers which historical snapshot explicitly supplied each current GSC metric on `WebsitePage`. It tracks only `clicks_28d`, `impressions_28d`, `ctr`, and `average_position`. Current state means the latest successfully applied nonblank value, not necessarily the newest reporting period. Historical snapshots retain each file's normalized observations, including `NULL`.
第五阶段回答哪个历史快照明确提供了 `WebsitePage` 上的各个当前 GSC 指标。仅追踪 `clicks_28d`、`impressions_28d`、`ctr` 及 `average_position`。当前状态表示最近成功应用的非空白值，不一定属于最新报告时间段。历史快照保留每个文件的标准化观察，包括 `NULL`。

`analysis/current_provenance.py` validates recorded links without accessing the database, writing records, calling external services, or reconstructing an origin from equal values. It is separate from `performance_comparison.py` and `data_quality.py`. Provenance observations are factual source conditions, without SEO scores, recommendations, AI reasoning, or execution.
`analysis/current_provenance.py` 校验已记录关联，不访问数据库、不写入、不调用外部服务，也不根据相等值重建来源。它与 `performance_comparison.py` 及 `data_quality.py` 分开。来源观察属于事实来源条件，不包含 SEO 评分、建议、AI 推理或执行。

## Schema and migration / 数据库结构与迁移

`PageMetricProvenance` maps to `page_metric_provenance`, with exactly three required columns: `page_id`, `metric_name`, and `snapshot_id`. Its composite primary key `(page_id, metric_name)` permits one current link per supported metric per page. A check constraint limits names to the four fields above. Foreign keys reference `website_pages.id` and `page_performance_snapshots.id`, both with `ON DELETE RESTRICT`; `snapshot_id` has an index. The snapshot identifies the supplying import, so values and import IDs are not duplicated. An update timestamp is unnecessary for this contract.
`PageMetricProvenance` 对应 `page_metric_provenance`，恰有三个必填字段：`page_id`、`metric_name` 及 `snapshot_id`。复合主键 `(page_id, metric_name)` 允许每个页面的每个受支持指标只有一个当前关联。检查约束限定上述四个字段名。外键关联 `website_pages.id` 与 `page_performance_snapshots.id`，均使用 `ON DELETE RESTRICT`；`snapshot_id` 带索引。快照标识提供值的导入，因此不复制值或导入 ID。此契约不需要更新时间戳。

Run `uv run alembic upgrade head` from `backend/`. Revision `0003_current_metric_provenance`, following `0002_import_history`, creates an empty provenance table. It preserves every existing page, import, snapshot, and opportunity value and creates no legacy links. Matching metric values do not justify backfill. Downgrading to `0002_import_history` removes only the current links; values and historical rows remain intact. Re-upgrading creates empty links again.
在 `backend/` 中运行 `uv run alembic upgrade head`。修订 `0003_current_metric_provenance` 继承 `0002_import_history`，创建空来源表。它保留每个已有页面、导入、快照及机会值，不创建旧来源关联。指标值相等不能成为回填理由。降级至 `0002_import_history` 仅移除当前关联；值及历史记录保持完整。再次升级会重新创建空关联表。

Simple foreign keys enforce existence, not that a snapshot belongs to the referenced page or supplies the specified metric. The writer constructs each link from the same normalized row and page; read analysis verifies that association. Direct SQL can bypass these application checks. No composite foreign key, trigger, or audit infrastructure is added.
简单外键约束引用存在，不约束快照属于所引用页面或提供指定指标。写入器根据同一标准化行及页面构建各个关联；读取分析校验该关联。直接 SQL 可绕过这些应用检查。不增加复合外键、触发器或审计基础设施。

## Atomic import behavior / 原子导入行为

One successful new import commits `ImportRun`, current page changes, `PagePerformanceSnapshot` rows, and provenance upserts in the existing transaction. Snapshots are flushed before referencing links. Existing page row locks remain held through commit, and provenance upserts use bounded batches. A failure after any provenance write rolls back all four targets, including earlier page or link changes in that transaction.
一个新的成功导入在已有事务内提交 `ImportRun`、当前页面变化、`PagePerformanceSnapshot` 行及来源新增或更新。快照在关联引用之前写入。已有页面行锁保持至提交，来源写入使用有大小限制的批次。任一来源写入后失败会回滚全部四个目标，包括该事务中此前的页面或关联变化。

| Incoming metric / 传入指标 | Current value and source / 当前值与来源 |
| --- | --- |
| Non-`NULL` / 非 `NULL` | Apply the supplied value and point that metric to this new snapshot.<br>应用提供值，并将该指标指向本次新快照。 |
| Same numerical value / 相同数值 | Keep the value but refresh the source to this new snapshot; explicit re-observation is still evidence.<br>保留值，但刷新来源至本次新快照；明确再次观察仍是证据。 |
| `NULL` or blank / `NULL` 或空白 | Preserve both the previous current value and its source. A legacy unknown source remains absent.<br>同时保留此前当前值及来源。未知旧来源保持缺失。 |
| Measured zero / 测得零 | Store zero and refresh its source; zero is never blank.<br>存储零并刷新来源；零绝不是空白。 |
| New page / 新页面 | Create links only for supplied non-`NULL` metrics; other values remain `NULL` without links.<br>仅为提供的非 `NULL` 指标创建关联；其他值保持 `NULL`，没有关联。 |
| Identical-file retry / 相同文件重试 | Return the original import ID without rewriting values, links, or history.<br>返回原导入 ID，不重写值、关联或历史。 |
| Older report applied later / 较早报告后来应用 | Its supplied fields become the current values and sources, following apply order.<br>其提供字段按应用顺序成为当前值及来源。 |

For example, snapshot A supplies clicks `12` and impressions `500`. Snapshot B supplies clicks `12` but blank impressions. Current clicks remain `12` and now point to B; impressions remain `500` and point to A. If impressions had no legacy source link, they would remain unknown instead. A later measured clicks `0` moves clicks to that new snapshot. Retrying A's identical bytes restores neither old values nor old sources.
例如，快照 A 提供点击 `12` 及展示 `500`。快照 B 提供点击 `12`，但展示为空白。当前点击保持 `12`，现指向 B；展示保持 `500`，指向 A。如果展示没有旧来源关联，则保持未知。后来测得点击 `0` 会将点击来源移至该新快照。重试 A 的相同字节不会恢复旧值或旧来源。

Import counts still describe numeric page outcomes: a same-value page can count as skipped while its provenance refreshes. `WebsitePage.updated_at` continues to follow actual page-field changes; it does not describe the last provenance refresh. Import timestamps are stored metadata, not a replacement for the explicit source link or a certification of transaction commit order.
导入计数仍描述页面数值处理结果：相同值页面可计为跳过，同时刷新来源。`WebsitePage.updated_at` 继续跟随实际页面字段变化；它不描述最近来源刷新。导入时间戳是存储元数据，不能替代明确来源关联，也不能证明事务提交顺序。

## Provenance status / 来源状态

| Status / 状态 | Deterministic rule / 确定性规则 |
| --- | --- |
| `known` | The current metric is non-`NULL`, exactly one recorded link resolves to this page's snapshot and import, and the snapshot supplied a non-`NULL` value equal to the current value.<br>当前指标非 `NULL`，恰有一个已记录关联解析到本页面快照及导入，且快照提供了与当前值相等的非 `NULL` 值。 |
| `unknown` | The current metric is non-`NULL` but has no valid recorded source. Missing, stale, cross-page, or inconsistent links do not establish provenance.<br>当前指标非 `NULL`，但没有有效已记录来源。缺失、过时、跨页面或不一致关联不能证明来源。 |
| `unavailable` | The current metric itself is `NULL`, even if an invalid or stale link exists.<br>当前指标本身为 `NULL`，即使存在无效或过时关联。 |

Equality checks consistency only after an explicit link exists. The analyzer never searches equal-valued historical snapshots to establish a missing source. Thus existing values with matching history remain unknown after migration. Only `known` entries expose snapshot/import/date/time metadata; `unknown` and `unavailable` entries return `null` for all source metadata. A known source may legitimately have unknown reporting dates, as with CSV imports.
相等性仅在明确关联存在之后检查一致性。分析器绝不搜索数值相等的历史快照来建立缺失来源。因此，具有匹配历史的已有值在迁移后仍保持未知。只有 `known` 条目公开快照、导入、日期及时间元数据；`unknown` 与 `unavailable` 条目的所有来源元数据返回 `null`。已知来源可以具有未知报告日期，例如 CSV 导入。

## Observations and readiness / 观察与就绪度

`unknown_current_metric_provenance` has `warning` severity when one or more current non-`NULL` metrics lack proven sources. Its evidence identifies the affected metric names and count. `NULL` current metrics do not contribute to this observation.
当一个或多个当前非 `NULL` 指标缺少已证明来源时，`unknown_current_metric_provenance` 具有 `warning` 严重程度。证据标识受影响指标名称及数量。当前 `NULL` 指标不产生此观察。

`current_state_not_single_snapshot` has `info` severity only when at least two current metrics with valid known sources reference different snapshot IDs. Evidence contains those IDs, their import IDs, and metric-source mappings. Unknown sources alone never prove a mixed state. Different snapshot IDs suffice even if numerical values or period bounds happen to match.
仅当至少两个具有有效已知来源的当前指标引用不同快照 ID 时，`current_state_not_single_snapshot` 具有 `info` 严重程度。证据包含这些 ID、其导入 ID 及指标来源映射。仅有未知来源不能证明混合状态。不同快照 ID 即构成证据，即使数值或时间段范围碰巧相同。

Provenance observations are returned in the sibling `provenance` object and shown next to data quality. They do not modify Phase 4 quality observations, counts, readiness, selected snapshots, or Phase 3 calculations. Historical comparison uses source snapshots, not merged current values. A `ready` historical comparison may therefore coexist with mixed or unknown current provenance.
来源观察在并列的 `provenance` 对象中返回，并在数据质量旁显示。它们不修改第四阶段质量观察、计数、就绪度、所选快照或第三阶段计算。历史对比使用来源快照，不使用合并的当前值。因此，`ready` 历史对比可以与混合或未知当前来源同时存在。

## API and interface / API 与界面

```sh
curl 'http://localhost:8000/api/v1/pages/PAGE_UUID/provenance'
curl 'http://localhost:8000/api/v1/pages/PAGE_UUID/performance?page=1&page_size=50'
```

The dedicated response and the embedded `provenance` object are identical for unchanged data. They contain `page_id`, four ordered `metrics` (`clicks_28d`, `impressions_28d`, `ctr`, `average_position`), `known_provenance_count`, `unknown_provenance_count`, `unavailable_metric_count`, `all_known_metrics_share_one_snapshot`, `distinct_snapshot_ids`, and `observations`. Each metric includes `metric_name`, `current_value`, `status`, `snapshot_id`, `import_run_id`, `period_start`, `period_end`, and `imported_at`. Decimal values serialize as strings; absent values/metadata serialize as `null`.
数据不变时，独立响应与内嵌 `provenance` 对象相同。它们包含 `page_id`、四个按顺序排列的 `metrics`（`clicks_28d`、`impressions_28d`、`ctr`、`average_position`）、`known_provenance_count`、`unknown_provenance_count`、`unavailable_metric_count`、`all_known_metrics_share_one_snapshot`、`distinct_snapshot_ids` 及 `observations`。各指标包含 `metric_name`、`current_value`、`status`、`snapshot_id`、`import_run_id`、`period_start`、`period_end` 及 `imported_at`。十进制值序列化为字符串；缺失值或元数据序列化为 `null`。

The three counts sum to four. `distinct_snapshot_ids` contains sorted IDs from known metrics only. `all_known_metrics_share_one_snapshot` is `null` when none are known, `true` for one distinct known snapshot, and `false` for multiple known snapshots. `true` does not claim that unknown or unavailable fields have proven sources, nor that all four fields were supplied together.
三个计数之和为四。`distinct_snapshot_ids` 仅包含已知指标的排序 ID。无已知指标时，`all_known_metrics_share_one_snapshot` 为 `null`；只有一个不同的已知快照时为 `true`；多个已知快照时为 `false`。`true` 不表示未知或不可用字段具有已证明来源，也不表示四个字段一起提供。

The shared history loader reads full snapshots once and reuses them for comparison, quality, and provenance. Performance/provenance requests add one query for current links (three SELECTs total); quality-only requests retain two SELECTs without reading links. All results are independent of displayed snapshot pagination. The frontend uses embedded provenance, avoiding an extra request. The dedicated endpoint returns `404` for an unknown page, `422` for an invalid UUID, and generic `503` database failures without private details. No provenance mutation endpoint exists.
共享历史读取流程仅读取一次完整快照，并将其复用于对比、质量及来源。性能或来源请求增加一个当前关联查询（共三个 SELECT）；仅质量请求保持两个 SELECT，不读取关联。全部结果独立于显示的快照分页。前端使用内嵌来源，避免额外请求。独立接口对未知页面返回 `404`，无效 UUID 返回 `422`，数据库失败返回不含私人细节的通用 `503`。没有来源修改接口。

`/pages/[id]` distinguishes current applied state, per-field sources, historical snapshots in import order, and the selected reporting-period comparison. Its bilingual provenance section shows each value, source status, snapshot/import IDs, reporting dates or explicitly unknown dates, and import timestamp. Current source conditions remain a development evidence view.
`/pages/[id]` 区分当前已应用状态、逐字段来源、按导入顺序排列的历史快照及所选报告时间段对比。双语来源区域显示各个值、来源状态、快照或导入 ID、报告日期或明确未知日期及导入时间戳。当前来源条件仍是开发证据视图。

## Verification and limits / 验证与限制

Synthetic unit, PostgreSQL persistence, migration, and API tests cover the import rules, constraint integrity, no backfill, preservation of every legacy column, rollback after completed provenance writes, concurrent imports, invalid source links, NULL/zero handling, pagination independence, unchanged readiness, read-only requests, and absence of external calls or opportunity generation. Browser checks cover provenance statuses, source refresh, mixed state, retries, apply chronology, and error handling. Private GSC exports remain outside Git.
合成单元、PostgreSQL 持久化、迁移及 API 测试覆盖导入规则、约束完整性、不回填、每个旧字段保留、已完成来源写入之后的回滚、并发导入、无效来源关联、NULL 或零处理、分页独立性、就绪度不变、只读请求，以及无外部调用或机会生成。浏览器检查覆盖来源状态、来源刷新、混合状态、重试、应用时间顺序及错误处理。私人 GSC 导出保留在 Git 之外。

This contract trusts the controlled import writer and append-only application history. Direct SQL can forge links or alter current/snapshot values. A different-value edit invalidates the recorded link at read time; an equal-value edit or coordinated tampering cannot be detected reliably. There is no database audit trail, origin backfill, or automatic link repair. Earlier imports may have no history. Provenance identifies the supplying stored observation, without certifying source accuracy, GSC property/filter scope, export coverage, or statistical significance. Full page history is loaded in memory, and concurrent imports are not frozen across separate pagination requests.
此契约信任受控导入写入器及应用的追加历史。直接 SQL 可伪造关联或修改当前值与快照值。不同值编辑会在读取时使已记录关联失效；相同值编辑或协同篡改无法可靠检测。没有数据库审计记录、来源回填或自动关联修复。较早导入可能没有历史。来源追踪标识提供值的已存储观察，不证明来源准确性、GSC 属性或筛选范围、导出覆盖或统计显著性。完整页面历史在内存中读取，不会跨独立分页请求冻结并发导入。

Phase 6 has not started. A focused next step would record explicit report/property/filter context and observed date coverage, then restrict compatible comparisons using that recorded evidence. Unknown legacy scope should remain unknown; this need not add SEO scores, AI, recommendations, or execution.
第六阶段尚未开始。下一步可集中记录明确报告、属性与筛选背景及已观察日期覆盖，再使用这些已记录证据限定兼容对比。未知旧范围应保持未知；无需增加 SEO 评分、AI、建议或执行。
