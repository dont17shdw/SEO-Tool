# Report scope and observed-date coverage / 报告范围与已观察日期覆盖

## Purpose and boundaries / 目的与边界

Phase 6 distinguishes compatible reporting dates from proven comparable property/search/filter scope. All parsing, canonicalization, compatibility, and coverage rules are deterministic. No missing dimension is inferred from page URLs, filenames, metrics, import timestamps, neighboring imports, or an AI model.
第六阶段区分兼容报告日期与已证明可比的属性、搜索及筛选范围。全部解析、规范化、兼容性与覆盖规则均具有确定性。不从页面 URL、文件名、指标、导入时间戳、相邻导入或 AI 模型推断任何缺失维度。

Scope facts belong to `ImportRun` because they describe the whole report. Snapshots remain page observations and reuse run evidence in API responses. Current provenance still identifies the explicitly supplying snapshot; it is neither rewritten nor inferred by scope analysis. There are no SEO opportunities, scores, priorities, recommended actions, AI calls, integrations, or execution in this phase.
范围事实属于 `ImportRun`，因为它们描述整份报告。快照仍为页面观察，API 响应复用导入证据。当前来源仍标识明确提供值的快照；范围分析既不重写也不推断来源。本阶段没有 SEO 机会、评分、优先级、建议行动、AI 调用、集成或执行。

## Site and property identity / 站点与属性身份

`Site` has `id`, unique canonical `identifier`, `display_name`, and `created_at`. Its identifier is an explicitly observed or user-declared GSC property: a domain property such as `sc-domain:example.com`, or an HTTP(S) URL-prefix property such as `https://example.com/shop/`. The property is the minimal site namespace; it does not establish authenticated access, customer ownership, or that every imported URL belongs to that property.
`Site` 包含 `id`、唯一规范 `identifier`、`display_name` 及 `created_at`。标识为明确观察或用户声明的 GSC 属性：例如网域属性 `sc-domain:example.com`，或 HTTP(S) URL 前缀属性 `https://example.com/shop/`。属性构成最小站点命名空间；不证明已认证访问、客户归属或每个导入 URL 均属于该属性。

Property canonicalization trims outer whitespace, normalizes domain/host case and IDNA, removes a trailing host dot and default port, and gives a root URL-prefix property `/` when its path is empty. It preserves meaningful URL-prefix paths and nondefault ports. Credentials, queries, and fragments are invalid property input. Domain properties and URL-prefix properties remain distinct; HTTP and HTTPS, or distinct prefix paths, are never merged by assumption.
属性规范化去除前后空白，规范网域与主机大小写及 IDNA，移除主机末尾点与默认端口，路径为空时为根 URL 前缀属性补 `/`。保留有意义的 URL 前缀路径及非默认端口。凭据、查询字符串与片段均为无效属性输入。网域属性与 URL 前缀属性保持不同；HTTP 与 HTTPS 或不同前缀路径绝不被假定合并。

Both `WebsitePage.site_id` and `ImportRun.site_id` are nullable foreign keys. Pages are unique by `(site_id, url)` with `NULLS NOT DISTINCT`. All unknown-site pages form one separate namespace; a known-property import of the same URL creates/reuses its own known-property page without claiming the legacy page. Different properties can retain the same URL independently. Different search/filter scopes within one property share the current page, while their snapshots retain distinct run scope.
`WebsitePage.site_id` 与 `ImportRun.site_id` 均为可空外键。页面通过带 `NULLS NOT DISTINCT` 的 `(site_id, url)` 保持唯一。全部未知站点页面构成一个独立命名空间；同 URL 的已知属性导入创建或复用自身已知属性页面，不认领旧页面。不同属性可独立保留相同 URL。同一属性内不同搜索或筛选范围共享当前页面，快照则保留不同导入范围。

A Site is resolved/created only on Apply, inside the import transaction. Legacy records remain unowned when ownership cannot be proven. No production property is hardcoded into migrations. There is no Site CRUD, organization, team, or account interface.
站点仅在应用时、于导入事务内解析或创建。无法证明归属时，旧记录保持未知。迁移不硬编码任何生产属性。没有站点增删改查、组织、团队或账户界面。

## Structured scope and evidence origins / 结构化范围与证据来源

`report_scope` exposes resolved `property_id`, `property_status`, `site_identifier`, `search_type`, ordered `filters`, `filters_complete`, overall `status`, and `fingerprint`, alongside `workbook_observed`, `user_declared`, and machine-readable `issues`. The two origin objects retain property, search type, and optional filters supplied by their respective sources. Missing source evidence is not manufactured to fill those objects.
`report_scope` 公开解析后的 `property_id`、`property_status`、`site_identifier`、`search_type`、排序的 `filters`、`filters_complete`、整体 `status` 及 `fingerprint`，同时包含 `workbook_observed`、`user_declared` 与机器可读 `issues`。两个来源对象分别保留各自提供的属性、搜索类型及可选筛选。不会编造缺失来源证据来填充对象。

Known scope requires a known property, known search type, and an explicitly complete non-date filter ledger. A partial observed list can prove an individual condition or conflict but cannot prove absence of additional conditions. `filters=null` in a declaration means an unknown/incomplete ledger; `filters=[]` explicitly declares no non-date filters. An omitted worksheet, missing row, empty observed list, or bare search type never proves an unfiltered report.
已知范围要求已知属性、已知搜索类型及明确完整的非日期筛选清单。部分观察列表可证明单个条件或冲突，但不能证明不存在其他条件。声明中的 `filters=null` 表示未知或不完整清单；`filters=[]` 明确声明无非日期筛选。缺失工作表、缺失行、空观察列表或仅有搜索类型绝不证明未筛选报告。

An explicit declaration may supplement missing observed dimensions. If both origins provide conflicting property/search/filter evidence, preview/apply rejects it with `scope_declaration_conflict`; conflicting supported workbook rows use `conflicting_scope_metadata`. Unsupported or malformed source metadata stays visible in `issues` and keeps the resolved ledger incomplete even when the declaration would otherwise be complete. Unrecognized human text is not hashed as a proven filter identity.
明确声明可补充缺失观察维度。如果两个来源提供冲突属性、搜索或筛选证据，预览或应用通过 `scope_declaration_conflict` 拒绝；受支持工作簿行相互冲突使用 `conflicting_scope_metadata`。不支持或损坏来源元数据在 `issues` 中保持可见，并使解析后的清单保持不完整，即使声明原本完整。不将未识别人类文本作为已证明筛选身份计算哈希。

## Supported Filters worksheet evidence / 受支持筛选工作表证据

Only recognized `Filters`, `Filter`, and `过滤器` worksheets supply workbook scope. Rows must have a supported label and reliable textual value with no extra nonblank cells. Headers such as `Filter`/`Value` are ignored as headers; date rows remain separate reporting-window metadata. Aggregate `Countries`, `Devices`, `Queries`, or `Pages` tables do not prove applied filters.
仅已识别 `Filters`、`Filter` 与 `过滤器` 工作表提供工作簿范围。行必须包含受支持标签及可靠文本值，且不能有额外非空单元格。`Filter`、`Value` 等表头作为表头忽略；日期行仍为独立报告窗口元数据。汇总国家、设备、查询或网页表不能证明已应用筛选。

| Evidence / 证据 | Supported examples / 支持示例 |
| --- | --- |
| Property / 属性 | `Property`, `GSC property`, `Property id`, `属性`, `资源属性`, `GSC 属性` with a canonicalizable property identifier.<br>上述标签与可规范化属性标识。 |
| Search type / 搜索类型 | `Search type` / `搜索类型`; canonical `web`, `image`, `video`, `news`, including supported English/Chinese values such as `Web` / `网络`.<br>规范值及受支持英文、中文值。 |
| Device / 设备 | `Device` / `设备`; `mobile`, `desktop`, `tablet`, with supported localized values such as `移动设备`.<br>规范设备值及受支持本地化值。 |
| Country / 国家 | `Country`, `Country/region`, `国家`, `国家/地区`; ISO alpha-3 codes. A small explicit workbook alias table maps United States/美国, China/中国, United Kingdom/英国, Canada/加拿大, Australia/澳大利亚, Germany/德国, France/法国, India/印度, and Japan/日本.<br>ISO 三字母代码及上述小型明确工作簿名称映射。 |
| Search appearance / 搜索结果呈现 | `Search appearance` / `搜索结果呈现` with a canonical machine identifier.<br>标签与规范机器标识。 |
| Query/page predicates / 查询与网页谓词 | Operator-qualified labels such as `Query contains` / `查询包含`, `Page equals` / `网页等于`, or explicit regex variants.<br>明确运算符标签或明确正则表达式变体。 |

A bare `Query`/`Page` label does not establish an equals/contains/regex operator. Unsupported values, extra-row shapes, or unresolved labels produce uncertainty, not a guessed match. Formula cell `data_type="f"` anywhere in a nonblank scope row produces `formula_scope_metadata`, skips that row, and keeps the resolved ledger incomplete even with a full declaration. Literal text beginning with `=` is distinguished from an unevaluated formula. Workbook rows alone never certify the complete non-date filter ledger.
仅有 `Query` 或 `Page` 标签不能确定等于、包含或正则运算符。不支持值、额外行形状或未解决标签产生不确定性，不产生猜测匹配。非空范围行中任一单元格的公式类型 `data_type="f"` 会产生 `formula_scope_metadata`，跳过该行，并使解析清单保持不完整，即使提供完整声明。以 `=` 开头的字面文本与未计算公式保持区分。仅有工作簿行绝不证明非日期筛选清单完整。

The previously inspected real localized export contained search type `网络` and date label `过去 28 天`, but no property identifier or complete filter ledger. Those two facts establish Web search and the supported window only. No real rows, identifiers, file bytes, or private workbook are committed; automated fixtures are synthetic.
此前检查的真实本地化导出包含搜索类型 `网络` 与日期标签 `过去 28 天`，但没有属性标识或完整筛选清单。这两个事实仅证明网络搜索及受支持窗口。不提交真实行、标识、文件字节或私人工作簿；自动化测试数据为合成数据。

## Declaration and canonical filters / 声明与规范筛选

Both upload endpoints accept optional multipart field `scope` containing a JSON declaration. Unknown keys and unsupported values are rejected; the field is bounded to 8,192 characters. The smallest fully declared synthetic example is:
两个上传接口均接受可选 multipart 字段 `scope`，内容为 JSON 声明。未知键及不支持值会被拒绝；字段限制为 8,192 个字符。最小完整合成声明示例：

```json
{
  "property_id": "sc-domain:example.com",
  "search_type": "web",
  "filters": []
}
```

A filtered synthetic example is:
带筛选的合成示例：

```json
{
  "property_id": "https://example.com/",
  "search_type": "web",
  "filters": [
    {"dimension": "device", "operator": "equals", "value": "mobile"},
    {"dimension": "country", "operator": "equals", "value": "USA"}
  ]
}
```

Supported dimensions are `country`, `device`, `search_appearance`, `query`, and `page`, with at most one distinct condition per dimension. Every declared predicate must explicitly provide `dimension`, `operator`, and `value`; a missing operator is invalid rather than defaulted. Enumerated dimensions accept `equals`/`not_equals`; query/page additionally accept `contains`, `not_contains`, `regex`, and `not_regex`. Regex conditions are stored as explicit predicates, not executed against URLs or queries. Values must be nonblank and have no control characters.
受支持维度为 `country`、`device`、`search_appearance`、`query` 及 `page`，每个维度至多一个不同条件。每个声明谓词必须明确提供 `dimension`、`operator` 与 `value`；缺失运算符属于无效输入，不采用默认值。枚举维度接受 `equals` 与 `not_equals`；查询或网页另接受 `contains`、`not_contains`、`regex` 及 `not_regex`。正则条件作为明确谓词存储，不针对 URL 或查询执行。值必须非空且不含控制字符。

Canonicalization removes duplicate equal predicates and sorts by dimension. Device/search identities normalize supported aliases, country declarations require ISO alpha-3 codes, and search-appearance values use lowercase machine identifiers. Ordinary filter values trim outer whitespace; query/page case and internal whitespace remain significant. Regex values preserve their complete text, including meaningful surrounding spaces. Conflicting conditions for the same dimension are rejected; no arbitrary Boolean-expression engine is added.
规范化移除重复相等谓词，并按维度排序。设备及搜索身份规范化受支持别名，国家声明要求 ISO 三字母代码，搜索结果呈现使用小写机器标识。普通筛选值去除前后空白；查询或网页大小写及内部空白仍有意义。正则值保留完整文本，包括有意义的前后空格。同维度冲突条件会被拒绝；不增加任意布尔表达式引擎。

The SHA-256 `fingerprint` hashes a versioned canonical JSON object containing property, search type, sorted filter predicates, and filter completeness. It excludes reporting dates, filename, import time, evidence-origin objects, and presentation issues. The same semantics in another ordering or supported spelling has the same identity; changing a property, search type, predicate value/operator, or complete-vs-unknown ledger changes identity. Unknown fingerprints identify uncertainty, not proven compatibility.
SHA-256 `fingerprint` 对带版本规范 JSON 对象计算哈希，其中包含属性、搜索类型、排序筛选谓词及筛选完整性。排除报告日期、文件名、导入时间、证据来源对象及展示问题。相同语义采用不同排序或受支持拼写时，身份相同；改变属性、搜索类型、谓词值或运算符、完整与未知清单状态时，身份改变。未知指纹标识不确定性，不表示已证明兼容。

## Preview binding and duplicate imports / 预览绑定与重复导入

`file_hash` remains raw-file SHA-256. `preview_hash` hashes that file identity plus the complete normalized report-scope evidence, including origins and declaration. Apply resubmits `scope`, reparses bytes, and verifies the preview binding before resolving the database dependency. A changed file or declaration requires re-preview; canonical equivalent filter ordering does not create a semantic change. A different declaration origin may require a fresh preview even when resolved canonical scope is unchanged.
`file_hash` 仍为原始文件 SHA-256。`preview_hash` 对该文件身份及完整标准化报告范围证据计算哈希，包括来源与声明。应用重新提交 `scope`、重新解析字节，并在解析数据库依赖之前验证预览绑定。文件或声明变化要求再次预览；规范等价筛选排序不会产生语义变化。即使解析后的规范范围不变，不同声明来源也可能要求新预览。

Successful duplicate uniqueness is `(source, source_type, file_hash, scope_fingerprint)`. Same bytes and same canonical scope return `already_processed=true` and the original run ID without refreshing current values, history, or provenance. Same bytes under another explicit scope create another run instead of resolving to unrelated history. Different bytes remain another run even if rows are semantically equal. Duplicate URLs inside one file still block Apply separately.
成功重复唯一性为 `(source, source_type, file_hash, scope_fingerprint)`。相同字节及相同规范范围返回 `already_processed=true` 与原导入 ID，不刷新当前值、历史或来源。相同字节配合另一明确范围创建另一导入，不解析至无关历史。即使行语义相等，不同字节仍是另一导入。单文件内重复 URL 仍独立阻止应用。

Legacy runs receive the canonical wholly-unknown identity and retain SQL `NULL` scope. A true unknown-scope retry returns the original run without backfill. If re-parsing the same workbook now provides additional supported observed scope, it can create a distinct newly evidenced run; it does not alter the old run or pretend that old evidence was recorded. Changing only evidence origin does not change duplicate identity when resolved scope remains the same.
旧导入获得规范完全未知身份，范围保留 SQL `NULL`。真正未知范围重试返回原导入，不回填。如果重新解析相同工作簿现提供额外受支持观察范围，可创建独立新证据导入；不改变旧导入，也不假装旧证据此前已记录。解析范围相同时，仅改变证据来源不会改变重复身份。

## Observed-date coverage / 已观察日期覆盖

Reliable XLSX daily-date worksheets provide a distinct date set. Multiple usable recognized sheets must agree; every nonblank data row must have a valid date. Repeated dates do not increase the count; order does not matter. Missing, malformed, ambiguous, conflicting, and CSV date evidence remains unknown. Dates are never filled from endpoint spans or the latest-28-days filter label.
可靠 XLSX 每日日期工作表提供不同日期集合。多个可用已识别工作表必须一致；每个非空白数据行必须具有有效日期。重复日期不增加数量；顺序不影响结果。缺失、损坏、歧义、冲突及 CSV 日期证据保持未知。绝不根据起止跨度或最近 28 天筛选标签补日期。

| Stored fact / 存储事实 | Exact rule / 准确规则 |
| --- | --- |
| `observed_date_count` | Number of distinct reliable observed dates; `NULL` when unknown.<br>不同可靠已观察日期数量；未知时为 `NULL`。 |
| `dates_consecutive` | Reliable count equals `(period_end - period_start).days + 1`; `NULL` when unknown.<br>可靠数量等于包含起止日跨度；未知时为 `NULL`。 |
| `coverage_status="complete"` | Count 28, consecutive, and inclusive span 28.<br>数量为 28、连续且包含起止日跨度为 28。 |
| `coverage_status="partial"` | Any other reliable nonempty date set, even if consecutive for fewer/more than 28 days.<br>任何其他可靠非空日期集合，即使少于或多于 28 天且连续。 |
| `coverage_status="unknown"` | No reliable set; count/consecutiveness stay `NULL`.<br>无可靠集合；数量与连续性保持 `NULL`。 |

For synthetic examples, September 1–28 with every date observed is complete. Only September 1, 10, and 28 is partial: count `3`, span `28`, and `dates_consecutive=false`. Twenty-eight rows repeating one date have count `1`, not `28`, and remain partial. Exact known endpoints can coexist with unknown legacy coverage because the migration cannot reconstruct the original daily set. Complete coverage proves observed dates only, not all page rows or zero-event days omitted by a source.
合成示例中，9 月 1–28 日每个日期均观察到时为完整。仅有 9 月 1、10、28 日时为部分：数量 `3`、跨度 `28`、`dates_consecutive=false`。28 行重复同一天的数量为 `1`，不是 `28`，仍为部分。准确已知起止值可与未知旧覆盖并存，因为迁移不能重建原始每日集合。完整覆盖仅证明已观察日期，不证明全部页面行或来源省略的零事件日。

## Compatibility and comparison selection / 兼容性与对比选择

| Result / 结果 | Deterministic rule / 确定性规则 |
| --- | --- |
| `incompatible` | Both sides explicitly provide different property/search values, conflicting predicate/operator/value for one known filter dimension, or one complete ledger proves absence of a condition explicitly present on the other side.<br>双方明确提供不同属性或搜索值、同一已知筛选维度谓词、运算符或值冲突，或一方完整清单证明不存在另一方明确提供的条件。 |
| `compatible` | No conflict, and both sides have known property, search type, and complete matching filter ledgers.<br>无冲突，且双方具有已知属性、搜索类型及完整匹配筛选清单。 |
| `unknown` | No explicit conflict but one or more essential dimensions or ledger completeness is unproven.<br>无明确冲突，但一个或多个必要维度或清单完整性未获证明。 |

An explicit mobile/desktop conflict is incompatible even if property is missing. One known scope versus a wholly unknown scope is unknown. Equal unknown fingerprints do not make scope compatible. An empty complete ledger conflicts with an explicit device predicate; an incomplete empty list does not prove that conflict.
明确移动与桌面设备冲突即使缺失属性也为不兼容。已知范围与完全未知范围之间为未知。相同未知指纹不会使范围兼容。完整空清单与明确设备谓词冲突；不完整空列表不能证明该冲突。

Comparison retains the same page/source/type/window, exact endpoints, equal inclusive duration, and distinct-period requirements. Latest revision selection groups by canonical scope identity and exact period, so an unrelated scope cannot erase another report with matching dates. Each scope stream contributes only its newest two distinct periods; known streams compare within their own canonical identity. Unknown/partial streams may also pair with nonconflicting other streams, using their bounded recent candidates. The eligible pair with the newest current reporting period wins, followed by current start/import time/ID and then previous end/start/import time/ID. A recent incompatible singleton cannot suppress an eligible pair in another stream. Legacy or partially known nonconflicting pairs remain descriptive and explicitly labeled `scope_compatibility="unknown"`; unknown scope is never promoted to compatible.
对比保留相同页面、来源、类型、窗口、准确起止值、相等包含起止日时长及不同时间段要求。最近修订选择按规范范围身份及准确时间段分组，使无关范围不能抹去日期相同的另一报告。每个范围流仅提供其最近两个不同时间段；已知范围流在自身规范身份内对比。未知或部分范围流也可与其他不冲突范围流配对，使用其有界近期候选。当前报告时间段最新的合格对优先，其次按当前起始日期、导入时间及 ID，再按此前结束日期、起始日期、导入时间及 ID 确定性排序。近期不兼容单条记录不能压制另一范围流内的合格对。旧或部分已知且不冲突对仍为描述性结果，明确标为 `scope_compatibility="unknown"`；未知范围绝不提升为兼容。

Rejected-scope evidence is bounded to one deterministic representative witness per distinct conflicting-dimension combination. It explains excluded alternatives without claiming to list all historical conflicting pairs. Selection uses full history to establish revisions and streams, independently of UI pagination; it is not an exhaustive pair enumeration or a ranking of SEO usefulness.
被拒绝范围证据限制为每个不同冲突维度组合的一条确定性代表记录。解释被排除候选，不声称列出全部历史冲突对。选择使用完整历史建立修订与范围流，独立于界面分页；不穷举全部快照对，也不对 SEO 价值排序。

Comparison exposes `previous_report_scope`, `current_report_scope`, `scope_compatibility`, and previous/current coverage status, observed date count, and consecutiveness. Arithmetic, `NULL` handling, zero-baseline behavior, and overlap caveats remain unchanged. Provenance follows Apply order within the page namespace regardless of selected history or filter scope.
对比公开 `previous_report_scope`、`current_report_scope`、`scope_compatibility`，以及此前、当前覆盖状态、已观察日期数量与连续性。计算、`NULL` 处理、零基准行为及重叠限制保持不变。来源在页面命名空间内跟随应用顺序，与所选历史或筛选范围无关。

## Readiness, API, and migration / 就绪度、API 与迁移

New stable quality codes are `unknown_report_scope`, `incompatible_report_scope`, `incomplete_date_coverage`, and `unknown_date_coverage`. No eligible pair remains `insufficient`. A selected unknown-scope pair or selected partial/unknown coverage makes readiness `limited`, alongside all previous caveats. `ready` requires matching proven scope and complete observed date coverage as well as the existing metric/date checks. Historical caveats and rejected incompatible alternatives remain visible without lowering an otherwise ready selected pair. Current-provenance observations remain independent.
新增稳定质量代码为 `unknown_report_scope`、`incompatible_report_scope`、`incomplete_date_coverage` 及 `unknown_date_coverage`。没有合格对仍为 `insufficient`。所选未知范围对或所选部分、未知覆盖使就绪度为 `limited`，同时保留全部此前限制。`ready` 除原有指标与日期检查之外，要求匹配已证明范围及完整已观察日期覆盖。历史限制与被拒绝不兼容候选保持可见，不降低原本就绪所选对。当前来源观察保持独立。

Preview, import history, `GET /api/v1/imports/{import_run_id}`, and joined page snapshots expose report evidence without writes. The UI distinguishes observed/declaration origins, unknown dimensions, and coverage before Apply and in history/comparison views. Shared loaders reuse existing run joins and full history; pagination cannot change analysis. There are no scope mutation or legacy assignment endpoints.
预览、导入历史、`GET /api/v1/imports/{import_run_id}` 及连接的页面快照公开报告证据，不执行写入。界面在应用前及历史、对比视图中区分观察与声明来源、未知维度及覆盖。共享读取流程复用已有导入连接与完整历史；分页不能改变分析。没有范围修改或旧归属分配接口。

Alembic head `0004_report_scope` preserves every existing page, opportunity, run, snapshot, provenance row, metric, timestamp, and link. It creates empty Sites and nullable unknown legacy evidence, using a canonical unknown fingerprint only for uniqueness. Upgrade fabricates no property/filter/date evidence. Downgrade preflights old URL/file uniqueness and refuses atomically if scoped duplicates cannot fit the previous schema. It never deletes retained history or rewrites hashes to force success. Details are in [data-model.md](data-model.md).
Alembic 最新修订 `0004_report_scope` 保留每个已有页面、机会、导入、快照、来源行、指标、时间戳与关联。创建空站点及可空未知旧证据，仅为唯一性使用规范未知指纹。升级不编造属性、筛选或日期证据。降级预检查旧 URL 与文件唯一性；按范围存储的重复项无法适应此前结构时，会原子拒绝。绝不删除保留历史或重写哈希来强制成功。详情见 [data-model.md](data-model.md)。

## Limits and downstream opportunity gate / 限制与后续机会门槛

Supported metadata and user declarations are factual evidence, not an authenticated GSC certificate. Unsupported operators/values remain unknown or reject invalid declaration. A complete declaration depends on the user supplying the correct full ledger; no external source verifies it. Domain/prefix identities are not automatically grouped into a larger website. Date coverage does not certify page-table completeness, accuracy, statistical significance, or independent nonoverlapping periods. Legacy unknowns remain unchanged. Direct SQL can bypass controlled writers; there is no immutable audit log. Analysis still loads full history in memory, and concurrent requests do not share a frozen snapshot.
受支持元数据及用户声明为事实证据，不是已认证 GSC 证明。不支持运算符或值保持未知，或拒绝无效声明。完整声明依赖用户提供正确完整清单；没有外部来源验证。网域与前缀身份不会自动归入更大网站。日期覆盖不证明页面表完整性、准确性、统计显著性或独立互不重叠时间段。旧未知保持不变。直接 SQL 可绕过受控写入器；没有不可变审计日志。分析仍在内存中读取完整历史，并发请求不共享冻结快照。

Phase 7 now uses these unchanged scope/coverage facts in a separate runtime [Opportunity Engine](opportunity-engine.md). A candidate requires existing `ready` readiness, explicitly `compatible` selected scope, and both reports' complete observed 28-day coverage; unknown or partial evidence generates zero candidates. The engine neither promotes declarations to authenticated ownership nor infers missing legacy evidence. It retains source IDs, metrics, and exact thresholds without writing `SEOOpportunity` records. Scoring, prioritization, Decision Engine, AI, integrations, recommendations, and execution remain separately scoped future work.
第七阶段现在在独立运行时[机会引擎](opportunity-engine.md) 中使用这些不变的范围与覆盖事实。候选要求已有 `ready` 就绪度、明确 `compatible` 所选范围，以及两个报告均有完整已观察 28 天覆盖；未知或部分证据生成零个候选。引擎既不将声明提升为已认证归属，也不推断缺失旧证据。保留来源 ID、指标及准确阈值，不写入 `SEOOpportunity` 记录。评分、优先级、决策引擎、AI、集成、建议及执行仍为另行定义范围的未来任务。
