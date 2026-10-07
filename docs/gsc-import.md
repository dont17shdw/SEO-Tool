# GSC Pages import / GSC 网页导入

## Supported source / 支持的数据源

Phase 2 accepts one source: the Google Search Console Pages performance export for the **latest 28 days**, uploaded manually as `.csv` or `.xlsx`. It does not import search queries, countries, devices, dates, search appearance, or indexing reports. English and Chinese localized page exports are supported.
第二阶段接受一种数据源：Google Search Console **最近 28 天**网页性能导出，手动上传 `.csv` 或 `.xlsx`。不导入搜索查询、国家、设备、日期、搜索结果呈现或索引报告。支持英文与中文本地化的网页导出。

CSV must be UTF-8, with or without a BOM. Comma, semicolon, and tab delimiters are supported. The first nonblank row is the header. Blank rows are ignored; row-level errors retain the original source row numbers.
CSV 必须使用 UTF-8，可包含或不包含 BOM。支持逗号、分号及制表符分隔。首个非空行为表头。空白行会被忽略；行级错误保留源文件中的原始行号。

XLSX uses `openpyxl` in read-only mode. Formula cells are not evaluated; metric formulas fail validation rather than silently becoming missing values. Prefer the case-insensitive `Pages` worksheet, then `网页`. If neither exists, accept only one worksheet with all recognized page-performance headers and at least one valid absolute HTTP(S) URL in the page dimension. Known unrelated worksheet names are excluded even if their metric columns resemble page metrics. Multiple matching fallback sheets are rejected; name the intended one `Pages` or `网页`.
XLSX 使用 `openpyxl` 只读模式。不计算公式单元格；指标公式会导致校验失败，不会静默变为缺失值。优先选择不区分大小写的 `Pages` 工作表，其次选择 `网页`。两者均不存在时，仅接受同时具有全部已识别网页性能列名，且网页维度至少包含一个有效绝对 HTTP(S) URL 的唯一工作表。已知的无关工作表名称会被排除，即使其指标列与网页指标相似。多个匹配的回退工作表会被拒绝；请将目标表命名为 `Pages` 或 `网页`。

Recognized filter worksheets are `Filters`, `Filter`, and `过滤器`. Their `Date`, `Dates`, `Date range`, or `日期` entries must use a supported latest-28-day label: `Last 28 days`, `Past 28 days`, `28 days`, `过去 28 天`, or `最近 28 天` (case and spacing variations are accepted). A conflicting nonblank date label is rejected. If date metadata is absent or blank, including CSV, the documented latest-28-day assumption applies: the user must choose that date filter before export. Custom date ranges are not interpreted.
识别的筛选工作表为 `Filters`、`Filter` 与 `过滤器`。其中 `Date`、`Dates`、`Date range` 或 `日期` 条目必须使用受支持的最近 28 天标签：`Last 28 days`、`Past 28 days`、`28 days`、`过去 28 天` 或 `最近 28 天`（允许大小写与空白差异）。冲突的非空日期标签会被拒绝。日期元数据缺失或为空时，包括 CSV，采用文档约定的最近 28 天假设：用户必须在导出前选择该日期筛选。不解释自定义日期范围。

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

1. Select a CSV/XLSX file at `/imports/gsc` and request preview.
   在 `/imports/gsc` 选择 CSV/XLSX 文件并请求预览。
2. Inspect detected source, reporting window, XLSX sheet, counts, mapping, errors, and sample normalized rows. Preview does not use PostgreSQL or persist any records.
   检查识别的数据源、报告窗口、XLSX 工作表、统计、映射、错误及标准化样本。预览不使用 PostgreSQL，也不持久化任何记录。
3. Correct errors in the source file and preview again if necessary.
   必要时修正源文件错误并重新预览。
4. Explicitly confirm import. The browser resubmits the selected file with `confirmed=true` and its preview hash. Changing the file invalidates the earlier preview.
   显式确认导入。浏览器再次提交选中的文件，并附带 `confirmed=true` 与预览哈希。更改文件会使此前预览失效。
5. The backend reparses and revalidates the complete file, checks the SHA-256 fingerprint, and persists it transactionally. Then review the result and open `/pages`.
   后端重新解析并校验完整文件，检查 SHA-256 指纹，并在事务中持久化。然后查看结果并打开 `/pages`。

No server-side preview session is stored. Normalized client-side rows are never accepted as the persistence source. The fingerprint provides file consistency, not authentication or an audit record.
不存储服务端预览会话。客户端标准化行不会被接受为持久化数据源。指纹用于保证文件一致性，不是身份认证或审计记录。

## Persistence / 持久化

Upsert `WebsitePage` by exact trimmed URL. Create a missing page using only supplied GSC values; unspecified nullable fields stay `NULL`. For an existing page, update only nonblank supplied `clicks_28d`, `impressions_28d`, `ctr`, and `average_position`. Blank incoming metrics preserve stored values, while measured zeros overwrite them. Unchanged existing pages count as skipped. Non-GSC fields, other reporting periods, and opportunities are preserved.
按去除前后空白后的精确 URL 新增或更新 `WebsitePage`。新页面仅使用已提供的 GSC 值；未指定的可空字段保持 `NULL`。已有页面仅更新已提供且非空白的 `clicks_28d`、`impressions_28d`、`ctr` 与 `average_position`。传入空白指标保留已存储值，测得的零则覆盖它们。未变化的已有页面计为跳过。非 GSC 字段、其他报告时间段与机会记录均保留。

All validated rows are committed in one transaction. PostgreSQL URL uniqueness resolves concurrent insert conflicts; existing rows are locked while supplied metrics are updated. Unexpected database failures roll back all changes. There is no partial valid-row import, delete operation, or automatic recommendation.
全部已校验行在一个事务内提交。PostgreSQL URL 唯一性处理并发插入冲突；更新已提供指标时会锁定已有行。意外数据库失败会回滚全部变更。没有仅导入有效行的部分导入、删除操作或自动建议。

## API contract / API 契约

Both upload endpoints accept `multipart/form-data`. Run the following from a directory containing a synthetic or privately held `gsc-pages.csv`; do not commit source uploads.
两个上传接口均接受 `multipart/form-data`。在包含合成或私下保存的 `gsc-pages.csv` 的目录中运行以下命令；不要提交源上传文件。

```sh
curl -X POST http://localhost:8000/api/v1/imports/gsc/pages/preview \
  -F 'file=@gsc-pages.csv'
```

The preview response includes `source="gsc_pages"`, `reporting_window="latest_28_days"`, `detected_sheet` (`null` for CSV), `total_rows`, `valid_rows`, `invalid_rows`, `duplicate_rows`, `column_mapping`, `errors`, `sample_rows`, `can_apply`, and `preview_hash`. Each error has `row`, `field`, `code`, and a human-readable `message`. Samples include source `row`, `url`, and the four normalized GSC fields. Decimal fields serialize as JSON strings, for example `"0.025000"`; missing metrics serialize as `null`.
预览响应包含 `source="gsc_pages"`、`reporting_window="latest_28_days"`、`detected_sheet`（CSV 为 `null`）、`total_rows`、`valid_rows`、`invalid_rows`、`duplicate_rows`、`column_mapping`、`errors`、`sample_rows`、`can_apply` 与 `preview_hash`。每个错误包含 `row`、`field`、`code` 及易理解的 `message`。样本包含源 `row`、`url` 及四个标准化 GSC 字段。小数字段序列化为 JSON 字符串，例如 `"0.025000"`；缺失指标序列化为 `null`。

Replace the placeholder below with the exact 64-character lowercase hexadecimal hash returned by preview:
将下方占位符替换为预览返回的准确 64 位小写十六进制哈希：

```sh
curl -X POST http://localhost:8000/api/v1/imports/gsc/pages/apply \
  -F 'file=@gsc-pages.csv' \
  -F 'confirmed=true' \
  -F 'preview_hash=REPLACE_WITH_PREVIEW_HASH'
```

Success returns `created_count`, `updated_count`, `skipped_count`, and `error_count` (`0` after a successful atomic import). A failed operation returns an HTTP error instead of reporting partial success.
成功时返回 `created_count`、`updated_count`、`skipped_count` 与 `error_count`（成功的原子导入后为 `0`）。失败操作返回 HTTP 错误，不会报告部分成功。

```sh
curl 'http://localhost:8000/api/v1/pages?page=1&page_size=50'
```

The page list returns `items`, `page`, `page_size`, `total`, and `total_pages`. Items contain `id`, `url`, `clicks_28d`, `impressions_28d`, `ctr`, and `average_position`. `page` starts at 1; `page_size` defaults to 50 and must be 1–100. Ordering is stable by `created_at`, then `id`. An empty database has `total_pages=0`; a page beyond the end returns empty `items`. This is offset pagination, without a consistent snapshot across simultaneous imports.
页面列表返回 `items`、`page`、`page_size`、`total` 与 `total_pages`。条目包含 `id`、`url`、`clicks_28d`、`impressions_28d`、`ctr` 与 `average_position`。`page` 从 1 开始；`page_size` 默认 50，必须位于 1–100。按 `created_at`、其次 `id` 保持稳定排序。空数据库的 `total_pages=0`；超出末页的页面返回空 `items`。这是偏移量分页，不提供跨并发导入的一致快照。

## Errors and resource limits / 错误与资源限制

| HTTP status / 状态 | Meaning / 含义 |
| --- | --- |
| `200` | Preview available, including row errors; or apply/list succeeded.<br>预览可用，包括行错误；或应用、列表成功。 |
| `422` | Unsupported/empty/malformed file, missing or ambiguous columns/sheets, conflicting reporting window, invalid form, missing confirmation, or blocked apply.<br>不支持、为空或损坏的文件，缺失或歧义列、工作表，冲突的报告窗口，无效表单，缺少确认或被阻止的应用。 |
| `409` | Submitted file differs from the preview; preview it again.<br>提交文件与预览不同；请重新预览。 |
| `413` | Upload, expanded XLSX, or row limit exceeded.<br>超出上传、解压后 XLSX 或行数限制。 |
| `503` | Database operation failed; no partial import is committed.<br>数据库操作失败；不会提交部分导入。 |

File errors use `detail.code` and `detail.message`; invalid form/query parameters use FastAPI validation details. Internal reader exceptions and database stack traces are not returned. Row-level errors remain in a successful preview response so the user can inspect and correct them.
文件错误使用 `detail.code` 与 `detail.message`；无效表单或查询参数使用 FastAPI 校验详情。不会返回内部读取器异常或数据库堆栈。行级错误保留在成功的预览响应中，以便用户检查并修正。

Maximum upload size is 5 MiB, maximum expanded XLSX ZIP contents are 50 MiB, and maximum nonblank data rows are 10,000. Preview shows at most 100 errors and 10 valid samples. Complete row counts still cover the entire accepted-size file; one row can have several errors, so the number of displayed errors is not the number of invalid rows.
最大上传大小为 5 MiB，解压后 XLSX ZIP 内容最大为 50 MiB，非空白数据行最多为 10,000。预览最多显示 100 个错误与 10 个有效样本。完整行数统计仍覆盖大小合规的整个文件；一行可能有多个错误，因此显示的错误数量不等于无效行数。

## Privacy, tests, and current limits / 隐私、测试与当前限制

Uploads are read in memory or framework-managed ephemeral upload storage; the application does not save source files permanently. Real exports and scratch data must remain outside Git. Automated CSV/XLSX fixtures are generated with synthetic URLs and metrics, not copied from a private export. Protect the local environment: authentication, authorization, production upload hardening, and production deployment are outside this phase.
上传文件通过内存或框架管理的临时上传存储读取；应用不会永久保存源文件。真实导出与临时数据必须留在 Git 之外。自动化 CSV/XLSX 测试数据使用合成 URL 与指标生成，不从私人导出复制。请保护本地环境：身份认证、权限控制、生产上传加固与生产部署不属于本阶段。

No schema migration is needed beyond the Phase 1 migration. The model stores only current supplied metrics, without import history, date anchors, per-site ownership, or metric snapshots. Blank metric updates intentionally preserve previous values, so a record can contain observations from different uploads. This cannot support historical trend claims or prove that a metadata-free file actually covers 28 days. See [data-model.md](data-model.md) for these persistence limits.
第一阶段迁移之外无需新增数据库迁移。模型仅存储当前提供的指标，没有导入历史、日期基准、站点归属或指标快照。空白指标更新有意保留此前值，因此记录可能包含不同上传的观察结果。这不能支持历史趋势结论，也不能证明没有元数据的文件确实覆盖 28 天。持久化限制详见 [data-model.md](data-model.md)。

Phase 2 contains no SEO analysis, scoring, opportunities, recommendations, AI, GSC API integration, query import, editing/deletion, background jobs, or execution. Phase 3 has not started.
第二阶段不包含 SEO 分析、评分、机会、建议、AI、GSC API 集成、查询导入、编辑删除、后台任务或执行。第三阶段尚未开始。
