# Data quality and evidence readiness / 数据质量与证据就绪度

## Scope and boundary / 范围与边界

Phase 4 explains the factual evidence available for descriptive GSC page-performance comparison: known dates, compatible history, missing metrics, overlap, repeated periods, import chronology, and zero percentage baselines. It produces no SEO quality label, opportunity, priority, action, numeric score, or AI output.
第四阶段解释可用于描述性 GSC 页面性能对比的事实证据：已知日期、兼容历史、缺失指标、重叠、重复时间段、导入时间顺序及零百分比基准。不产生 SEO 质量标签、机会、优先级、行动、数值评分或 AI 输出。

`analysis/performance_comparison.py` continues to select the Phase 3 pair and calculate changes. `analysis/data_quality.py` consumes the comparison result, full snapshot history, and import metadata to explain evidence limitations. It neither duplicates arithmetic nor changes the selected pair. The analysis functions are deterministic and have no database access, writes, external calls, or observation persistence.
`analysis/performance_comparison.py` 继续选择第三阶段对比对并计算变化。`analysis/data_quality.py` 使用对比结果、完整快照历史及导入元数据解释证据限制。它既不重复计算，也不改变所选对。分析函数具有确定性，不访问数据库、不写入、不调用外部服务，也不持久化观察。

No migration is required. Schema head remains `0002_import_history`; existing `WebsitePage`, `ImportRun`, and `PagePerformanceSnapshot` records are read unchanged. Quality requests do not fill `NULL`, rewrite history, or create `SEOOpportunity` records. The import validation and atomic persistence contracts are unchanged.
无需迁移。数据库结构最新修订仍为 `0002_import_history`；已有 `WebsitePage`、`ImportRun` 与 `PagePerformanceSnapshot` 记录保持不变地读取。质量请求不填补 `NULL`、不重写历史，也不创建 `SEOOpportunity` 记录。导入校验及原子持久化契约保持不变。

## Observation contract / 观察契约

Each observation has `code`, `severity`, `scope`, bilingual `message`, `snapshot_ids`, `import_run_ids`, and a structured JSON `evidence` dictionary. IDs identify the supporting records; the evidence reports concrete dates, metrics/fields, counts, or chronology. One observation per applicable code aggregates its affected evidence. Code order and ID ordering are deterministic; codes are stable machine-readable identifiers.
每条观察包含 `code`、`severity`、`scope`、双语 `message`、`snapshot_ids`、`import_run_ids` 及结构化 JSON `evidence` 字典。ID 标识支持记录；证据报告具体日期、指标或字段、计数或时间顺序。每个适用代码的一条观察汇总其受影响证据。代码与 ID 排序具有确定性；代码为稳定的机器可读标识。

| Severity / 严重程度 | Meaning / 含义 |
| --- | --- |
| `info` | A factual context item, such as repeated exact periods; it does not lower readiness by itself.<br>事实背景条目，例如重复准确时间段；本身不降低就绪度。 |
| `warning` | A supported evidence limitation; its relevance to the selected pair determines readiness.<br>有证据支持的限制；与所选对的相关性决定就绪度。 |
| `blocking` | No compatible exact comparison is available from stored history. It does not invalidate a successful import or reject a valid upload.<br>已存储历史中没有可用兼容准确对比。不否定成功导入，也不拒绝有效上传。 |

Severity concerns evidence, without any judgment about page performance. `scope` is `page` or `import`. The same code can apply in either scope, with evidence appropriate to that scope.
严重程度涉及证据，不判断页面表现。`scope` 为 `page` 或 `import`。相同代码可用于任一范围，并提供适合该范围的证据。

## Page observation codes / 页面观察代码

Page history is scoped by actual `page_id`. Exact-period grouping uses page, source, source type, reporting window, and both date bounds. Comparison compatibility additionally requires equal period lengths, as defined in [performance-history.md](performance-history.md).
页面历史按实际 `page_id` 限定。准确时间段分组使用页面、来源、来源类型、报告窗口及两个日期边界。对比兼容性还要求时间段长度相同，定义见 [performance-history.md](performance-history.md)。

| Code / 代码 | Severity / 严重程度 | Condition and evidence / 条件与证据 |
| --- | --- | --- |
| `insufficient_history` | `blocking` | Phase 3 supplied no compatible comparison. Evidence includes its unavailable reason and history counts; zero history, one observation, unknown dates, or only one compatible distinct period can cause this.<br>第三阶段未提供兼容对比。证据包含不可用原因与历史计数；零历史、一个观察、未知日期或只有一个兼容不同时间段均可能导致此情况。 |
| `unknown_reporting_dates` | `warning` | At least one snapshot lacks date endpoints. Evidence lists affected snapshot/run IDs, source/window, dates, import times, and count.<br>至少一个快照缺少起止日期。证据列出受影响快照与导入 ID、来源与窗口、日期、导入时间及数量。 |
| `overlapping_comparison_periods` | `warning` | The selected pair has inclusive overlap. Evidence names both periods and their overlap start/end; no other pair is substituted.<br>所选对存在包含起止日的重叠。证据标明两个时间段及重叠起止日期；不替换为其他对。 |
| `missing_metrics` | `warning` | At least one snapshot has `NULL` clicks, impressions, CTR, or average position. Evidence maps snapshot IDs to missing field names and counts snapshots, not missing cells.<br>至少一个快照的点击数、展示数、点击率或平均排名为 `NULL`。证据将快照 ID 映射到缺失字段名，统计快照数，不统计缺失单元格数。 |
| `zero_percentage_baseline` | `warning` | In the selected pair, previous clicks or impressions are known zero and the current count is known, including zero. Evidence identifies each metric and both values; percentage change remains `null`.<br>所选对的此前点击数或展示数为已知零，且当前计数已知，包括零。证据标识各指标与两个值；百分比变化保持 `null`。 |
| `same_period_revisions` | `info` | An exact-period group has more than one distinct import ID for the page. Evidence lists each source/window/date group and its snapshot/run IDs. Phase 3 retains the latest imported revision for selection only.<br>页面的准确时间段组具有多个不同导入 ID。证据列出各来源、窗口、日期组及其快照与导入 ID。第三阶段仅在选择时使用最近导入的修订。 |
| `out_of_order_import` | `warning` | A snapshot with an older `period_end` was imported strictly after a snapshot with a newer end in the same page/source/type/window group. Evidence pairs each offending older snapshot with one earlier-imported newer-period witness.<br>在同一页面、来源、类型、窗口组内，具有较早 `period_end` 的快照严格晚于具有较新结束日期的快照导入。证据将每个乱序旧快照与一个较早导入的较新时间段证据配对。 |

Equal `imported_at` timestamps cannot prove out-of-order chronology. IDs may break display ties but do not create temporal evidence. Same-period revisions have matching ends and do not establish an older-period case. Unknown dates are excluded from overlap/revision/chronology checks requiring exact dates.
相同 `imported_at` 时间戳不能证明乱序时间顺序。ID 可处理显示并列，但不创建时间证据。同时间段修订的结束日期相同，不构成较早时间段情况。未知日期从需要准确日期的重叠、修订与时间顺序检查中排除。

## Exact page-readiness rules / 准确的页面就绪度规则

Readiness applies to the exact pair selected by Phase 3, not to every snapshot in history. It uses no numerical score or SEO threshold.
就绪度应用于第三阶段选中的准确对，不应用于历史中的每个快照。不使用数值评分或 SEO 阈值。

| State / 状态 | Deterministic rule / 确定性规则 |
| --- | --- |
| `insufficient` | No Phase 3 compatible exact-period comparison exists; `readiness_reasons` contains `insufficient_history` and `selected_snapshot_ids` is empty.<br>不存在第三阶段兼容准确时间段对比；`readiness_reasons` 包含 `insufficient_history`，`selected_snapshot_ids` 为空。 |
| `limited` | A comparison exists and its selected pair overlaps, has any missing metric, has a known zero previous count with known current count, or contains an offending older snapshot proven imported after newer evidence (either selected previous or current snapshot).<br>对比存在，且所选对重叠、有任一缺失指标、有已知零此前计数与已知当前计数，或包含已证明在较新证据之后导入的乱序旧快照（所选此前或当前快照均适用）。 |
| `ready` | A compatible exact-period comparison exists and none of those selected-pair caveats applies.<br>存在兼容准确时间段对比，且不适用上述所选对限制。 |

Unknown dates, missing metrics, and out-of-order offenders outside the selected pair remain visible observations without automatically lowering readiness. A selected snapshot used only as a newer-period witness does not trigger an out-of-order readiness reason. Same-period revision information alone does not lower readiness. Thus a `ready` response may still contain historical `warning` or `info` observations; `readiness_reasons` identifies precisely which codes affect the selected pair.
所选对之外的未知日期、缺失指标及乱序旧快照保留为可见观察，不自动降低就绪度。所选快照如果仅作为较新时间段证据，不触发乱序就绪度原因。仅有同时间段修订信息不会降低就绪度。因此 `ready` 响应仍可包含历史 `warning` 或 `info` 观察；`readiness_reasons` 准确标识影响所选对的代码。

`ready` means the stored dates and metric availability satisfy these checks. It does not certify source accuracy, matching GSC filters, complete exports, full 28-day coverage, statistical significance, or a page's SEO condition. Observed period bounds can be sparse and overlapping periods remain computable with a caveat.
`ready` 表示存储日期与指标可用性满足这些检查。不证明来源准确性、GSC 筛选一致、导出完整性、完整 28 天覆盖、统计显著性或页面 SEO 状况。已观察的时间段范围可能稀疏，重叠时间段仍可计算并附带限制提示。

## Import-level facts / 导入级事实

Import quality compares one run with stored runs sharing `source`, `source_type`, and `reporting_window`. It reports no readiness state or metric judgment. The same exact date bounds can belong to different GSC properties or filter scopes because ownership/filter provenance is not stored; these observations describe matching or overlapping dates across stored runs, not proven revisions of one site's complete report.
导入质量将一个导入与具有相同 `source`、`source_type` 及 `reporting_window` 的已存储导入比较。不报告就绪度状态或指标判断。由于未存储归属及筛选来源追踪，相同准确日期范围可能属于不同 GSC 属性或筛选范围；这些观察描述已存储导入之间匹配或重叠的日期，不证明同一站点完整报告的修订。

| Code / 代码 | Severity / 严重程度 | Target-run condition / 目标导入条件 |
| --- | --- | --- |
| `unknown_reporting_dates` | `warning` | The target run lacks exact period dates.<br>目标导入缺少准确时间段日期。 |
| `same_period_revisions` | `info` | Other files have the same exact date bounds within the source/type/window context.<br>在来源、类型、窗口上下文内，其他文件具有相同准确日期范围。 |
| `overlapping_reporting_periods` | `warning` | Other distinct known date ranges overlap inclusively. Matching same-period files are excluded from this overlap count.<br>其他不同的已知日期范围存在包含起止日的重叠。日期范围相同的文件从此重叠计数中排除。 |
| `out_of_order_import` | `warning` | The target has an older period end than another run imported strictly earlier.<br>目标时间段结束日期早于另一个严格更早导入的记录。 |

Import evidence includes the target record and relevant related run IDs, dates, source/window, and import timestamps. Related revision/overlap/chronology records must have hashes different from the target. Unknown target dates cannot establish revisions, overlap, or chronology. Identical-file retries create no extra run and therefore no new revision observation. A file's changed bytes can create a separate run under the Phase 3 contract.
导入证据包含目标记录及相关导入 ID、日期、来源与窗口及导入时间戳。相关修订、重叠及时间顺序记录的哈希必须与目标不同。未知目标日期不能确定修订、重叠或时间顺序。相同文件重试不创建额外导入，因此不产生新修订观察。文件字节变化可按第三阶段契约创建独立导入。

## API contracts and counts / API 契约与计数

```sh
curl 'http://localhost:8000/api/v1/pages/PAGE_UUID/quality'
curl 'http://localhost:8000/api/v1/imports/IMPORT_UUID/quality'
```

Use IDs from the existing page/import history APIs. A page response contains `page_id`, `readiness`, `observations`, `counts`, `comparison_exists`, `selected_snapshot_ids` (previous then current), and `readiness_reasons` (stable codes). The identical quality object is embedded as `quality` in `GET /api/v1/pages/{page_id}/performance`. Each request loads full page history once and calculates the existing comparison once; observations, counts, and readiness are independent of snapshot pagination.
使用现有页面与导入历史 API 的 ID。页面响应包含 `page_id`、`readiness`、`observations`、`counts`、`comparison_exists`、`selected_snapshot_ids`（此前在前、当前在后）及 `readiness_reasons`（稳定代码）。相同质量对象以 `quality` 内嵌在 `GET /api/v1/pages/{page_id}/performance` 中。每次请求仅加载一次完整页面历史并计算一次现有对比；观察、计数及就绪度独立于快照分页。

| Page count / 页面计数 | Meaning / 含义 |
| --- | --- |
| `total_snapshots` | All snapshots for this page.<br>本页面全部快照。 |
| `exact_date_snapshots` | Snapshots with both period endpoints.<br>具有两个时间段起止日期的快照。 |
| `unknown_date_snapshots` | Snapshots lacking exact endpoints.<br>缺少准确起止日期的快照。 |
| `snapshots_with_missing_metrics` | Snapshots with at least one missing metric, counted once each.<br>至少缺失一个指标的快照，各计一次。 |
| `distinct_exact_periods` | Distinct page/source/type/window/start/end groups.<br>不同的页面、来源、类型、窗口、起止日期组。 |
| `revision_periods` | Exact-period groups with more than one distinct import ID.<br>具有多个不同导入 ID 的准确时间段组。 |
| `compatible_exact_periods` | Largest number of distinct periods in a page/source/type/window/equal-duration group; not a count of compared pairs.<br>页面、来源、类型、窗口、相同时长组中最多的不同时间段数量；不是对比对数量。 |

An import response contains `import_run_id`, `observations`, and `counts`, without page readiness. Its matching context includes the target run. Counts are `total_imports`, `exact_date_imports`, `unknown_date_imports`, `same_period_revision_imports` (other files with target bounds), `overlapping_imports` (other distinct ranges), and `earlier_imported_newer_periods` (strictly earlier imports with later ends).
导入响应包含 `import_run_id`、`observations` 与 `counts`，不包含页面就绪度。其匹配上下文包含目标导入。计数为 `total_imports`、`exact_date_imports`、`unknown_date_imports`、`same_period_revision_imports`（具有目标日期范围的其他文件）、`overlapping_imports`（其他不同范围）及 `earlier_imported_newer_periods`（严格更早导入且结束日期更晚的记录）。

Invalid UUIDs return `422`; unknown page/import IDs return `404` with `page_not_found`/`import_not_found`; database failures return `503` with a useful public message and no stack trace. No quality mutation endpoint exists. The `/pages/[id]` development view shows readiness, severity, observations, and affected evidence in its data-quality section.
无效 UUID 返回 `422`；未知页面或导入 ID 返回 `404`，代码为 `page_not_found` 或 `import_not_found`；数据库失败返回 `503`，包含有用公开消息，不包含堆栈。没有质量修改接口。`/pages/[id]` 开发视图在数据质量部分显示就绪度、严重程度、观察及受影响证据。

## Unprovable conditions and limits / 无法证明的条件与限制

`current_state_not_single_snapshot` is deliberately not emitted. `WebsitePage` can carry forward nonblank metrics from earlier imports, but it has no per-metric source reference. Earlier imports may lack snapshots, and manual/direct SQL changes have no complete provenance. Value matching or replaying known history cannot reliably establish origin. The system documents this uncertainty rather than inventing a detection rule.
有意不生成 `current_state_not_single_snapshot`。`WebsitePage` 可沿用较早导入的非空白指标，但没有逐指标来源引用。较早导入可能没有快照，手动或直接 SQL 变化没有完整来源追踪。值匹配或重放已知历史无法可靠确定来源。系统记录该不确定性，不编造检测规则。

Observations cover only stored evidence, not unknown source rows, export coverage, authentication, property ownership, report filters, or unobserved changes. Quality uses full history in memory and may aggregate substantial evidence without paging individual observations; it is intended for development-scale data. Existing upload/resource limits remain unchanged. Observations are recomputed, without an audit log or persisted analysis version. Tests use synthetic fixtures; private exports remain outside Git.
观察仅覆盖已存储证据，不覆盖未知来源行、导出覆盖、身份认证、属性归属、报告筛选或未观察变化。质量在内存中使用完整历史，可能汇总大量证据，不单独分页观察；适用于开发规模数据。已有上传与资源限制保持不变。观察重新计算，没有审计日志或持久化分析版本。测试使用合成数据；私人导出保留在 Git 之外。

Phase 4 includes no SEO opportunity generation, scores, prioritization, actions, Decision Engine, AI, integrations, scheduling, autonomous execution, or production deployment. Phase 5 has not started.
第四阶段不包含 SEO 机会生成、评分、优先级、行动、决策引擎、AI、集成、调度、自主执行或生产部署。第五阶段尚未开始。
