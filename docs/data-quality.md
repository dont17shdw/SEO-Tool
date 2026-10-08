# Data quality and evidence readiness / 数据质量与证据就绪度

## Scope and boundary / 范围与边界

Phase 4 established factual evidence checks for descriptive GSC page-performance comparison: dates, history, missing metrics, overlap, repeated periods, import chronology, and zero percentage baselines. Phase 6 additionally checks explicit report scope and observed daily-date coverage. The result describes evidence readiness, without an SEO quality label, opportunity, priority, action, numeric score, or AI output.
第四阶段建立描述性 GSC 页面性能对比的事实证据检查：日期、历史、缺失指标、重叠、重复时间段、导入时间顺序及零百分比基准。第六阶段额外检查明确报告范围与已观察每日日期覆盖。结果描述证据就绪度，不包含 SEO 质量标签、机会、优先级、行动、数值评分或 AI 输出。

Phase 7 separately consumes this readiness result to gate runtime opportunity signals. Quality itself remains factual and unchanged: a signal detector requires `ready`, explicitly compatible scope, and complete selected coverage rather than adding another quality system. See [opportunity-engine.md](opportunity-engine.md).
第七阶段独立使用此就绪度结果，限制运行时机会信号。质量本身保持事实性且不改变：信号检测器要求 `ready`、明确兼容范围及完整所选覆盖，不添加另一质量系统。详见 [opportunity-engine.md](opportunity-engine.md)。

`analysis/performance_comparison.py` selects the pair using the Phase 3 date rules refined by Phase 6 scope compatibility, then calculates changes. `analysis/data_quality.py` consumes that result, rejected scope-conflict witnesses, full snapshot history, and joined import metadata to explain evidence limitations. It neither duplicates arithmetic nor changes the selected pair. The analysis functions are deterministic and have no database access, writes, external calls, or observation persistence.
`analysis/performance_comparison.py` 使用第六阶段范围兼容性细化后的第三阶段日期规则选择对比对，再计算变化。`analysis/data_quality.py` 使用该结果、被拒绝范围冲突证据、完整快照历史及连接的导入元数据，解释证据限制。它既不重复计算，也不改变所选对。分析函数具有确定性，不访问数据库、不写入、不调用外部服务，也不持久化观察。

Phase 4 quality needed no migration. Phase 5 added `0003_current_metric_provenance`; Phase 6 head `0004_report_scope` stores report-level scope/coverage evidence on `ImportRun` and preserves existing current-source links. Quality requests still read existing history without filling `NULL`, rewriting rows, or creating `SEOOpportunity` records. Current provenance remains a separate runtime result, not an input to comparison readiness.
第四阶段质量无需迁移。第五阶段增加 `0003_current_metric_provenance`；第六阶段最新修订 `0004_report_scope` 在 `ImportRun` 上存储报告级范围与覆盖证据，并保留已有当前来源关联。质量请求仍读取已有历史，不填补 `NULL`、不重写行，也不创建 `SEOOpportunity` 记录。当前来源仍为独立运行时结果，不是对比就绪度输入。

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

Page history is scoped by actual `page_id`. Revision and chronology groups use page, source, source type, reporting window, and canonical scope identity; revision groups also require both exact date bounds. Comparison additionally requires equal period lengths and excludes explicitly incompatible scope. Unknown scope is never labeled compatible. See [performance-history.md](performance-history.md) and [report-scope.md](report-scope.md).
页面历史按实际 `page_id` 限定。修订与时间顺序组使用页面、来源、来源类型、报告窗口及规范范围身份；修订组还要求两个准确日期边界。对比额外要求时间段长度相同，并排除明确不兼容范围。未知范围绝不标为兼容。详见 [performance-history.md](performance-history.md) 与 [report-scope.md](report-scope.md)。

| Code / 代码 | Severity / 严重程度 | Condition and evidence / 条件与证据 |
| --- | --- | --- |
| `insufficient_history` | `blocking` | Phase 3 supplied no compatible comparison. Evidence includes its unavailable reason and history counts; zero history, one observation, unknown dates, or only one compatible distinct period can cause this.<br>第三阶段未提供兼容对比。证据包含不可用原因与历史计数；零历史、一个观察、未知日期或只有一个兼容不同时间段均可能导致此情况。 |
| `unknown_report_scope` | `warning` | At least one snapshot's joined run lacks a known property, search type, or complete non-date filter ledger. Evidence lists resolved scope and origins, plus selected compatibility when available. It lowers readiness only when the selected pair has `scope_compatibility="unknown"`.<br>至少一个快照关联导入缺少已知属性、搜索类型或完整非日期筛选清单。证据列出解析范围与来源，并在可用时提供所选兼容性。仅所选对具有 `scope_compatibility="unknown"` 时降低就绪度。 |
| `incompatible_report_scope` | `warning` | Comparison selection rejected explicit scope conflicts. Evidence contains representative snapshot pairs and conflicting dimension names; it does not enumerate every possible conflicting pair. Rejected alternatives alone do not lower a valid selected pair's readiness.<br>对比选择拒绝明确范围冲突。证据包含代表性快照对及冲突维度名，不枚举全部可能冲突对。仅有被拒绝候选不会降低有效所选对的就绪度。 |
| `unknown_reporting_dates` | `warning` | At least one snapshot lacks date endpoints. Evidence lists affected snapshot/run IDs, source/window, dates, import times, and count.<br>至少一个快照缺少起止日期。证据列出受影响快照与导入 ID、来源与窗口、日期、导入时间及数量。 |
| `incomplete_date_coverage` | `warning` | At least one joined run has reliable but `partial` daily-date coverage. Evidence includes date count, consecutiveness, bounds, and run scope. It lowers readiness when either selected snapshot uses that run.<br>至少一个关联导入具有可靠但为 `partial` 的每日日期覆盖。证据包含日期数量、连续性、起止值及导入范围。任一所选快照使用该导入时，降低就绪度。 |
| `unknown_date_coverage` | `warning` | At least one joined run has `unknown` observed coverage, including legacy or CSV imports. Exact endpoints can coexist with unknown coverage. It lowers readiness when either selected snapshot uses that run.<br>至少一个关联导入的已观察覆盖为 `unknown`，包括旧导入或 CSV 导入。准确起止值可与未知覆盖并存。任一所选快照使用该导入时，降低就绪度。 |
| `overlapping_comparison_periods` | `warning` | The selected pair has inclusive overlap. Evidence names both periods and their overlap start/end; no other pair is substituted.<br>所选对存在包含起止日的重叠。证据标明两个时间段及重叠起止日期；不替换为其他对。 |
| `missing_metrics` | `warning` | At least one snapshot has `NULL` clicks, impressions, CTR, or average position. Evidence maps snapshot IDs to missing field names and counts snapshots, not missing cells.<br>至少一个快照的点击数、展示数、点击率或平均排名为 `NULL`。证据将快照 ID 映射到缺失字段名，统计快照数，不统计缺失单元格数。 |
| `zero_percentage_baseline` | `warning` | In the selected pair, previous clicks or impressions are known zero and the current count is known, including zero. Evidence identifies each metric and both values; percentage change remains `null`.<br>所选对的此前点击数或展示数为已知零，且当前计数已知，包括零。证据标识各指标与两个值；百分比变化保持 `null`。 |
| `same_period_revisions` | `info` | An exact-period and canonical-scope group has more than one distinct import ID for the page. Evidence lists each group, snapshot/run IDs, and scope compatibility. Selection retains the latest imported revision only; equal unknown scope identities remain visibly uncertain.<br>页面的准确时间段与规范范围组具有多个不同导入 ID。证据列出各组、快照与导入 ID 及范围兼容性。选择仅保留最近导入的修订；相等未知范围身份仍明确保持不确定。 |
| `out_of_order_import` | `warning` | A snapshot with an older `period_end` was imported strictly after a newer-ended snapshot in the same page/source/type/window/canonical-scope group. Evidence pairs each offending older snapshot with one earlier-imported newer-period witness and exposes their scope compatibility.<br>在同一页面、来源、类型、窗口与规范范围组内，具有较早 `period_end` 的快照严格晚于具有较新结束日期的快照导入。证据将每个乱序旧快照与一个较早导入的较新时间段证据配对，并公开范围兼容性。 |

Equal `imported_at` timestamps cannot prove out-of-order chronology. IDs may break display ties but do not create temporal evidence. Same-period revisions have matching ends and do not establish an older-period case. Unknown dates are excluded from overlap/revision/chronology checks requiring exact dates.
相同 `imported_at` 时间戳不能证明乱序时间顺序。ID 可处理显示并列，但不创建时间证据。同时间段修订的结束日期相同，不构成较早时间段情况。未知日期从需要准确日期的重叠、修订与时间顺序检查中排除。

## Exact page-readiness rules / 准确的页面就绪度规则

Readiness applies to the exact pair selected by the scope-aware comparison, not to every snapshot in history. It uses no numerical score or SEO threshold.
就绪度应用于考虑范围的对比选中的准确对，不应用于历史中的每个快照。不使用数值评分或 SEO 阈值。

| State / 状态 | Deterministic rule / 确定性规则 |
| --- | --- |
| `insufficient` | No eligible exact-period comparison exists; `readiness_reasons` contains `insufficient_history` and `selected_snapshot_ids` is empty. Explicitly incompatible reports never form a selected pair.<br>不存在合格准确时间段对比；`readiness_reasons` 包含 `insufficient_history`，`selected_snapshot_ids` 为空。明确不兼容报告绝不构成所选对。 |
| `limited` | A comparison exists and its scope compatibility is unknown, either selected run has partial/unknown observed coverage, or the pair overlaps, has a missing metric, has a known zero previous count with known current count, or contains an offending older snapshot proven imported after newer evidence.<br>对比存在，且范围兼容性未知、任一所选导入已观察覆盖为部分或未知，或所选对重叠、缺少指标、具有已知零此前计数与已知当前计数，或包含已证明在较新证据之后导入的乱序旧快照。 |
| `ready` | An eligible comparison has proven matching property/search/full-filter scope, both reports have complete observed 28-day coverage, and none of the previous selected-pair caveats applies.<br>合格对比具有已证明匹配的属性、搜索及完整筛选范围，两个报告均有完整已观察 28 天覆盖，且不适用此前所选对限制。 |

Historical unknown scope/dates/coverage, partial coverage, missing metrics, and out-of-order offenders outside the selected pair remain visible without automatically lowering readiness. A selected snapshot used only as a newer-period witness does not trigger an out-of-order readiness reason. Same-period revision information and rejected incompatible alternatives alone do not lower readiness. Thus a `ready` response may still contain historical `warning` or `info` observations; `readiness_reasons` identifies precisely which stable codes affect the selected pair.
所选对之外的历史未知范围、日期或覆盖、部分覆盖、缺失指标及乱序旧快照保持可见，不自动降低就绪度。所选快照如果仅作为较新时间段证据，不触发乱序就绪度原因。仅有同时间段修订信息与被拒绝的不兼容候选不会降低就绪度。因此 `ready` 响应仍可包含历史 `warning` 或 `info` 观察；`readiness_reasons` 准确标识影响所选对的稳定代码。

`ready` means stored scope evidence, observed dates, and metric availability satisfy these checks. Scope evidence may include user declarations; it does not authenticate GSC access or independently verify the declaration. Complete coverage proves 28 distinct consecutive observed dates, not completeness of every page row. Readiness certifies neither source accuracy, statistical significance, causation, nor a page's SEO condition. Sparse endpoints can remain descriptively comparable, with partial coverage and `limited` readiness.
`ready` 表示存储范围证据、已观察日期及指标可用性满足这些检查。范围证据可包含用户声明；不认证 GSC 访问，也不独立验证声明。完整覆盖证明 28 个不同连续的已观察日期，不证明每个页面行均完整。就绪度不证明来源准确性、统计显著性、因果关系或页面 SEO 状况。稀疏起止值仍可进行描述性对比，同时明确部分覆盖及 `limited` 就绪度。

## Import-level facts / 导入级事实

Import quality loads runs sharing `source`, `source_type`, and `reporting_window` for context and counts. Revision, overlap, and chronology checks narrow related runs to the target's canonical scope identity and different file hashes. Explicit scope conflicts in the broader context are reported separately. The response has no page-readiness state or metric judgment. Equal unknown canonical identities preserve legacy descriptive facts without proving property/filter equality.
导入质量读取具有相同 `source`、`source_type` 及 `reporting_window` 的导入，作为上下文与计数。修订、重叠及时间顺序检查将相关记录限定为目标规范范围身份相同且文件哈希不同的导入。更广上下文中的明确范围冲突单独报告。响应没有页面就绪度状态或指标判断。相等未知规范身份保留旧描述性事实，但不证明属性与筛选相同。

| Code / 代码 | Severity / 严重程度 | Target-run condition / 目标导入条件 |
| --- | --- | --- |
| `unknown_report_scope` | `warning` | The target lacks sufficient property/search/full-filter evidence.<br>目标缺少充分属性、搜索或完整筛选证据。 |
| `incompatible_report_scope` | `warning` | Other runs in the source/type/window context explicitly conflict with the target; evidence identifies dimensions and related runs.<br>来源、类型及窗口上下文中，其他导入与目标明确冲突；证据标识维度与相关导入。 |
| `incomplete_date_coverage` | `warning` | The target's reliable observed coverage is partial.<br>目标可靠已观察覆盖为部分。 |
| `unknown_date_coverage` | `warning` | The target has no reliable observed coverage.<br>目标没有可靠已观察覆盖。 |
| `unknown_reporting_dates` | `warning` | The target run lacks exact period dates.<br>目标导入缺少准确时间段日期。 |
| `same_period_revisions` | `info` | Other different-hash runs with the same canonical scope have the same exact date bounds.<br>其他不同哈希且规范范围相同的导入具有相同准确日期范围。 |
| `overlapping_reporting_periods` | `warning` | Other different-hash runs with the same canonical scope have distinct known ranges that overlap inclusively. Same-period revisions are excluded.<br>其他不同哈希且规范范围相同的导入具有不同已知日期范围，存在包含起止日的重叠。同时间段修订排除在外。 |
| `out_of_order_import` | `warning` | The target's end is older than another strictly earlier-imported, different-hash run in the same canonical scope.<br>目标结束日期早于同规范范围中另一个严格更早导入且哈希不同的记录。 |

Import evidence includes the target record and relevant run IDs, dates, source/window, import times, resolved scope, and coverage. Unknown target dates cannot establish revisions, overlap, or chronology. Same-file/same-scope retries create no extra run or revision. The same bytes under another scope can create a separate run and scope-conflict evidence, but do not count as a same-scope revision.
导入证据包含目标记录及相关导入 ID、日期、来源与窗口、导入时间、解析范围及覆盖。未知目标日期不能确定修订、重叠或时间顺序。同文件与同范围重试不创建额外导入或修订。相同字节配合另一范围可创建独立导入及范围冲突证据，但不计为同范围修订。

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
| `distinct_exact_periods` | Distinct page/source/type/window/canonical-scope/start/end groups.<br>不同的页面、来源、类型、窗口、规范范围及起止日期组。 |
| `revision_periods` | Exact-period/canonical-scope groups with more than one distinct import ID.<br>具有多个不同导入 ID 的准确时间段与规范范围组。 |
| `compatible_exact_periods` | Largest number of distinct periods in a page/source/type/window/canonical-scope/equal-duration group; not a pair count or proof that unknown scope is compatible.<br>页面、来源、类型、窗口、规范范围及相同时长组中最多的不同时间段数量；不是对比对数量，也不证明未知范围兼容。 |

An import response contains `import_run_id`, `observations`, and `counts`, without page readiness. Its matching context includes the target run. Counts are `total_imports`, `exact_date_imports`, `unknown_date_imports`, `same_period_revision_imports` (other files with target bounds), `overlapping_imports` (other distinct ranges), and `earlier_imported_newer_periods` (strictly earlier imports with later ends).
导入响应包含 `import_run_id`、`observations` 与 `counts`，不包含页面就绪度。其匹配上下文包含目标导入。计数为 `total_imports`、`exact_date_imports`、`unknown_date_imports`、`same_period_revision_imports`（具有目标日期范围的其他文件）、`overlapping_imports`（其他不同范围）及 `earlier_imported_newer_periods`（严格更早导入且结束日期更晚的记录）。

Invalid UUIDs return `422`; unknown page/import IDs return `404` with `page_not_found`/`import_not_found`; database failures return `503` with a useful public message and no stack trace. No quality mutation endpoint exists. The `/pages/[id]` development view shows readiness, severity, observations, and affected evidence in its data-quality section.
无效 UUID 返回 `422`；未知页面或导入 ID 返回 `404`，代码为 `page_not_found` 或 `import_not_found`；数据库失败返回 `503`，包含有用公开消息，不包含堆栈。没有质量修改接口。`/pages/[id]` 开发视图在数据质量部分显示就绪度、严重程度、观察及受影响证据。

## Unprovable conditions and limits / 无法证明的条件与限制

Phase 4 could not prove `current_state_not_single_snapshot` without per-field source links. Phase 5 now records links during new imports and emits that `info` observation in the separate `provenance` result only for multiple validated known snapshot IDs. `unknown_current_metric_provenance` describes non-`NULL` current values without valid recorded origins; it does not imply a mixed state. Neither observation changes historical quality or readiness. See [current-provenance.md](current-provenance.md).
第四阶段在缺少逐字段来源关联时，无法证明 `current_state_not_single_snapshot`。第五阶段现在于新导入时记录关联，仅在多个已验证已知快照 ID 时，在独立 `provenance` 结果中生成该 `info` 观察。`unknown_current_metric_provenance` 描述没有有效已记录来源的非 `NULL` 当前值；它不表示混合状态。两个观察都不改变历史质量或就绪度。详见 [current-provenance.md](current-provenance.md)。

Earlier imports may lack snapshots or provenance. Matching values and replaying history cannot establish missing sources. Direct SQL can bypass the controlled writer, and equal-value manual edits can remain undetectable. Legacy provenance remains unknown without backfill.
较早导入可能缺少快照或来源。值匹配及重放历史不能建立缺失来源。直接 SQL 可绕过受控写入器，相同值手动编辑可能仍无法检测。旧来源保持未知，不回填。

Phase 6 reports only supported workbook evidence and explicit user declarations. Missing property/filter evidence and legacy observed coverage stay unknown; migration never reconstructs daily dates from endpoints. Formula scope cells produce `formula_scope_metadata` uncertainty, and workbook filter rows alone never prove a complete ledger. No authenticated ownership, complete page-table export, source accuracy, or unobserved change is certified. Quality uses full history in memory and may aggregate substantial evidence without paging observations; it is intended for development-scale data. Existing upload/resource limits remain unchanged. Observations are recomputed without an audit log or persisted analysis version. Synthetic fixtures cover scope, coverage, legacy readiness, and read-only behavior; private exports remain outside Git.
第六阶段仅报告受支持工作簿证据与明确用户声明。缺失属性或筛选证据及旧已观察覆盖保持未知；迁移绝不从起止值重建每日日期。范围公式单元格产生 `formula_scope_metadata` 不确定性，单凭工作簿筛选行绝不证明完整清单。不证明已认证归属、完整页面表导出、来源准确性或未观察变化。质量在内存中使用完整历史，可能汇总大量证据，不单独分页观察；适用于开发规模数据。已有上传与资源限制保持不变。观察重新计算，没有审计日志或持久化分析版本。合成数据覆盖范围、覆盖、旧就绪度与只读行为；私人导出保留在 Git 之外。

Phase 6 included no SEO opportunity generation. Phase 7 now evaluates four separate runtime signals from the existing selected `ready` comparison; unrelated historical warnings and current-provenance observations do not automatically block those signals. Quality/provenance semantics remain unchanged, and no `SEOOpportunity` rows are created. Scores, prioritization, actions, Decision Engine, AI, integrations, scheduling, autonomous execution, and production deployment remain unimplemented.
第六阶段不包含 SEO 机会生成。第七阶段现在从已有所选 `ready` 对比评估四种独立运行时信号；无关历史警告及当前来源观察不自动阻止这些信号。质量与来源语义保持不变，不创建 `SEOOpportunity` 行。评分、优先级、行动、决策引擎、AI、集成、调度、自主执行及生产部署仍未实现。
