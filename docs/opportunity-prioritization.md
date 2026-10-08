# Opportunity prioritization / 机会优先级

## Purpose and dependency boundary / 目的与依赖边界

Phase 8 assigns transparent attention tiers to existing Phase 7 runtime candidates. The flow is **GSC evidence → Comparison → Readiness → Opportunity detection → Prioritization**. `backend/app/analysis/opportunity_prioritization.py` is a separate deterministic module with no database, network, AI, or persistence dependency. It cannot create candidates, change page eligibility, select another comparison, fill missing evidence, or alter Phase 7 detection thresholds.
第八阶段为已有第七阶段运行时候选分配透明关注层级。流程为 **GSC evidence → Comparison → Readiness → Opportunity detection → Prioritization**。`backend/app/analysis/opportunity_prioritization.py` 为独立确定性模块，不依赖数据库、网络、AI 或持久化。不能创建候选、改变页面资格、另选对比、补充缺失证据，或修改第七阶段检测阈值。

The tiers are `high`, `medium`, and `low`. Priority means which detected signal deserves attention under the documented heuristics. It does not assess business value, statistical confidence, causation, revenue, predicted traffic recovery, conversion value, effort, or the right action. There is no numeric score, recommendation, diagnosis, execution control, or severity assessment.
层级为 `high`、`medium` 与 `low`。优先级表示根据已记录启发式规则，哪项已检测信号值得关注。不评估业务价值、统计置信度、因果关系、收入、预计流量恢复、转化价值、工作量或正确行动。没有数值评分、建议、诊断、执行控制或严重程度评估。

The mandatory upstream gate is unchanged: selected historical evidence must be `ready`, have explicitly compatible complete property/search/filter scope, and include two complete observed 28-day periods without overlap. Existing missing-metric, zero-baseline, and relevant out-of-order checks still apply. Current applied metrics and their provenance never substitute for the historical snapshots. See [opportunity-engine.md](opportunity-engine.md) and [data-quality.md](data-quality.md).
上游必须满足的门槛保持不变：所选历史证据必须为 `ready`，具有明确兼容且完整的属性、搜索及筛选范围，并包含两个互不重叠且已观察覆盖完整的 28 天时间段。已有缺失指标、零基准及相关乱序检查继续适用。当前应用指标及其来源绝不替代历史快照。详见 [opportunity-engine.md](opportunity-engine.md) 与 [data-quality.md](data-quality.md)。

Every independent detected candidate is retained. A page can have traffic and ranking decline together, or other combinations. Each is evaluated separately; no candidate suppresses another, and no combined page impact score is calculated. An eligible page can legitimately return zero candidates, which means these rules did not fire, not that its SEO is healthy.
保留每个独立已检测候选。页面可同时具有流量与排名下降，或其他组合。分别评估每个候选；候选互不压制，不计算综合页面影响评分。合格页面可合理返回零个候选，表示这些规则未触发，不表示其 SEO 健康。

## Real-data workflow audit and remedy / 真实数据流程审计与修复

The earlier importer accepted latest-28-day Filters labels but rejected explicit custom date ranges. Two latest-28-day reports exported at least 28 days apart could already become ready if all other evidence passed. Weekly exports generally overlap; custom non-overlapping historical periods were blocked even with complete daily evidence. Phase 8 fixes that narrow source-validation blocker before adding prioritization.
此前导入器接受最近 28 天筛选标签，但拒绝明确自定义日期范围。只要其他证据均通过，至少相隔 28 天导出的两个最近 28 天报告原本即可就绪。每周导出通常重叠；即使每日证据完整，自定义互不重叠历史时间段仍被阻止。第八阶段先修复此限定的数据源校验阻碍，再增加优先级。

XLSX Filters date labels now accept unambiguous ISO `YYYY-MM-DD` or Chinese `YYYY年M月D日` endpoints separated by `to`, `至`, `到`, `-`, `–`, or `—`, with an optional `Custom`, `Custom date range`, `自定义`, or `自定义日期范围` prefix. Dates must be valid and span exactly 28 days including both endpoints. Examples are `2026-01-01 to 2026-01-28` and `自定义：2026年1月29日至2026年2月25日`. Bare custom labels require independently observed complete 28-day coverage.
XLSX 筛选日期标签现在接受无歧义 ISO `YYYY-MM-DD` 或中文 `YYYY年M月D日` 起止值，以 `to`、`至`、`到`、`-`、`–` 或 `—` 分隔，可带 `Custom`、`Custom date range`、`自定义` 或 `自定义日期范围` 前缀。日期必须有效，且包含两个起止日恰为 28 天。示例为 `2026-01-01 to 2026-01-28` 与 `自定义：2026年1月29日至2026年2月25日`。仅有自定义标签时，需要独立观察到完整 28 天覆盖。

Different explicit ranges in the workbook or reliable observed bounds outside a declared range return `conflicting_reporting_dates`. Invalid, ambiguous, non-28-day ranges and bare custom labels without complete coverage return `unsupported_reporting_window`. Explicit ranges with sparse or unknown date evidence can import, retaining partial or unknown coverage; they cannot unlock opportunity detection. Latest labels and absent/blank date metadata keep their previous behavior.
工作簿内不同明确范围，或可靠已观察起止值超出声明范围时，返回 `conflicting_reporting_dates`。无效、歧义、非 28 天范围，以及缺少完整覆盖的单独自定义标签，返回 `unsupported_reporting_window`。明确范围配合稀疏或未知日期证据可导入，但覆盖保持部分或未知，不能解锁机会检测。最近日期标签及缺失、空白日期元数据保留此前行为。

Only the recognized daily-date worksheets establish observed endpoints, date count, consecutiveness, and coverage. Labels do not supply dates, turn sparse endpoints into 28 observations, or repair malformed/conflicting daily sheets. CSV remains unknown-date/unknown-coverage. The legacy `reporting_window="latest_28_days"` literal is unchanged and represents the existing 28-day metric family, not proof that dates are relative to upload time. Scope fingerprints, duplicate identity, stored history, and comparison semantics are unchanged; no migration or backfill is needed.
只有已识别每日日期工作表建立已观察起止值、日期数量、连续性及覆盖。标签不提供日期、不将稀疏起止值变成 28 个观察，也不修复损坏或冲突的每日工作表。CSV 日期与覆盖继续未知。旧 `reporting_window="latest_28_days"` 字面值保持不变，表示已有 28 天指标类别，不证明日期相对于上传时间。范围指纹、重复身份、已存储历史及对比语义保持不变，无需迁移或回填。

## Versioned, inclusive v1 thresholds / 带版本且包含边界的 V1 阈值

`OpportunityPriorityConfig` and each nested threshold dataclass are frozen. `DEFAULT_PRIORITY_CONFIG` centralizes the immutable defaults with version `priority-v1`. API callers cannot supply thresholds. Evaluate every high-tier predicate together first; if they do not all pass, evaluate every medium-tier predicate together; otherwise retain the detected candidate as low. Every priority boundary below includes equality.
`OpportunityPriorityConfig` 及每个嵌套阈值数据类均不可变。`DEFAULT_PRIORITY_CONFIG` 集中保存不可变默认值，版本为 `priority-v1`。API 调用者不能提供阈值。先同时评估高层级全部谓词；若未全部通过，再同时评估中层级全部谓词；否则将已检测候选保留为低层级。以下优先级边界均包含等号。

| Existing type / 已有类型 | High: all required / 高：全部满足 | Medium: all required / 中：全部满足 |
| --- | --- | --- |
| `traffic_decline` | Previous clicks ≥ 20; click loss ≥ 10; click decline ≥ 30%.<br>此前点击 ≥ 20；点击减少 ≥ 10；点击下降 ≥ 30%。 | Previous clicks ≥ 10; click loss ≥ 5; click decline ≥ 20%.<br>此前点击 ≥ 10；点击减少 ≥ 5；点击下降 ≥ 20%。 |
| `ctr_opportunity` | Both periods' impressions ≥ 500; CTR decline ≥ 1 percentage point.<br>两个时间段展示均 ≥ 500；CTR 下降 ≥ 1 个百分点。 | Both periods' impressions ≥ 150; CTR decline ≥ 0.7 percentage points.<br>两个时间段展示均 ≥ 150；CTR 下降 ≥ 0.7 个百分点。 |
| `ranking_decline` | Both periods' impressions ≥ 500; average-position worsening ≥ 4.<br>两个时间段展示均 ≥ 500；平均排名变差 ≥ 4。 | Both periods' impressions ≥ 150; average-position worsening ≥ 3.<br>两个时间段展示均 ≥ 150；平均排名变差 ≥ 3。 |
| `impression_growth_gap` | Both periods' impressions ≥ 500; impression growth ≥ 50%; CTR decline ≥ 1 percentage point.<br>两个时间段展示均 ≥ 500；展示增长 ≥ 50%；CTR 下降 ≥ 1 个百分点。 | Both periods' impressions ≥ 150; impression growth ≥ 35%; CTR decline ≥ 0.5 percentage points.<br>两个时间段展示均 ≥ 150；展示增长 ≥ 35%；CTR 下降 ≥ 0.5 个百分点。 |

The traffic rule combines baseline volume, absolute loss, and relative decline so a large percentage on a tiny count remains low. Impression minima temper attention to sparse CTR/position observations. CTR and position deltas separate larger measured changes from weaker existing signals. The growth-gap rule also requires a larger exact growth ratio. These are explainable preliminary heuristics supplied for this phase, not thresholds established by statistical validation or universal SEO correctness. Low still denotes an actual detected signal, not noise dismissal or proof that no action is needed.
流量规则同时要求基准数量、绝对减少及相对下降，使极小计数的大百分比变化仍为低层级。最低展示数量限制对稀疏 CTR 或排名观察的关注程度。CTR 与排名变化将较大测量变化和较弱已有信号分开。增长缺口规则还要求更大的准确增长比率。这些是本阶段提供的可解释初步启发式规则，不是通过统计验证确立或普遍正确的 SEO 阈值。低层级仍表示实际已检测信号，不是忽略为噪声，也不证明无需行动。

Original Phase 7 stable-position and impression-change predicates have already passed for a CTR candidate; original click-growth and CTR predicates have already passed for a growth-gap candidate. Prioritization does not duplicate or relax those detection rules. A higher numerical average position means worse ranking.
CTR 候选已通过原第七阶段排名稳定及展示变化谓词；增长缺口候选已通过原点击增长及 CTR 谓词。优先级不重复或放宽这些检测规则。平均排名数值越大表示排名越差。

### Exact arithmetic and units / 精确计算与单位

Priority arithmetic reads the candidate's original `previous` and `current` measurements, not rounded descriptive percentages in `evidence.changes`. Signed changes remain `current - previous`. Positive click loss/decline is the negated click change; positive CTR decline is the negated percentage-point change. CTR fractions have six stored decimal places, and position has four. Exact Decimal subtraction uses its own sufficient precision independent of the caller's context.
优先级计算读取候选原始 `previous` 与 `current` 测量值，不读取 `evidence.changes` 内已舍入描述性百分比。带符号变化保持 `当前 - 此前`。正数点击减少或下降为点击变化的相反数；正数 CTR 下降为百分点变化的相反数。CTR 存储比例具有六位小数，排名具有四位小数。精确 Decimal 减法使用自身足够精度，不依赖调用方上下文。

For positive baseline `previous`, a signed percentage is exactly `((current - previous) * 100) / previous`. To compare a positive loss/growth numerator `n`, denominator `d`, and threshold `t = a/b`, evaluate `n*b >= d*a` using integers. No displayed rounding can promote a just-below-threshold ratio to a higher tier. Percentage-point change is `(current_ctr - previous_ctr) * 100`; it is not a relative CTR percentage change.
正数基准 `previous` 的带符号百分比恰为 `((current - previous) * 100) / previous`。比较正数减少或增长分子 `n`、分母 `d` 与阈值 `t = a/b` 时，使用整数评估 `n*b >= d*a`。展示舍入不能将略低于阈值的比率提升至更高层级。百分点变化为 `(current_ctr - previous_ctr) * 100`，不是 CTR 相对百分比变化。

Exact percentage numerators and denominators serialize as integer strings because the numerator can exceed JavaScript's safe-integer range even when every imported count is safe. Decimal inputs and thresholds also serialize as strings; original count inputs remain integers. The browser displays these values and the assigned tier without recalculating priority with floating-point arithmetic.
精确百分比分子与分母序列化为整数字符串，因为即使每个导入计数均安全，分子仍可能超出 JavaScript 安全整数范围。Decimal 输入与阈值也序列化为字符串；原始计数输入保持整数。浏览器显示这些值及已分配层级，不使用浮点计算重新分配优先级。

## Candidate contract / 候选契约

The internal frozen `PrioritizedOpportunityCandidate` retains the original candidate in `candidate`. The API flattens the original Phase 7 fields without changing them and adds these fields:
内部不可变 `PrioritizedOpportunityCandidate` 在 `candidate` 中保留原始候选。API 展平原第七阶段字段，不改变它们，并增加以下字段：

| Added field / 新增字段 | Meaning / 含义 |
| --- | --- |
| `priority_tier` | `high`, `medium`, or `low` attention tier.<br>`high`、`medium` 或 `low` 关注层级。 |
| `priority_rule_version` | The configuration version, currently `priority-v1`.<br>配置版本，当前为 `priority-v1`。 |
| `priority_reason_code` | Type plus `_high_thresholds_met`, `_medium_thresholds_met`, or `_low_higher_tier_thresholds_not_met`.<br>类型加上上述高、中满足阈值或低层级未满足更高阈值后缀。 |
| `priority_message` | English-first Chinese-second factual tier explanation and original measurements.<br>英文在前、中文在后的事实层级解释及原始测量值。 |
| `priority_inputs` | Exact original values and derived signed changes or integer-ratio strings relevant to the tier rule.<br>与层级规则相关的准确原始值、派生带符号变化或整数比字符串。 |
| `priority_thresholds` | Both `high` and `medium` dictionaries, including for low candidates.<br>同时包含 `high` 与 `medium` 字典，包括低层级候选。 |

Relevant priority input names are:
相关优先级输入名称为：

- Traffic: `previous_clicks`, `current_clicks`, `clicks_absolute_change`, `clicks_percentage_change_numerator`, `clicks_percentage_change_denominator`.
  流量：此前与当前点击、点击绝对变化、准确点击百分比变化分子与分母。
- CTR: `previous_impressions`, `current_impressions`, `previous_ctr`, `current_ctr`, `ctr_percentage_point_change`.
  CTR：此前与当前展示、此前与当前 CTR、CTR 百分点变化。
- Ranking: `previous_impressions`, `current_impressions`, `previous_average_position`, `current_average_position`, `average_position_change`.
  排名：此前与当前展示、此前与当前平均排名、平均排名变化。
- Growth gap: the CTR inputs plus `impressions_absolute_change`, `impressions_percentage_change_numerator`, `impressions_percentage_change_denominator`.
  增长缺口：CTR 输入加展示绝对变化、准确展示百分比变化分子与分母。

Threshold keys are `minimum_previous_clicks`, `minimum_click_loss`, and `minimum_click_decline_percentage` for traffic; `minimum_impressions` and `minimum_ctr_decline_percentage_points` for CTR; `minimum_impressions` and `minimum_average_position_worsening` for ranking; `minimum_impressions`, `minimum_impressions_growth_percentage`, and `minimum_ctr_decline_percentage_points` for growth gap. Detection thresholds remain separately available in the original `evidence.thresholds`.
流量阈值键为 `minimum_previous_clicks`、`minimum_click_loss` 与 `minimum_click_decline_percentage`；CTR 为 `minimum_impressions` 与 `minimum_ctr_decline_percentage_points`；排名为 `minimum_impressions` 与 `minimum_average_position_worsening`；增长缺口为 `minimum_impressions`、`minimum_impressions_growth_percentage` 与 `minimum_ctr_decline_percentage_points`。检测阈值仍在原始 `evidence.thresholds` 中单独提供。

All original type/page/site/URL identity, selected snapshot IDs, exact periods, `ready`/`compatible` facts, reason/message, and metric/change/threshold evidence remain available. There is no persistent candidate ID, status lifecycle, score, recommendation, forecast, effort, risk, or AI-confidence field. Tiers and candidates are recomputed at request time; no analysis-version history is persisted.
所有原始类型、页面、站点、URL 身份，所选快照 ID、准确时间段、`ready` 与 `compatible` 事实、原因与消息，以及指标、变化和阈值证据均继续可用。没有持久化候选 ID、状态生命周期、评分、建议、预测、工作量、风险或 AI 置信度字段。层级与候选在请求时重新计算，不持久化分析版本历史。

## Read-only API, ordering, and empty results / 只读 API、排序及空结果

```sh
curl 'http://localhost:8000/api/v1/opportunities/prioritized?page=1&page_size=50'
curl 'http://localhost:8000/api/v1/opportunities/prioritized?site_id=SITE_UUID&priority_tier=high'
curl 'http://localhost:8000/api/v1/opportunities?page=1&page_size=50'
```

Replace `SITE_UUID` with a recorded site ID from page/import history. The prioritized endpoint accepts `page >= 1` (default 1), `page_size` 1–100 (default 50), optional UUID `site_id`, and optional `priority_tier` of `high`, `medium`, or `low`. Site isolation follows stored page ownership, not URL inference. Invalid parameters return `422`; a valid nonexistent site returns an empty list. Database failures return a generic `503` without private details.
将 `SITE_UUID` 替换为页面或导入历史内已记录的站点 ID。优先级接口接受 `page >= 1`（默认 1）、1–100 的 `page_size`（默认 50）、可选 UUID `site_id`，以及值为 `high`、`medium` 或 `low` 的可选 `priority_tier`。站点隔离遵循已存储页面归属，不根据 URL 推断。无效参数返回 `422`；有效但不存在站点返回空列表。数据库失败返回不含私人细节的通用 `503`。

Response fields are `items`, `page`, `page_size`, `total`, `total_pages`, and `summary`. `total` and `total_pages` count actual candidates after tier filtering. Sorting is **High → Medium → Low**, then exact URL, opportunity type, and page UUID. A page with several candidates consumes several result slots. No numerical or estimated SEO value decides ordering inside a tier. A page beyond the end returns empty `items`; an empty filtered list has zero total pages.
响应字段为 `items`、`page`、`page_size`、`total`、`total_pages` 及 `summary`。`total` 与 `total_pages` 统计层级筛选之后的实际候选。先按 **高 → 中 → 低**，再按精确 URL、机会类型及页面 UUID 排序。具有多个候选的页面占多个结果位置。层级内排序不由数值或预计 SEO 价值决定。超出末页返回空 `items`；空筛选列表总页数为零。

The existing `GET /api/v1/opportunities` neutral contract stays unchanged: it has only the five pagination fields, retains Phase 7 evidence without priority additions, and orders by URL/type/page ID. Page-level opportunities and the embedded performance response remain factual Phase 7 analyses. The new listing reuses two grouped page/history SELECTs and one comparison/quality/detection analysis per page, without queries per page or candidate.
已有 `GET /api/v1/opportunities` 中立契约保持不变：仅包含五个分页字段，保留第七阶段证据且不增加优先级，并按 URL、类型及页面 ID 排序。页面级机会及内嵌性能响应仍为事实第七阶段分析。新列表复用两个分组页面、历史 SELECT，以及每个页面一次对比、质量与检测分析，不按页面或候选单独查询。

The summary always describes all analyzed pages within the selected site **before tier filtering and pagination**:
摘要始终在**层级筛选及分页之前**描述所选站点全部已分析页面：

| Summary field / 摘要字段 | Meaning / 含义 |
| --- | --- |
| `analyzed_pages` | All relevant imported pages; zero means no pages in this selection.<br>全部相关已导入页面；零表示此选择内没有页面。 |
| `eligible_pages`, `ineligible_pages` | Existing Phase 7 evidence-gate outcomes; sum to `analyzed_pages`.<br>已有第七阶段证据门槛结果；之和为 `analyzed_pages`。 |
| `pages_with_candidates` | Eligible pages that emitted at least one original candidate.<br>生成至少一个原始候选的合格页面。 |
| `ready_pages_without_candidates` | Eligible pages with no detected signal; together with `pages_with_candidates`, sums to `eligible_pages`.<br>没有检测到信号的合格页面；与 `pages_with_candidates` 之和为 `eligible_pages`。 |
| `detected_candidates` | All original candidates before tier filtering; may exceed page counts.<br>层级筛选之前全部原始候选；可超过页面数量。 |
| `gate_reason_counts` | Existing quality codes counted once per affected ineligible page per code; includes zero counts and can overlap.<br>已有质量代码按每个受影响不合格页面、每个代码计一次；包含零计数，且可重叠。 |

With a selected comparison, gate counts use its existing Phase 7 gate reasons. When no comparison exists, recorded scope/date/coverage observations supplement the broad `insufficient_history` code. That code means no eligible comparison, not necessarily fewer than two snapshots. Unrelated historical warnings never label an eligible page blocked. Counts are factual context, not a second quality taxonomy or an exhaustive diagnosis of every alternative history pair.
有所选对比时，门槛计数使用其已有第七阶段门槛原因。没有对比时，已记录范围、日期与覆盖观察补充宽泛的 `insufficient_history` 代码。此代码表示没有合格对比，不一定表示少于两个快照。无关历史警告绝不将合格页面标为受阻。计数为事实背景，不是第二套质量分类或对所有备选历史对的穷尽诊断。

The `/opportunities` workspace has separate prioritized and original neutral views. Prioritized cards show tier/type/URL, periods, measured changes, rationale, version, both tier threshold sets, and snapshot references. The summary distinguishes no pages, unavailable history, unknown/incompatible scope, incomplete/unknown coverage, ready-no-signal pages, and detected candidates. No matching tier and an out-of-range result page are separate from no detected candidates. Empty output never declares the site's SEO healthy. No recommendation or execution buttons are present.
`/opportunities` 工作区具有分开的优先级与原中立视图。优先级卡片显示层级、类型、URL、时间段、测量变化、理由、版本、两个层级阈值集合及快照引用。摘要区分没有页面、历史不可用、未知或不兼容范围、部分或未知覆盖、就绪但无信号页面，以及已检测候选。没有匹配层级及结果页超出范围，与没有已检测候选分别处理。空输出绝不宣称站点 SEO 健康。没有建议或执行按钮。

## Synthetic tier examples / 合成层级示例

Each example assumes the full existing evidence gate passes and a Phase 7 candidate already exists. Other required metrics are present; other types may also fire. These are synthetic measurements, not real-site observations.
每个示例均假设已有完整证据门槛已通过，且第七阶段候选已存在。其他必要指标均存在；其他类型还可同时触发。这些是合成测量，不是真实站点观察。

| Candidate / 候选 | High / 高 | Medium / 中 | Low / 低 |
| --- | --- | --- | --- |
| `traffic_decline` | Clicks `20 → 10`: loss 10, decline 50%.<br>点击 `20 → 10`：减少 10，下降 50%。 | Clicks `10 → 5`: loss 5, decline 50%.<br>点击 `10 → 5`：减少 5，下降 50%。 | Clicks `5 → 2`: loss 3, decline 60%; below medium volume/loss.<br>点击 `5 → 2`：减少 3，下降 60%；低于中层级数量与减少要求。 |
| `ctr_opportunity` | Impressions `500 → 500`, CTR `5% → 4%`, stable position.<br>展示 `500 → 500`，CTR `5% → 4%`，排名稳定。 | Impressions `150 → 150`, CTR `5% → 4.3%`, stable position.<br>展示 `150 → 150`，CTR `5% → 4.3%`，排名稳定。 | Impressions `50 → 50`, CTR `5% → 4.5%`, stable position.<br>展示 `50 → 50`，CTR `5% → 4.5%`，排名稳定。 |
| `ranking_decline` | Impressions `500 → 500`, position `4 → 8`.<br>展示 `500 → 500`，排名 `4 → 8`。 | Impressions `150 → 150`, position `4 → 7`.<br>展示 `150 → 150`，排名 `4 → 7`。 | Impressions `50 → 50`, position `4 → 6`.<br>展示 `50 → 50`，排名 `4 → 6`。 |
| `impression_growth_gap` | Impressions `500 → 750`, clicks `50 → 50`, CTR `10% → 6.6667%`.<br>展示 `500 → 750`，点击 `50 → 50`，CTR `10% → 6.6667%`。 | Impressions `200 → 270`, clicks `20 → 20`, CTR `10% → 7.4074%`.<br>展示 `200 → 270`，点击 `20 → 20`，CTR `10% → 7.4074%`。 | Impressions `100 → 125`, clicks `10 → 10`, CTR `10% → 8%`.<br>展示 `100 → 125`，点击 `10 → 10`，CTR `10% → 8%`。 |

A traffic high example exposes signed `clicks_absolute_change=-10`, percentage numerator `"-1000"` and denominator `"20"`, high thresholds `{20, 10, "30"}`, and medium thresholds `{10, 5, "20"}` under their named keys. The exact signed percentage is `-1000/20 = -50%`; the positive decline is 50%. Version is `priority-v1` and reason code is `traffic_decline_high_thresholds_met`. Medium and low use their respective documented suffixes.
流量高层级示例公开带符号 `clicks_absolute_change=-10`、百分比分子 `"-1000"` 与分母 `"20"`、命名键对应的高阈值 `{20, 10, "30"}` 及中阈值 `{10, 5, "20"}`。准确带符号百分比为 `-1000/20 = -50%`，正数下降为 50%。版本为 `priority-v1`，原因代码为 `traffic_decline_high_thresholds_met`。中与低使用各自已记录后缀。

## Verification and real-data status / 验证与真实数据状态

Synthetic English and Chinese XLSX integration checks exercise preview, explicit confirmation, two independently observed complete periods (`2026-01-01–2026-01-28`, then `2026-01-29–2026-02-25`), compatible declared scope, atomic persistence, ready comparison, and existing Phase 7 candidates. Separate cases retain incomplete/unknown dates, incompatible/unknown scope, overlap, duplicate retry, blank carry-forward, measured zero, same-value source refresh, and read-only source/opportunity preservation. Automated tier checks cover every rule, inclusive boundaries, low-volume signals, exact rounded-display cases, context independence, multiple signals, filtering, pagination, stable order, and neutral-contract regressions.
合成英文及中文 XLSX 集成检查覆盖预览、明确确认、两个独立观察到完整覆盖的时间段（`2026-01-01–2026-01-28`，随后 `2026-01-29–2026-02-25`）、兼容声明范围、原子持久化、就绪对比及已有第七阶段候选。独立用例保留部分或未知日期、不兼容或未知范围、重叠、重复重试、空白沿用、测得零、相同值来源刷新，以及来源与机会的只读保留。自动层级检查覆盖每条规则、包含边界、低数量信号、准确舍入展示情况、上下文独立性、多信号、筛选、分页、稳定排序及中立契约回归。

Read-only parsing of one authorized real workbook confirmed supported Chinese latest-28 metadata and 28 distinct consecutive observed dates with complete coverage. It did not provide a second independent period or a complete property/full-filter scope. No private workbook, rows, URLs, metrics, or bytes are committed or used as automated fixtures. **Real-site calibration has not yet been performed.** Parser compatibility and synthetic correctness do not establish practical SEO usefulness.
对一个授权真实工作簿的只读解析确认了受支持中文最近 28 天元数据，以及 28 个不同连续已观察日期与完整覆盖。没有第二个独立时间段，也没有完整属性与完整筛选范围。不提交私人工作簿、行、URL、指标或字节，也不将它们用作自动化测试数据。**尚未进行真实站点校准。** 解析器兼容性与合成正确性不能证明实际 SEO 价值。

## Real TuffPlus acceptance procedure / 真实 TuffPlus 验收流程

Run this procedure privately in a local acceptance database migrated to `0004_report_scope`; keep exports and acceptance notes outside Git. No production deployment or data cleanup is part of this phase.
请在已迁移至 `0004_report_scope` 的本地验收数据库中私下执行此流程；导出与验收笔记保留在 Git 之外。本阶段不包含生产部署或数据清理。

1. In GSC, select the actual authorized TuffPlus property and record whether it is a domain or URL-prefix property. Do not infer that identity from the filename or page host. Select the same search type and full non-date filter ledger for both reports; use an explicit empty ledger only if no such filters were applied.
   在 GSC 中选择实际授权的 TuffPlus 属性，并记录其为网域或 URL 前缀属性。不要从文件名或页面主机推断此身份。两个报告选择相同搜索类型与完整非日期筛选清单；只有确实未应用此类筛选时，才使用明确空清单。
2. Export two separate completed 28-calendar-day periods as XLSX, without GSC's combined comparison presentation. The periods must not overlap; adjacent windows are convenient. Allow source reporting delay and inspect the daily worksheet for every date in each period. Do not manufacture omitted dates or metrics if an export is incomplete.
   将两个分别完成的 28 个日历天时间段导出为 XLSX，不使用 GSC 合并对比展示。时间段不得重叠；相邻窗口便于操作。考虑数据源报告延迟，并检查每日工作表中各时间段的每个日期。导出不完整时，不编造省略日期或指标。
3. At `/imports/gsc`, preview the older workbook. Supply accurate property/search/full-filter declarations only where needed. Verify detected `Pages`/`网页`, valid rows, the actual date endpoints, count 28, consecutive dates, `complete` coverage, and fully known scope. Inspect observed versus declared origins. Resolve source/declaration errors and preview again before confirmation.
   在 `/imports/gsc` 预览较早工作簿。仅在需要时补充准确属性、搜索及完整筛选声明。确认识别 `Pages` 或 `网页`、有效行、实际起止日期、数量 28、日期连续、`complete` 覆盖及完全已知范围。检查观察与声明来源。确认之前解决数据源或声明错误，并重新预览。
4. Explicitly apply the older report, record its import ID privately, then preview and apply the newer report with the same verified canonical scope. Expect one successful run per new file/scope and one snapshot per valid imported page. Do not change scope between preview and Apply. Importing old data after new data deliberately preserves apply-order current provenance and may limit the selected comparison.
   明确应用较早报告，私下记录其导入 ID，再以相同已确认规范范围预览并应用较新报告。每个新文件与范围应有一个成功导入，每个有效导入页面有一个快照。不要在预览与应用之间改变范围。新数据之后再导入旧数据会按设计保留应用顺序的当前来源，并可能限制所选对比。
5. Open shared pages in `/pages/[id]`. Verify both chosen snapshot IDs, independent periods, compatible scope, complete coverage, original GSC measurements, and `ready` quality. If blocked, use the displayed history/scope/date/metric/baseline/chronology facts; keep the gate intact. Pages missing from one export may lack a comparison. Complete daily coverage does not prove all page rows were exported.
   在 `/pages/[id]` 打开共有页面。确认两个选中快照 ID、独立时间段、兼容范围、完整覆盖、原始 GSC 测量及 `ready` 质量。若受阻，请使用显示的历史、范围、日期、指标、基准或时间顺序事实，保持门槛不变。某个导出缺失的页面可能没有对比。完整每日覆盖不证明全部页面行均已导出。
6. Select the site in the prioritized `/opportunities` view and compare its candidates with `GET /api/v1/opportunities?site_id=SITE_UUID`, or match cards manually in the global neutral UI. The original neutral UI has no site filter. Every prioritized item must match an original candidate's type and snapshot pair. Check the supplied `priority-v1` inputs and high/medium predicates manually against the private reports. Confirm multiple signals remain separate and that same-tier ordering follows URL/type/page ID. A ready zero-candidate result is valid; do not modify metrics or thresholds to force a signal.
   在 `/opportunities` 优先级视图中选择站点，并将候选与 `GET /api/v1/opportunities?site_id=SITE_UUID` 比较，或在全局中立界面中手动匹配卡片。原中立界面没有站点筛选。每个优先级条目必须匹配原始候选的类型及快照对。根据私人报告，手动检查提供的 `priority-v1` 输入及高、中谓词。确认多信号保持独立，相同层级按 URL、类型及页面 ID 排序。就绪且零候选为有效结果；不要修改指标或阈值强制产生信号。
7. Retry identical bytes with the same scope. Confirm the original import ID returns without new history, current-value changes, or provenance refresh. Exercise pagination and tier filtering; the eligibility summary must stay constant for the selected site. Repeated read-only analysis must not create `SEOOpportunity` records or change source/history/provenance.
   用相同范围重试相同字节。确认返回原导入 ID，不新增历史、不改变当前值，也不刷新来源。检查分页与层级筛选；所选站点的资格摘要必须保持不变。重复只读分析不得创建 `SEOOpportunity` 记录，也不得改变来源、历史或来源关联。
8. Record acceptance observations privately: useful signals, low-volume behavior, surprising tiers, omitted-page/export limitations, source delays, seasonality, and manual arithmetic checks. Treat them as site-specific feedback; these two reports cannot establish statistical significance or universal thresholds. Any calibration change needs separately reviewed evidence, documented rationale, a new rule version, and regression checks.
   私下记录验收观察：有用信号、低数量行为、出乎预期层级、缺失页面或导出限制、数据源延迟、季节性及手动计算检查。将其视为站点特定反馈；这两个报告不能建立统计显著性或通用阈值。任何校准变化都需要另行评审证据、记录理由、新规则版本及回归检查。

## Preservation and current limits / 保留与当前限制

No migration is added; Alembic head remains `0004_report_scope` and all six existing tables retain their semantics. No runtime candidates or priorities are persisted into `SEOOpportunity`. GET analysis changes no page, run, snapshot, provenance, site, or reserved opportunity row. Imports retain atomic writes, SHA-256/scope duplicate identity, preview binding, measured zeros, blank carry-forward, same-value refresh, legacy unknown provenance, and out-of-order apply behavior.
不增加迁移；Alembic 最新修订仍为 `0004_report_scope`，已有六个表保留各自语义。运行时候选或优先级不持久化至 `SEOOpportunity`。GET 分析不改变页面、导入、快照、来源、站点或预留机会行。导入保留原子写入、SHA-256 与范围重复身份、预览绑定、测得零、空白沿用、相同值来源刷新、未知旧来源及乱序应用行为。

Full relevant histories and candidates are loaded in memory before pagination, so this remains a development-scale workflow. Separate requests do not freeze concurrent imports; evidence and totals can change between result pages. No threshold calibration, statistical test, query/intent/SERP analysis, seasonality adjustment, expected CTR curve, authenticated property verification, complete page-export certification, immutable audit log, or production authentication is provided. Aggregate metrics and heuristic tiers cannot establish why a signal occurred or what action to take.
分页前在内存中读取全部相关历史与候选，因此仍为开发规模流程。独立请求不会冻结并发导入；结果页之间证据与总数可能变化。不提供阈值校准、统计检验、查询或意图或搜索结果分析、季节性调整、预期 CTR 曲线、已认证属性验证、完整页面导出证明、不可变审计日志或生产身份认证。汇总指标与启发式层级不能确定信号产生原因或应该采取的行动。

The next milestone is **MVP real-data acceptance and deployment**, scoped and reviewed separately. This is not authorization for automatic Phase 9 expansion, Decision Engine logic, AI recommendations, WordPress actions, GSC API synchronization, research/crawling, content generation, outreach, scheduling, accounts, or production deployment.
下一里程碑是另行定义范围并评审的 **MVP 真实数据验收与部署**。这不授权自动扩展第九阶段、决策引擎逻辑、AI 建议、WordPress 行动、GSC API 同步、研究或爬取、内容生成、外链联系、调度、账户或生产部署。
