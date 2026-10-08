# GSC Pages import / GSC 网页导入

## Supported source / 支持的数据源

The importer accepts one source: the Google Search Console Pages performance export for **28 days**, uploaded manually as `.csv` or `.xlsx`. XLSX supports existing latest-28-day labels and narrowly recognized custom 28-day ranges. It does not import search queries, countries, devices, search appearance, or indexing reports. English and Chinese localized page exports are supported. Date worksheets provide reporting-period and observed-date coverage evidence; supported Filters rows supply report-scope metadata. Neither becomes page records or dimension-table imports.
导入器接受一种数据源：Google Search Console **28 天**网页性能导出，手动上传 `.csv` 或 `.xlsx`。XLSX 支持已有最近 28 天标签及严格识别的自定义 28 天范围。不导入搜索查询、国家、设备、搜索结果呈现或索引报告。支持英文与中文本地化的网页导出。日期工作表提供报告时间段及已观察日期覆盖证据；受支持筛选行提供报告范围元数据。二者都不会成为页面记录或维度表导入。

CSV must be UTF-8, with or without a BOM. Comma, semicolon, and tab delimiters are supported. The first nonblank row is the header. Blank rows are ignored; row-level errors retain the original source row numbers.
CSV 必须使用 UTF-8，可包含或不包含 BOM。支持逗号、分号及制表符分隔。首个非空行为表头。空白行会被忽略；行级错误保留源文件中的原始行号。

XLSX uses `openpyxl` in read-only mode. Formula cells are not evaluated; metric formulas fail validation rather than silently becoming missing values. Prefer the case-insensitive `Pages` worksheet, then `网页`. If neither exists, accept only one worksheet with all recognized page-performance headers and at least one valid absolute HTTP(S) URL in the page dimension. Known unrelated worksheet names are excluded even if their metric columns resemble page metrics. Multiple matching fallback sheets are rejected; name the intended one `Pages` or `网页`.
XLSX 使用 `openpyxl` 只读模式。不计算公式单元格；指标公式会导致校验失败，不会静默变为缺失值。优先选择不区分大小写的 `Pages` 工作表，其次选择 `网页`。两者均不存在时，仅接受同时具有全部已识别网页性能列名，且网页维度至少包含一个有效绝对 HTTP(S) URL 的唯一工作表。已知的无关工作表名称会被排除，即使其指标列与网页指标相似。多个匹配的回退工作表会被拒绝；请将目标表命名为 `Pages` 或 `网页`。

Recognized filter worksheets are `Filters`, `Filter`, and `过滤器`. Their `Date`, `Dates`, `Date range`, or `日期` entries accept existing latest-28-day labels: `Last 28 days`, `Past 28 days`, `28 days`, `过去 28 天`, or `最近 28 天` (case and spacing variations are accepted). Phase 8 also accepts valid explicit 28-day inclusive ranges with ISO `YYYY-MM-DD` or Chinese `YYYY年M月D日` endpoints separated by `to`, `至`, `到`, `-`, `–`, or `—`, optionally prefixed by `Custom`, `Custom date range`, `自定义`, or `自定义日期范围` and a colon. Examples are `2026-01-01 to 2026-01-28` and `自定义：2026年1月29日至2026年2月25日`.
识别的筛选工作表为 `Filters`、`Filter` 与 `过滤器`。其中 `Date`、`Dates`、`Date range` 或 `日期` 条目接受已有最近 28 天标签：`Last 28 days`、`Past 28 days`、`28 days`、`过去 28 天` 或 `最近 28 天`（允许大小写与空白差异）。第八阶段还接受有效且包含起止日恰为 28 天的明确范围，起止值采用 ISO `YYYY-MM-DD` 或中文 `YYYY年M月D日`，以 `to`、`至`、`到`、`-`、`–` 或 `—` 分隔，可带 `Custom`、`Custom date range`、`自定义` 或 `自定义日期范围` 前缀及冒号。示例为 `2026-01-01 to 2026-01-28` 与 `自定义：2026年1月29日至2026年2月25日`。

Bare `Custom`, `Custom date range`, `自定义`, or `自定义日期范围` labels require independently observed complete 28-day coverage. Invalid/ambiguous/non-28-day ranges and bare custom labels without that evidence return `unsupported_reporting_window`. Different explicit ranges across recognized filter sheets/rows, or reliable observed dates outside the declared range, return `conflicting_reporting_dates`. An explicit valid range with partial or unknown daily evidence can import while keeping that evidence partial or unknown. Labels never supply endpoints or missing daily dates.
仅有 `Custom`、`Custom date range`、`自定义` 或 `自定义日期范围` 标签时，需要独立观察到完整 28 天覆盖。无效、歧义、非 28 天范围及缺少该证据的单独自定义标签返回 `unsupported_reporting_window`。已识别筛选工作表或行中的不同明确范围，或可靠已观察日期超出声明范围时，返回 `conflicting_reporting_dates`。有效明确范围配合部分或未知每日证据可导入，但证据保持部分或未知。标签绝不提供起止值或缺失每日日期。

Absent/blank date metadata keeps the existing 28-day export assumption: the user must select a 28-day report before export. The unchanged `reporting_window="latest_28_days"` identifier names the legacy 28-day metric family, not an upload-relative date guarantee; verified custom periods share that identity. CSV has no workbook date/filter evidence and remains unknown-date/unknown-coverage. Historical compatibility, scope identity, SHA-256 duplicate behavior, and provenance are unchanged.
缺失或空白日期元数据保留已有 28 天导出假设：用户必须在导出之前选择 28 天报告。不变的 `reporting_window="latest_28_days"` 标识表示旧 28 天指标类别，不保证相对于上传时间的日期；已校验自定义时间段共享此身份。CSV 没有工作簿日期或筛选证据，日期与覆盖继续未知。历史兼容性、范围身份、SHA-256 重复行为及来源保持不变。

Phase 3 additionally examines recognized XLSX date worksheets (`Chart`, `Date`, `Dates`, `图表`, `日期`) for observed reporting dates. Earliest/latest valid dates become `period_start`/`period_end`. Absent, malformed, or conflicting date evidence leaves both `NULL` and marks `period_status="unknown"`; the valid Pages import may continue. Filenames and import dates are never used to invent reporting dates. CSV has no exact period evidence in this contract. See [performance-history.md](performance-history.md) for the precise extraction rules.
第三阶段还检查已识别的 XLSX 日期工作表（`Chart`、`Date`、`Dates`、`图表`、`日期`）中的已观察报告日期。最早与最晚有效日期成为 `period_start` 与 `period_end`。日期证据缺失、损坏或冲突时，两者保持 `NULL` 并标记 `period_status="unknown"`；有效的网页导入仍可继续。绝不使用文件名或导入日期编造报告日期。此契约中的 CSV 没有准确时间段证据。明确的提取规则详见 [performance-history.md](performance-history.md)。

## Report scope and observed coverage / 报告范围与已观察覆盖

Phase 6 extracts only explicit supported Filters facts: property identifier, search type, enumerated country/device/search-appearance conditions, and query/page conditions with known operators. Workbook lists remain partial; an omitted condition does not mean no filter. In the previously inspected real localized export, only Web search (`网络`) and the past-28-days window were present; property identity and the full non-date filter ledger could not be proven. Source filenames and page hosts never supply missing property evidence.
第六阶段仅提取明确受支持筛选事实：属性标识、搜索类型、枚举国家、设备及搜索结果呈现条件，以及具有已知运算符的查询或网页条件。工作簿清单保持部分；省略条件不表示无筛选。此前检查的真实本地化导出仅提供网络搜索（`网络`）与过去 28 天窗口；属性身份及完整非日期筛选清单无法证明。源文件名及页面主机绝不提供缺失属性证据。

Optional multipart `scope` supplies structured `property_id`, `search_type`, and `filters`. Omitted/`null` filters mean unknown completeness; an explicit list, including `[]`, declares the full non-date filter ledger. Observed and declared origins are retained separately. Conflicts are rejected; unresolved workbook metadata remains visible and prevents false complete scope. Known property resolves a minimal Site on Apply; unknown ownership stays in its separate nullable namespace.
可选 multipart `scope` 提供结构化 `property_id`、`search_type` 及 `filters`。省略或 `null` 筛选表示完整性未知；明确列表（包括 `[]`）声明完整非日期筛选清单。观察及声明来源分别保留。冲突会被拒绝；未解决工作簿元数据保持可见，防止错误完整范围。已知属性在应用时解析最小站点；未知归属保持独立可空命名空间。

Coverage adds `observed_date_count`, `dates_consecutive`, and `coverage_status`. Reliable 28 distinct consecutive dates with a 28-day inclusive span are `complete`; other reliable sets are `partial`; missing/unreliable sets and CSV are `unknown`. Duplicate dates do not inflate counts. Legacy known endpoints receive no invented coverage. See [report-scope.md](report-scope.md) for exact declarations, aliases, operators, canonicalization, and compatibility rules.
覆盖增加 `observed_date_count`、`dates_consecutive` 及 `coverage_status`。可靠的 28 个不同连续日期，且包含起止日跨度为 28 天时，为 `complete`；其他可靠集合为 `partial`；缺失或不可靠集合及 CSV 为 `unknown`。重复日期不增加数量。旧已知起止日期不获得编造覆盖。准确声明、别名、运算符、规范化及兼容性规则详见 [report-scope.md](report-scope.md)。

## Source column mapping / 来源列映射

All five semantic columns must be identifiable. Metric cells may be empty; metric headers must still exist. This is a small GSC-specific alias table, without AI or a generic mapping framework. Labels match case-insensitively after trimming, collapsing whitespace, and treating underscores as spaces. Multiple columns matching the same semantic field are rejected.
五个语义列都必须能够识别。指标单元格可为空，但指标表头仍必须存在。这是一个小型 GSC 专用别名表，不使用 AI 或通用映射框架。标签去除前后空白、合并空白、将下划线视为空格后，不区分大小写进行匹配。多个列匹配同一语义字段时会被拒绝。

| Semantic key / 语义键 | Accepted headers / 接受的列名 | WebsitePage field / WebsitePage 字段 |
| --- | --- | --- |
| `url` | `Page`, `Pages`, `URL`, `Top pages`, `Top page`, `排名靠前的网页`, `网页` | `url` |
| `clicks` | `Clicks`, `Click`, `点击次数`, `点击数` | `clicks_28d` |
| `impressions` | `Impressions`, `Impression`, `展示`, `展示次数`, `展示数` | `impressions_28d` |
| `ctr` | `CTR`, `Click through rate`, `Click-through rate`, `点击率` | `ctr` |
| `position` | `Position`, `Average position`, `Avg position`, `排名`, `平均排名` | `average_position` |

The preview's `column_mapping` maps semantic keys to the original detected labels, for example `{"url":"排名靠前的网页","clicks":"点击次数","impressions":"展示","ctr":"点击率","position":"排名"}`. Unknown extra columns are ignored; they never populate other model fields.
预览中的 `column_mapping` 将语义键映射到原始检测标签，例如 `{"url":"排名靠前的网页","clicks":"点击次数","impressions":"展示","ctr":"点击率","position":"排名"}`。未知的额外列会被忽略；它们不会填充其他模型字段。

## Validation and normalization / 校验与标准化

- **URL:** Required textual absolute `http://` or `https://` URL with a valid host. Trim surrounding whitespace only. Do not remove trailing slashes, rewrite schemes, lowercase paths, or change query strings. The importer never fetches the URL.
  **URL：** 必须是文本形式、主机有效的绝对 `http://` 或 `https://` URL。仅去除前后空白。不移除末尾斜杠、不重写协议、不将路径转换为小写，也不修改查询字符串。导入器不会访问 URL。
- **Clicks and impressions:** Optional non-negative whole numbers from `0` through `9007199254740991` (`2^53 - 1`). This import bound keeps JSON integers exact in JavaScript; PostgreSQL still uses `BIGINT`. Standard thousands separators such as `1,000` are accepted; quote such values in comma-separated CSV. Fractional counts, negative values, booleans, and non-finite values are invalid.
  **点击数与展示数：** 可选的非负整数，范围为 `0` 至 `9007199254740991`（`2^53 - 1`）。此导入上限保证 JSON 整数在 JavaScript 中保持精确；PostgreSQL 仍使用 `BIGINT`。接受 `1,000` 等标准千位分隔符；在逗号分隔的 CSV 中请为此类值加引号。小数计数、负数、布尔值与非有限数均无效。
- **CTR:** Accept `2.5%` or fractional `0.025`; normalize both to `0.025000`. Percentages must be in `[0%, 100%]`; fractions must be in `[0, 1]`. Bare `2.5` is invalid. Validate bounds before rounding to six decimal places with `ROUND_HALF_UP`.
  **点击率：** 接受 `2.5%` 或比例小数 `0.025`；两者均标准化为 `0.025000`。百分数必须位于 `[0%, 100%]`；比例必须位于 `[0, 1]`。无百分号的 `2.5` 无效。先校验范围，再使用 `ROUND_HALF_UP` 舍入至六位小数。
- **Position:** Optional finite numeric value from `0` through `999999.9999`, matching `NUMERIC(10,4)`. Validate bounds before rounding to four decimal places with `ROUND_HALF_UP`.
  **排名：** 可选的有限数值，范围为 `0` 至 `999999.9999`，与 `NUMERIC(10,4)` 一致。先校验范围，再使用 `ROUND_HALF_UP` 舍入至四位小数。
- **Missing metrics:** Empty cells and whitespace-only strings normalize to `NULL`, not zero. Do not recalculate missing CTR from clicks/impressions, infer unknown SEO fields, or populate seven-day and previous-28-day metrics.
  **缺失指标：** 空单元格与仅含空白的字符串标准化为 `NULL`，不是零。不根据点击数与展示数重新计算缺失的点击率，不推导未知 SEO 字段，也不填充七天与前 28 天指标。

Synthetic example only; it contains no real website data:
仅为合成示例；不包含真实网站数据：

```csv
Page,Clicks,Impressions,CTR,Position
https://example.com/products,25,1000,2.5%,8.4
https://example.com/about,,,,
```

The first row normalizes to `clicks_28d=25`, `impressions_28d=1000`, `ctr=0.025000`, and `average_position=8.4000`. The second row has four unknown metrics.
首行标准化为 `clicks_28d=25`、`impressions_28d=1000`、`ctr=0.025000` 与 `average_position=8.4000`。第二行的四个指标均为未知。

## Duplicates and preview counts / 重复数据与预览统计

Duplicate detection compares exact URLs after trimming surrounding whitespace. Every occurrence of a duplicate URL is marked, including the first occurrence; no rows are aggregated. Two occurrences produce `duplicate_rows=2`. Differences in trailing slash, URL path case, scheme, or query string remain distinct.
重复检测比较去除前后空白后的精确 URL。重复 URL 的每次出现都会被标记，包括首次出现；不聚合行。出现两次会产生 `duplicate_rows=2`。末尾斜杠、URL 路径大小写、协议或查询字符串差异仍视为不同值。

Counts are mutually exclusive: `total_rows = valid_rows + invalid_rows + duplicate_rows`. Duplicate rows belong to the duplicate category even if they also have metric errors; those metric errors can still appear in the error list. Samples contain only valid, nonduplicate rows. Any invalid or duplicate row sets `can_apply=false` and blocks the entire import until corrected.
统计互斥：`total_rows = valid_rows + invalid_rows + duplicate_rows`。重复行归入重复类别，即使它们还存在指标错误；这些指标错误仍可能出现在错误列表中。样本仅包含有效且不重复的行。任何无效或重复行都会使 `can_apply=false`，并在修正前阻止整个导入。

## Preview and apply / 预览与应用

1. Select a CSV/XLSX file at `/imports/gsc`, optionally declare property/search/full filter scope, and request preview.
   在 `/imports/gsc` 选择 CSV/XLSX 文件，可选声明属性、搜索及完整筛选范围，并请求预览。
2. Inspect observed/declared scope, unknown dimensions, actual reporting dates and coverage, alongside source, worksheet, mapping, counts, errors, and normalized samples. Preview uses no PostgreSQL and creates no Site or other records.
   在数据源、工作表、映射、统计、错误与标准化样本之外，检查观察及声明范围、未知维度、实际报告日期与覆盖。预览不使用 PostgreSQL，也不创建站点或其他记录。
3. Correct errors in the source file and preview again if necessary.
   必要时修正源文件错误并重新预览。
4. Explicitly confirm import. Resubmit the retained file and the same normalized declaration with `confirmed=true` and `preview_hash`. Changing file or scope invalidates the earlier preview and requires revalidation.
   显式确认导入。重新提交保留文件及相同标准化声明，附带 `confirmed=true` 与 `preview_hash`。文件或范围改变会使此前预览失效，需要重新校验。
5. The backend reparses the file/scope and verifies the preview binding before database access. One transaction resolves optional Site, updates pages, records scope/coverage on a completed run, creates snapshots, and refreshes supplied provenance links. Already-processed bytes under the same canonical scope return the original run unchanged. Review `/imports/history` or a page's history.
   后端在访问数据库之前，重新解析文件与范围并验证预览绑定。一个事务解析可选站点、更新页面、在已完成导入上记录范围与覆盖、创建快照并刷新已提供来源关联。同一规范范围下已处理字节返回原导入且不修改。可查看 `/imports/history` 或页面历史。

No server-side preview session is stored. Normalized client-side rows are never accepted as the persistence source. The raw `file_hash` identifies source bytes; the separate `preview_hash` binds bytes and complete normalized scope evidence, including declared/observed origins. Canonical scope fingerprint determines duplicate identity together with raw bytes. These are consistency controls, not authentication. Source bytes are never retained permanently.
不存储服务端预览会话。客户端标准化行不会被接受为持久化数据源。原始 `file_hash` 标识来源字节；独立 `preview_hash` 绑定字节及完整标准化范围证据，包括声明与观察来源。规范范围指纹结合原始字节决定重复身份。这些是保持一致性的控制，不是身份认证。源字节不会永久保留。

## Persistence / 持久化

Upsert `WebsitePage` by `(site_id, exact trimmed URL)`, preserving the separate unknown-site namespace. Explicit property evidence does not claim a same-URL legacy page. Create a missing page using only supplied GSC values; unspecified nullable fields stay `NULL`. For an existing page, update only nonblank supplied `clicks_28d`, `impressions_28d`, `ctr`, and `average_position`. Blank incoming metrics preserve stored values, while measured zeros overwrite them. Unchanged existing pages count as skipped. Non-GSC fields, other reporting periods, and opportunities are preserved.
按 `(site_id, 去除前后空白后的精确 URL)` 新增或更新 `WebsitePage`，保留独立未知站点命名空间。明确属性证据不认领相同 URL 的旧页面。新页面仅使用已提供的 GSC 值；未指定的可空字段保持 `NULL`。已有页面仅更新已提供且非空白的 `clicks_28d`、`impressions_28d`、`ctr` 与 `average_position`。传入空白指标保留已存储值，测得的零则覆盖它们。未变化的已有页面计为跳过。非 GSC 字段、其他报告时间段与机会记录均保留。

For a new file/scope identity, one transaction commits any new Site, current-page upserts, one scoped `ImportRun` with `status="completed"`, snapshots for every validated row (including unchanged pages), and current provenance links. Each snapshot stores this upload's normalized metric values, including `NULL`; it never carries forward an omitted metric from the current page. PostgreSQL URL uniqueness resolves concurrent insert conflicts; existing rows are locked during updates. Any history, snapshot, or page persistence failure rolls back every change. Preview, invalid files, and failures create no import history. There is no partial import, delete operation, or automatic recommendation.
对于新的文件与范围身份，一个事务提交可选新站点、当前页面新增与更新、一个 `status="completed"` 且带范围的 `ImportRun`、每个已校验行的快照（包括页面未变化行）及当前来源关联。每条快照存储本次上传的标准化指标值，包括 `NULL`；绝不从当前页面沿用未提供的指标。PostgreSQL URL 唯一性处理并发插入冲突；更新时锁定已有行。任何历史、快照或页面持久化失败都会回滚全部变更。预览、无效文件及失败不创建导入历史。没有部分导入、删除操作或自动建议。

Identical successful `(source, source_type, file_hash, scope_fingerprint)` returns `already_processed=true`, the original `import_run_id`, zero created/updated counts, and a skipped count equal to the file's row count. That retry neither rewrites pages/provenance nor duplicates runs/snapshots, even if another file changed a page afterward; the original counts remain unchanged. The same bytes under another explicit canonical scope create a separate run and normally apply supplied fields within that Site's page namespace. Reusing a filename with different bytes is a new import; byte-level formatting changes can also create a new run. Duplicate-import protection is separate from duplicate URLs inside one file, which still block apply.
相同成功 `(source, source_type, file_hash, scope_fingerprint)` 返回 `already_processed=true`、原 `import_run_id`、零新增与更新数，以及等于文件行数的跳过数。该重试既不重写页面或来源，也不重复创建导入或快照，即使此后另一个文件改变了页面；原统计保持不变。相同字节配合另一明确规范范围会创建独立导入，并正常在该站点页面命名空间内应用已提供字段。同名但字节不同的文件是新导入；字节级格式变化也可能创建新记录。重复导入保护与单文件内重复 URL 不同；后者仍会阻止应用。

## API contract / API 契约

Both upload endpoints accept `multipart/form-data`. Run the following from a directory containing a synthetic or privately held `gsc-pages.csv`; do not commit source uploads.
两个上传接口均接受 `multipart/form-data`。在包含合成或私下保存的 `gsc-pages.csv` 的目录中运行以下命令；不要提交源上传文件。

```sh
curl -X POST http://localhost:8000/api/v1/imports/gsc/pages/preview \
  -F 'file=@gsc-pages.csv'
```

The preview response additionally includes raw `file_hash`, structured `report_scope`, `observed_date_count`, `dates_consecutive`, and `coverage_status`. It includes `source="gsc_pages"`, `reporting_window="latest_28_days"`, `period_start`, `period_end`, `period_status` (`exact` or `unknown`), `detected_sheet` (`null` for CSV), `total_rows`, `valid_rows`, `invalid_rows`, `duplicate_rows`, `column_mapping`, `errors`, `sample_rows`, `can_apply`, and `preview_hash`. Each error has `row`, `field`, `code`, and a human-readable `message`. Samples include source `row`, `url`, and the four normalized GSC fields. Decimal fields serialize as JSON strings, for example `"0.025000"`; missing metrics serialize as `null`.
预览响应另外包含原始 `file_hash`、结构化 `report_scope`、`observed_date_count`、`dates_consecutive` 及 `coverage_status`。它包含 `source="gsc_pages"`、`reporting_window="latest_28_days"`、`period_start`、`period_end`、`period_status`（`exact` 或 `unknown`）、`detected_sheet`（CSV 为 `null`）、`total_rows`、`valid_rows`、`invalid_rows`、`duplicate_rows`、`column_mapping`、`errors`、`sample_rows`、`can_apply` 与 `preview_hash`。每个错误包含 `row`、`field`、`code` 及易理解的 `message`。样本包含源 `row`、`url` 及四个标准化 GSC 字段。小数字段序列化为 JSON 字符串，例如 `"0.025000"`；缺失指标序列化为 `null`。

Replace the placeholder below with the exact 64-character lowercase hexadecimal hash returned by preview:
将下方占位符替换为预览返回的准确 64 位小写十六进制哈希：

```sh
curl -X POST http://localhost:8000/api/v1/imports/gsc/pages/apply \
  -F 'file=@gsc-pages.csv' \
  -F 'confirmed=true' \
  -F 'preview_hash=REPLACE_WITH_PREVIEW_HASH'
```

To declare scope, add the same JSON field to both calls; this synthetic example declares Web search and no non-date filters:
如需声明范围，请在两次调用中加入相同 JSON 字段；此合成示例声明网络搜索且无非日期筛选：

```sh
-F 'scope={"property_id":"sc-domain:example.com","search_type":"web","filters":[]}'
```

Use returned `preview_hash` for confirmation, never raw `file_hash`. Omit `scope` on both calls to retain unknown declaration. Equivalent canonical declaration ordering is accepted; changing resolved values or evidence origins requires another preview.
确认时使用返回的 `preview_hash`，绝不使用原始 `file_hash`。两次调用均省略 `scope` 可保留未知声明。接受等价规范声明排序；改变解析值或证据来源需要再次预览。

Success returns `import_run_id`, `already_processed`, `created_count`, `updated_count`, `skipped_count`, and `error_count` (`0` after success). For a new run, row counts describe current-page changes; snapshots are created even for skipped unchanged pages. A failed operation returns an HTTP error instead of reporting partial success. Historical read APIs are documented in [performance-history.md](performance-history.md).
成功时返回 `import_run_id`、`already_processed`、`created_count`、`updated_count`、`skipped_count` 与 `error_count`（成功后为 `0`）。新导入的行数描述当前页面变化；跳过的未变化页面仍会创建快照。失败操作返回 HTTP 错误，不会报告部分成功。历史读取 API 详见 [performance-history.md](performance-history.md)。

```sh
curl 'http://localhost:8000/api/v1/pages?page=1&page_size=50'
```

The page list returns `items`, `page`, `page_size`, `total`, and `total_pages`. Items contain `id`, nullable `site_id`, `url`, `clicks_28d`, `impressions_28d`, `ctr`, and `average_position`. `page` starts at 1; `page_size` defaults to 50 and must be 1–100. Ordering is stable by `created_at`, then `id`. An empty database has `total_pages=0`; a page beyond the end returns empty `items`. This is offset pagination, without a consistent snapshot across simultaneous imports.
页面列表返回 `items`、`page`、`page_size`、`total` 与 `total_pages`。条目包含 `id`、可空 `site_id`、`url`、`clicks_28d`、`impressions_28d`、`ctr` 与 `average_position`。`page` 从 1 开始；`page_size` 默认 50，必须位于 1–100。按 `created_at`、其次 `id` 保持稳定排序。空数据库的 `total_pages=0`；超出末页的页面返回空 `items`。这是偏移量分页，不提供跨并发导入的一致快照。

## Errors and resource limits / 错误与资源限制

| HTTP status / 状态 | Meaning / 含义 |
| --- | --- |
| `200` | Preview available, including row errors; or apply/list succeeded.<br>预览可用，包括行错误；或应用、列表成功。 |
| `422` | Unsupported/empty/malformed file, missing or ambiguous columns/sheets, conflicting reporting window, invalid form, missing confirmation, or blocked apply.<br>不支持、为空或损坏的文件，缺失或歧义列、工作表，冲突的报告窗口，无效表单，缺少确认或被阻止的应用。 |
| `409` | Submitted file or normalized scope evidence differs from preview; preview again.<br>提交文件或标准化范围证据与预览不同；请重新预览。 |
| `413` | Upload, expanded XLSX, or row limit exceeded.<br>超出上传、解压后 XLSX 或行数限制。 |
| `503` | Database operation failed; no partial import is committed.<br>数据库操作失败；不会提交部分导入。 |

File errors use `detail.code` and `detail.message`; invalid form/query parameters use FastAPI validation details. Internal reader exceptions and database stack traces are not returned. Row-level errors remain in a successful preview response so the user can inspect and correct them.
文件错误使用 `detail.code` 与 `detail.message`；无效表单或查询参数使用 FastAPI 校验详情。不会返回内部读取器异常或数据库堆栈。行级错误保留在成功的预览响应中，以便用户检查并修正。

Window validation returns `422` for `unsupported_reporting_window` or `conflicting_reporting_dates` before any database writes. Sparse/unknown daily evidence under an accepted explicit label stays visibly partial/unknown rather than becoming a file-window error. Opportunity gates still exclude those incomplete reports.
窗口校验在任何数据库写入之前，为 `unsupported_reporting_window` 或 `conflicting_reporting_dates` 返回 `422`。受接受明确标签下的稀疏或未知每日证据明确保持部分或未知，不变成文件窗口错误。机会门槛仍排除此类不完整报告。

Maximum upload size is 5 MiB, maximum expanded XLSX ZIP contents are 50 MiB, and maximum nonblank data rows are 10,000. Preview shows at most 100 errors and 10 valid samples. Complete row counts still cover the entire accepted-size file; one row can have several errors, so the number of displayed errors is not the number of invalid rows.
最大上传大小为 5 MiB，解压后 XLSX ZIP 内容最大为 50 MiB，非空白数据行最多为 10,000。预览最多显示 100 个错误与 10 个有效样本。完整行数统计仍覆盖大小合规的整个文件；一行可能有多个错误，因此显示的错误数量不等于无效行数。

## Privacy, tests, and current limits / 隐私、测试与当前限制

Uploads are read in memory or framework-managed ephemeral upload storage; the application does not save source files permanently. Real exports and scratch data must remain outside Git. Automated CSV/XLSX fixtures are generated with synthetic URLs and metrics, not copied from a private export. Protect the local environment: authentication, authorization, production upload hardening, and production deployment are outside this phase.
上传文件通过内存或框架管理的临时上传存储读取；应用不会永久保存源文件。真实导出与临时数据必须留在 Git 之外。自动化 CSV/XLSX 测试数据使用合成 URL 与指标生成，不从私人导出复制。请保护本地环境：身份认证、权限控制、生产上传加固与生产部署不属于本阶段。

Apply head migration `0004_report_scope` before using the importer. It preserves all five earlier tables, current values, timestamps, and provenance links without inferring legacy site/scope/coverage. Observed bounds alone do not certify complete coverage; explicit scope does not authenticate property access or prove complete page exports. Unknown-date observations cannot form period comparisons. Blank carry-forward and older reports applied later remain valid. See [report-scope.md](report-scope.md), [current-provenance.md](current-provenance.md), and [performance-history.md](performance-history.md).
使用导入器前请应用最新迁移 `0004_report_scope`。它保留此前五个表、当前值、时间戳与来源关联，不推断旧站点、范围或覆盖。仅有已观察范围不证明完整覆盖；明确范围不认证属性访问，也不证明完整页面导出。未知日期观察不能构成时间段对比。空白沿用及较早报告后来应用仍有效。详见 [report-scope.md](report-scope.md)、[current-provenance.md](current-provenance.md) 与 [performance-history.md](performance-history.md)。

Phase 5 extends the same transaction to provenance. Each supplied non-`NULL` field, including zero and unchanged numeric values, points to this import's snapshot. Blanks keep both value and source; legacy unknown provenance stays unknown. Identical bytes and canonical scope return the original run and change neither values nor links. Page, run, snapshot, or provenance failure rolls back the whole import. Counts still describe numeric page changes, so source refresh can occur on a skipped same-value page.
第五阶段将同一事务扩展至来源。每个提供的非 `NULL` 字段，包括零及未变化数值，都指向本次导入快照。空白同时保留值及来源；未知旧来源保持未知。相同字节及规范范围返回原导入，不改变值或关联。页面、导入、快照或来源失败回滚整个导入。计数仍描述页面数值变化，因此来源刷新可发生在相同值的跳过页面上。

A `blocking` historical quality observation means comparison evidence is unavailable, without invalidating a successful import. Current provenance observations remain separate from comparison readiness and are not persisted. See [data-quality.md](data-quality.md) and [current-provenance.md](current-provenance.md).
`blocking` 历史质量观察表示对比证据不可用，不否定成功导入。当前来源观察保持独立于对比就绪度，不持久化。详见 [data-quality.md](data-quality.md) 与 [current-provenance.md](current-provenance.md)。

Phase 7 adds a separate read-only runtime [Opportunity Engine](opportunity-engine.md) consuming selected historical comparison and readiness. Phase 8 validates recognized custom 28-day labels and separately [prioritizes existing candidates](opportunity-prioritization.md), without changing import persistence, duplicates, scope, coverage extraction, or provenance. The importer never generates or stores candidates. Weekly latest-28-day reports generally overlap; independent opportunities require two non-overlapping complete reports under matching full scope. Scores, recommendations, AI, integrations, and execution remain unimplemented.
第七阶段增加独立只读运行时[机会引擎](opportunity-engine.md)，使用所选历史对比及就绪度。第八阶段校验已识别自定义 28 天标签，并独立为[已有候选分配优先级](opportunity-prioritization.md)，不改变导入持久化、重复、范围、覆盖提取或来源。导入器绝不生成或存储候选。每周最近 28 天报告通常重叠；独立机会要求相同完整范围下两个互不重叠且完整的报告。评分、建议、AI、集成及执行仍未实现。
