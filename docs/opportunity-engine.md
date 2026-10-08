# Opportunity Engine / 机会引擎

## Purpose and boundary / 目的与边界

Phase 7 detects four factual SEO signals from an existing selected historical comparison: `traffic_decline`, `ctr_opportunity`, `ranking_decline`, and `impression_growth_gap`. A candidate states which observed change met a transparent heuristic rule and retains its source records and thresholds. It does not explain the cause of that change or decide what should happen next.
第七阶段根据已有所选历史对比检测四种事实 SEO 信号：`traffic_decline`、`ctr_opportunity`、`ranking_decline` 及 `impression_growth_gap`。候选说明哪项已观察变化满足透明启发式规则，并保留来源记录及阈值。不解释变化原因，也不决定下一步应该采取什么行动。

Keep the stages distinct: data quality asks whether evidence supports comparison; opportunity detection identifies a factual signal; prioritization assigns attention to that signal; decisions define an action. Phase 8 implements prioritization in a [separate module and endpoint](opportunity-prioritization.md), without changing this detection contract. There are no scores, priorities, severity rankings, business-value weights, confidence scores, recommended actions, AI calls, or external integrations in the detection engine itself.
各阶段保持独立：数据质量判断证据能否支持对比；机会检测识别事实信号；优先级为该信号分配关注程度；决策定义行动。第八阶段在[独立模块及接口](opportunity-prioritization.md) 中实现优先级，不改变此检测契约。检测引擎本身没有评分、优先级、严重程度排序、业务价值权重、置信度评分、建议行动、AI 调用或外部集成。

`backend/app/analysis/opportunity_engine.py` contains frozen database-independent dataclasses and deterministic rule logic. It consumes `compare_performance(...)` and `analyse_page_quality(...)` results, including Phase 6 scope and coverage evidence. It does not read the database, select another comparison, rebuild data quality, fill missing values, or write any record.
`backend/app/analysis/opportunity_engine.py` 包含不可变且独立于数据库的数据类与确定性规则逻辑。它使用 `compare_performance(...)` 与 `analyse_page_quality(...)` 结果，包括第六阶段范围及覆盖证据。不读取数据库、不另选对比、不重建数据质量、不填补缺失值，也不写入任何记录。

## Mandatory evidence gate / 必须满足的证据门槛

Candidate evaluation requires all of these selected-comparison facts:
候选评估要求所选对比同时满足以下事实：

1. The existing Phase 3/6 comparison selected a previous and current snapshot for the page.
   已有第三、六阶段对比为该页面选中此前及当前快照。
2. Existing Phase 4/6 page readiness is exactly `ready`, with no selected-pair readiness reasons.
   已有第四、六阶段页面就绪度必须恰好为 `ready`，没有所选对就绪度限制原因。
3. Scope compatibility is explicitly `compatible`, with matching known property, search type, and complete filter ledger.
   范围兼容性明确为 `compatible`，具有匹配的已知属性、搜索类型及完整筛选清单。
4. Both reports have `complete` observed coverage: 28 distinct consecutive dates spanning exactly 28 calendar days.
   两个报告均有 `complete` 已观察覆盖：28 个不同连续日期，恰好跨越 28 个日历天。
5. The selected periods do not overlap. Required rule metrics are non-`NULL`, and every percentage used by that rule has a positive previous count baseline.
   所选时间段不重叠。该规则要求的指标均非 `NULL`，且每个被规则使用的百分比均具有正数此前计数基准。

The engine consumes existing `readiness_reasons` and associated quality observations; its scope/coverage/overlap guards check those same selected facts without introducing another quality taxonomy. A `limited` or `insufficient` response always produces `eligible=false` and `candidates=[]`. Unknown scope, sparse or unknown coverage, overlapping periods, missing selected metrics, zero percentage baselines, and relevant out-of-order imports cannot produce candidates through this gate.
引擎使用已有 `readiness_reasons` 及关联质量观察；范围、覆盖与重叠保护检查相同所选事实，不增加另一质量分类。`limited` 或 `insufficient` 响应始终返回 `eligible=false` 与 `candidates=[]`。未知范围、稀疏或未知覆盖、重叠时间段、缺失所选指标、零百分比基准及相关乱序导入不能通过此门槛生成候选。

Readiness remains scoped to the selected pair. A `ready` page may contain unrelated historical `warning` or `info` observations, including rejected incompatible alternatives or revisions. Those observations do not veto candidates. The gate uses selected readiness reasons, not a blanket ban on historical warnings. Each rule also checks its own required metrics and valid baselines defensively.
就绪度仍限定于所选对。`ready` 页面可包含无关历史 `warning` 或 `info` 观察，包括被拒绝的不兼容候选或修订。这些观察不否定候选。门槛使用所选就绪度原因，不全面禁止历史警告。每条规则还防御性检查其自身所需指标及有效基准。

Eligibility and a signal are separate outcomes. A valid ready comparison with no met threshold returns `eligible=true` and `candidates=[]`; no candidate is manufactured. An ineligible page remains a successfully imported page, without an SEO failure label.
资格与信号是不同结果。有效就绪对比未满足任何阈值时，返回 `eligible=true` 与 `candidates=[]`，不编造候选。不合格页面仍为成功导入页面，不被标为 SEO 失败。

## Exact centralized v1 rules / 准确的集中 V1 规则

`OpportunityRuleConfig` is a frozen dataclass and `DEFAULT_RULE_CONFIG` holds all defaults in one place. These are transparent Phase 7 heuristics, not universal SEO truths. They require future calibration against authorized site evidence. API callers cannot supply thresholds; each emitted candidate exposes the thresholds actually used.
`OpportunityRuleConfig` 为不可变数据类，`DEFAULT_RULE_CONFIG` 在一个位置保存全部默认值。这些是透明的第七阶段启发式规则，不是通用 SEO 真理。未来需要根据已授权站点证据校准。API 调用者不能提供阈值；每个生成候选公开实际使用的阈值。

Every change is current minus previous. Counts use absolute and percentage change. CTR is stored as a fraction; its change is expressed in percentage points (`pp`), not relative percent. A larger average-position number means worse ranking. Except for the explicit strict predicates shown below, boundaries are inclusive.
每项变化均为当前值减此前值。计数使用绝对变化及百分比变化。CTR 以比例存储，其变化表示为百分点（`pp`），不是相对百分比。平均排名数值越大表示排名越差。除下列明确的严格谓词外，边界均包含等号。

| Type / 类型 | All required predicates / 必须同时满足的谓词 |
| --- | --- |
| `traffic_decline` / 流量下降 | Previous clicks `>= 5`; absolute click change `<= -3`; click percentage change `<= -20%`.<br>此前点击数 `>= 5`；点击绝对变化 `<= -3`；点击百分比变化 `<= -20%`。 |
| `ctr_opportunity` / CTR 机会 | Previous and current impressions each `>= 50`; CTR change `<= -0.5 pp`; average-position change `<= +0.5`; impression percentage change `>= -10%`.<br>此前与当前展示数均 `>= 50`；CTR 变化 `<= -0.5` 个百分点；平均排名变化 `<= +0.5`；展示百分比变化 `>= -10%`。 |
| `ranking_decline` / 排名下降 | Previous and current impressions each `>= 50`; average-position change `>= +2.0`; current impressions `> 0` explicitly.<br>此前与当前展示数均 `>= 50`；平均排名变化 `>= +2.0`；明确要求当前展示数 `> 0`。 |
| `impression_growth_gap` / 展示增长缺口 | Previous and current impressions each `>= 50`; impression percentage change `>= +25%`; click percentage change **`< +10%`**; CTR change `<= -0.3 pp`.<br>此前与当前展示数均 `>= 50`；展示百分比变化 `>= +25%`；点击百分比变化严格 **`< +10%`**；CTR 变化 `<= -0.3` 个百分点。 |

`current impressions > 0` is retained explicitly in the ranking configuration even though the default minimum of 50 already satisfies it. Exactly +10% click growth does not meet the growth-gap rule; a click decline or smaller positive growth can meet it. No rule identifies a generic low CTR against an expected SERP curve.
虽然默认最低展示数 50 已满足要求，排名配置仍明确保留 `当前展示数 > 0`。恰好 +10% 的点击增长不满足增长缺口规则；点击下降或更小正增长可满足。不根据预期搜索结果 CTR 曲线识别一般性的低 CTR。

### Exact percentage boundaries / 精确百分比边界

Phase 3's percentage evidence remains rounded to six decimal places for descriptive presentation. Rule percentage predicates use integer cross multiplication on the existing absolute count change and previous count, plus the Decimal threshold's exact integer ratio. They do not compare a rounded displayed percentage to a threshold and do not change comparison arithmetic or presentation.
第三阶段百分比证据仍舍入为六位小数，用于描述性展示。规则百分比谓词使用已有计数绝对变化、此前计数及 Decimal 阈值的精确整数比，执行整数交叉相乘。不将已舍入展示百分比与阈值比较，也不改变对比计算或展示。

For a positive baseline `previous` and threshold `t = numerator / denominator`, compare `absolute_change * 100 * denominator` with `previous * numerator`, using the rule's `<=`, `>=`, or `<`. Integer arithmetic preserves a strict boundary even for large counts and is independent of the caller's Decimal precision context. A true value just under +25% does not trigger merely because six-decimal display rounds to +25%; a true value just under +10% still passes the strict click predicate even if display rounds to +10%.
当正数基准为 `previous`，阈值为 `t = numerator / denominator` 时，使用规则要求的 `<=`、`>=` 或 `<`，比较 `absolute_change * 100 * denominator` 与 `previous * numerator`。整数运算即使对于大计数也保留严格边界，并独立于调用方 Decimal 精度上下文。真实值略低于 +25% 不会因六位小数展示舍入至 +25% 而触发；真实值略低于 +10%，即使展示舍入至 +10%，仍通过严格点击谓词。

CTR and position predicates consume the existing exact Decimal changes of the normalized stored values: CTR has six fractional places and average position has four. Exactly -0.5 pp or -0.3 pp is included, exactly +0.5 position change is included for the CTR rule, and exactly +2.0 triggers ranking decline. A +1.9999 position change does not trigger ranking decline.
CTR 与排名谓词使用已有标准化存储值的精确 Decimal 变化：CTR 具有六位比例小数，平均排名具有四位小数。恰好 -0.5 或 -0.3 个百分点包含在内；CTR 规则包含恰好 +0.5 的排名变化；恰好 +2.0 触发排名下降。+1.9999 的排名变化不触发排名下降。

### Interpretation and examples / 解释与示例

These synthetic examples assume the mandatory evidence gate passes. Other rules may also fire if their own thresholds are met.
以下合成示例假设必须满足的证据门槛已通过。如果其他规则也满足自身阈值，还可同时触发。

| Signal / 信号 | Previous → current / 此前 → 当前 | Factual result / 事实结果 |
| --- | --- | --- |
| `traffic_decline` | Clicks `20 → 12`.<br>点击数 `20 → 12`。 | Absolute `-8`, percentage `-40%`; candidate. `2 → 1` produces none because previous volume is below 5.<br>绝对变化 `-8`，百分比 `-40%`；生成候选。`2 → 1` 因此前数量低于 5，不生成候选。 |
| `ctr_opportunity` | Impressions `1000 → 1000`, CTR `5% → 4%`, position `4 → 4.5`.<br>展示数 `1000 → 1000`，CTR `5% → 4%`，排名 `4 → 4.5`。 | CTR `-1 pp`, position `+0.5`, impressions `0%`; candidate. A position change of `+0.5001` fails this rule.<br>CTR `-1` 个百分点，排名 `+0.5`，展示数 `0%`；生成候选。排名变化 `+0.5001` 不满足此规则。 |
| `ranking_decline` | Impressions `100 → 100`, position `4 → 7`.<br>展示数 `100 → 100`，排名 `4 → 7`。 | Position `+3` is worsening; candidate. `8 → 5` is improvement and produces none.<br>排名 `+3` 表示变差；生成候选。`8 → 5` 表示改善，不生成候选。 |
| `impression_growth_gap` | Impressions `1000 → 1250`, clicks `100 → 105`, CTR `10% → 8.4%`.<br>展示数 `1000 → 1250`，点击数 `100 → 105`，CTR `10% → 8.4%`。 | Impressions `+25%`, clicks `+5%`, CTR `-1.6 pp`; candidate. Exactly `+10%` clicks fails.<br>展示数 `+25%`，点击数 `+5%`，CTR `-1.6` 个百分点；生成候选。恰好 `+10%` 的点击数不满足。 |

The CTR rule describes deterioration in click-through efficiency while visibility remains broadly comparable. It does not prove a bad title/meta description or recommend editing either. The growth-gap rule describes visibility growing faster than clicks, without choosing a remedy. Traffic and ranking rules describe changes without inferring their causes.
CTR 规则描述在可见性大致可比时点击效率恶化。不证明标题或元描述不好，也不建议编辑。增长缺口规则描述可见性增长快于点击数，不选择解决方案。流量及排名规则描述变化，不推断原因。

A page can legitimately emit several types: for example, falling clicks and worsening average position can generate both `traffic_decline` and `ranking_decline`. No rule suppresses another. Each type appears at most once for page + selected previous/current snapshots within one runtime analysis. Phase 8 evaluates every retained candidate independently in its separate prioritization stage, without a combined impact score.
页面可合理生成多个类型：例如点击数下降及平均排名变差可同时生成 `traffic_decline` 与 `ranking_decline`。规则互不压制。在一次运行时分析中，每个页面及所选此前、当前快照对的每种类型最多出现一次。第八阶段在独立优先级阶段中分别评估每个保留候选，不使用综合影响评分。

## Candidate and page-response contract / 候选与页面响应契约

| Field / 字段 | Meaning / 含义 |
| --- | --- |
| `opportunity_type` | One of the four stable codes above.<br>上述四种稳定代码之一。 |
| `page_id`, `site_id`, `url` | Actual page identity; site is nullable, without inferred ownership.<br>实际页面身份；站点可空，不推断归属。 |
| `previous_snapshot_id`, `current_snapshot_id` | Exactly the existing selected comparison sources.<br>恰好为已有所选对比来源。 |
| `previous_period_start`, `previous_period_end`, `current_period_start`, `current_period_end` | Exact ISO reporting dates for both selected periods.<br>两个所选时间段的准确 ISO 报告日期。 |
| `evidence_readiness`, `scope_compatibility` | Always `ready` and `compatible` on an emitted candidate.<br>已生成候选始终为 `ready` 与 `compatible`。 |
| `reason_code`, `message` | Stable factual rule code and English-first Chinese-second summary.<br>稳定事实规则代码及英文在前、中文在后的摘要。 |
| `evidence` | Relevant `previous`, `current`, `changes`, and `thresholds` dictionaries.<br>相关 `previous`、`current`、`changes` 及 `thresholds` 字典。 |

Factual reason codes are `clicks_decline_threshold_met`, `ctr_declined_with_comparable_visibility`, `average_position_worsening_threshold_met`, and `impressions_grew_faster_than_clicks`, respectively. Integer counts remain integers; Decimal evidence and thresholds follow the API's existing Decimal serialization. Raw CTR evidence remains a fraction, with changes explicitly named `ctr_percentage_point_change`.
对应事实原因代码分别为 `clicks_decline_threshold_met`、`ctr_declined_with_comparable_visibility`、`average_position_worsening_threshold_met` 及 `impressions_grew_faster_than_clicks`。整数计数保持整数；Decimal 证据与阈值沿用 API 既有 Decimal 序列化。原始 CTR 证据保持比例，变化明确命名为 `ctr_percentage_point_change`。

A traffic candidate's evidence has `previous.clicks`, `current.clicks`, `changes.clicks_absolute_change`, `changes.clicks_percentage_change`, and thresholds `minimum_previous_clicks`, `maximum_clicks_absolute_change`, and `maximum_clicks_percentage_change`. Other rules return their relevant impression/CTR/position inputs and named changes/thresholds only. There is no candidate `id`, status, score, priority, action, expected impact, effort, risk, or AI confidence.
流量候选证据包含 `previous.clicks`、`current.clicks`、`changes.clicks_absolute_change`、`changes.clicks_percentage_change`，以及阈值 `minimum_previous_clicks`、`maximum_clicks_absolute_change` 与 `maximum_clicks_percentage_change`。其他规则仅返回相关展示、CTR 与排名输入，以及命名变化与阈值。没有候选 `id`、状态、评分、优先级、行动、预期影响、工作量、风险或 AI 置信度。

The page analysis contains `page_id`, nullable `site_id`, `url`, `eligible`, `evidence_readiness`, `gate_reasons`, `gate_observations`, `comparison`, and `candidates`. `comparison` is the existing full comparison or `null`, not a newly selected pair. `gate_reasons` uses existing stable quality codes; `gate_observations` reuses the matching structured observations. A ready response has no gate reasons, regardless of unrelated history warnings.
页面分析包含 `page_id`、可空 `site_id`、`url`、`eligible`、`evidence_readiness`、`gate_reasons`、`gate_observations`、`comparison` 及 `candidates`。`comparison` 为已有完整对比或 `null`，不是新选择的对。`gate_reasons` 使用已有稳定质量代码；`gate_observations` 复用匹配结构化观察。就绪响应没有门槛原因，不受无关历史警告影响。

## Read-only API and frontend / 只读 API 与前端

| Endpoint / 接口 | Contract / 契约 |
| --- | --- |
| `GET /api/v1/pages/{page_id}/opportunities` | Returns the page analysis above; an unavailable gate is a normal `200` with no candidates.<br>返回上述页面分析；不可用门槛是正常 `200`，没有候选。 |
| `GET /api/v1/pages/{page_id}/performance` | Embeds the same analysis as `opportunities`, alongside unchanged quality/provenance/comparison semantics.<br>将相同分析内嵌为 `opportunities`，并保留质量、来源与对比语义。 |
| `GET /api/v1/opportunities` | Returns `items`, `page`, `page_size`, `total`, and `total_pages` for actual candidates.<br>返回实际候选的 `items`、`page`、`page_size`、`total` 及 `total_pages`。 |

The listing accepts `page >= 1` (default 1), `page_size` from 1 to 100 (default 50), and optional UUID `site_id`. Site filtering uses recorded `WebsitePage.site_id`; it does not infer ownership from URL. A valid nonexistent site ID returns an empty list. Invalid parameters return `422`, unknown pages return `404` with `page_not_found`, and database failures return a public `503` without internal traces.
列表接受 `page >= 1`（默认 1）、1 至 100 的 `page_size`（默认 50），以及可选 UUID `site_id`。站点筛选使用已记录 `WebsitePage.site_id`，不从 URL 推断归属。有效但不存在站点 ID 返回空列表。无效参数返回 `422`；未知页面返回 `404`，代码为 `page_not_found`；数据库失败返回公开 `503`，不泄露内部堆栈。

```sh
curl 'http://localhost:8000/api/v1/opportunities?page=1&page_size=50'
curl http://localhost:8000/api/v1/pages/PAGE_UUID/opportunities
```

The original neutral `/opportunities` view shows bilingual signal labels, page URLs, selected periods, and factual evidence without priority metadata. Phase 8 adds a clearly separate prioritized workspace view. `/pages/[id]` retains factual page signals or existing evidence-gate reasons and reuses the performance response rather than fetching another opportunity/provenance view independently. Neither view adds scores, recommended actions, or execution buttons.
原 `/opportunities` 中立视图显示双语信号标签、页面 URL、所选时间段及事实证据，不包含优先级元数据。第八阶段增加明确独立的优先级工作区视图。`/pages/[id]` 保留事实页面信号或已有证据门槛原因，复用性能响应，不另行获取独立机会或来源视图。两个视图均不增加评分、建议行动或执行按钮。

## Candidate pagination and scale / 候选分页与规模

The global loader performs two grouped SELECTs: relevant pages and joined snapshot/run history. It computes the existing comparison and quality once per page, evaluates candidates, sorts them by exact URL, opportunity type, and page ID, then slices actual candidates and counts them. It never paginates raw page rows before detection. A page without candidates consumes no result slot; a page with several types consumes one slot per candidate.
全局读取流程执行两个分组 SELECT：相关页面及连接的快照与导入历史。每个页面计算一次已有对比及质量，评估候选，按精确 URL、机会类型与页面 ID 排序，然后截取实际候选并计数。绝不在检测之前对原始页面行分页。没有候选的页面不占结果位置；具有多种类型的页面每个候选占一个位置。

Ordering is deterministic and neutral, not by decline size, estimated impact, severity, business value, or score. Dedicated page opportunity analysis needs two SELECTs; performance retains its three including provenance. No per-candidate database round trips, candidate cache, or background recomputation job is added.
排序具有确定性与中立性，不按下降大小、预期影响、严重程度、业务价值或评分。独立页面机会分析需要两个 SELECT；性能接口仍保留包含来源在内的三个。不增加按候选数据库往返、候选缓存或后台重新计算任务。

Response pagination is bounded, but analysis is still development-scale: all relevant pages and full histories, quality evidence, and generated candidates are held in memory before slicing. Very large collections or many distinct scope streams need a separately designed scale strategy. Separate requests do not freeze concurrent imports; candidate totals and selected evidence may change between pages.
响应分页有界，但分析仍适用于开发规模：相关全部页面、完整历史、质量证据及已生成候选在截取前均保存在内存中。非常大的集合或大量不同范围流需要另行设计规模方案。独立请求不会冻结并发导入；候选总数及所选证据可能在分页间变化。

## Relationship to history, provenance, and storage / 与历史、来源及存储的关系

Phase 3/6 continues to select reporting-date-based comparisons, including scope-aware revision grouping. Phase 4/6 continues to determine readiness. Phase 7 does not replace a limited latest selected pair with an older ready pair to manufacture signals. Snapshot display pagination cannot alter comparison, readiness, or candidate selection.
第三、六阶段继续按报告日期选择对比，包括考虑范围的修订分组。第四、六阶段继续确定就绪度。第七阶段不会为了制造信号，将受限的最新所选对替换为较旧就绪对。快照展示分页不能改变对比、就绪度或候选选择。

Phase 5 current provenance remains independent. Blank carry-forward, measured zeros, same-value source refresh, duplicate retry, out-of-order applies, unknown legacy sources, and mixed current-state observations retain their meanings. Current values may combine several snapshots or reflect an older applied period. Opportunity metrics come only from the selected historical snapshots; neither mixed nor unknown current provenance alone blocks a ready historical signal.
第五阶段当前来源保持独立。空白沿用、测得零、相同值来源刷新、重复重试、乱序应用、未知旧来源及混合当前状态观察均保留原意。当前值可组合多个快照或反映较早已应用时间段。机会指标仅来自所选历史快照；仅有混合或未知当前来源不会阻止就绪历史信号。

The existing `SEOOpportunity` ORM model/table remains reserved and untouched; it is not the runtime candidate source of truth. Phase 7 adds no migration, and Alembic head remains `0004_report_scope`. GET operations never insert, update, or delete `SEOOpportunity` rows or any source/history/provenance rows.
已有 `SEOOpportunity` ORM 模型与表保持预留且不修改；不是运行时候选的唯一事实来源。第七阶段不增加迁移，Alembic 最新修订仍为 `0004_report_scope`。GET 操作绝不插入、更新或删除 `SEOOpportunity` 行或任何来源、历史及来源关联行。

Runtime-only candidates avoid committing unstable heuristic outputs to a lifecycle before thresholds are validated. There is no stale candidate regeneration, persisted deduplication/status transition, frozen result, or persisted analysis-version history. Thresholds are exposed for the current output, but code/config changes can change future outputs. A later phase must explicitly decide whether persistence is useful and define its versioning/lifecycle first.
仅运行时候选可避免在阈值验证之前，将不稳定启发式输出提交至生命周期。没有过期候选重新生成、持久化去重或状态变化、冻结结果，也没有持久化分析版本历史。当前输出公开阈值，但代码与配置变化可改变后续输出。后续阶段必须明确决定持久化是否有用，并先定义其版本与生命周期。

## Verification and limitations / 验证与限制

Synthetic gate and exact-boundary tests cover low volumes, zero baselines, Decimal precision contexts, rounded-display boundary cases, multiple signals, eligible no-op results, candidate pagination, site filtering, and neutral ordering. PostgreSQL/API tests cover read-only behavior, preservation of existing `SEOOpportunity` records, and generic database failure handling. Existing Phase 3–6 regression checks remain part of the backend suite. Private workbooks stay outside Git; no AI or external calls are needed for detection.
合成门槛与精确边界测试覆盖低数量、零基准、Decimal 精度上下文、展示舍入边界情况、多信号、合格无操作结果、候选分页、站点筛选及中立排序。PostgreSQL 与 API 测试覆盖只读行为、已有 `SEOOpportunity` 记录保留及通用数据库失败处理。已有第三至六阶段回归检查继续包含在后端测试集中。私人工作簿保留在 Git 之外；检测不需要 AI 或外部调用。

Ready evidence and met thresholds do not certify source accuracy, authenticated property ownership, complete page exports, statistical significance, causation, expected impact, or appropriate action. Aggregate page metrics do not provide query-level intent, expected CTR curves, SERP context, competitor behavior, seasonality controls, or enough evidence to diagnose a title/meta issue. Unsupported or legacy unknown scope/coverage stays unknown; it is not backfilled to unlock candidates. Direct SQL may bypass controlled writers, and this is not a tamper-proof audit system.
就绪证据及满足阈值不证明来源准确性、已认证属性归属、完整页面导出、统计显著性、因果关系、预期影响或合适行动。汇总页面指标不提供查询级意图、预期 CTR 曲线、搜索结果背景、竞争对手行为、季节性控制，或足以诊断标题、元描述问题的证据。不支持或旧未知范围与覆盖保持未知，不回填以解锁候选。直接 SQL 可绕过受控写入器；本系统不是防篡改审计系统。

## Relationship to Phase 8 / 与第八阶段的关系

Phase 8 adds narrowly validated custom 28-day XLSX windows and transparent `priority-v1` attention tiers to these same runtime candidates. It preserves every detection threshold, gate, original evidence field, neutral ordering, and read-only storage boundary. No persistence or migration is added. **Real-site calibration has not yet been performed.** See [opportunity-prioritization.md](opportunity-prioritization.md) for exact tier rules, API contracts, limitations, and the private TuffPlus acceptance procedure. The next milestone is MVP real-data acceptance and deployment, reviewed separately; recommendations, Decision Engine logic, AI, integrations, and execution remain unimplemented.
第八阶段为这些相同运行时候选增加严格校验的自定义 28 天 XLSX 窗口及透明 `priority-v1` 关注层级。保留全部检测阈值、门槛、原证据字段、中立排序及只读存储边界。不增加持久化或迁移。**尚未进行真实站点校准。** 准确层级规则、API 契约、限制及私下 TuffPlus 验收流程详见 [opportunity-prioritization.md](opportunity-prioritization.md)。下一里程碑为另行评审的 MVP 真实数据验收与部署；建议、决策引擎逻辑、AI、集成及执行仍未实现。
