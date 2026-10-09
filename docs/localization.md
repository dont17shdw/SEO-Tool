# MVP Simplified Chinese presentation
# MVP 简体中文展示

## Scope and architecture boundary
## 范围与架构边界

The MVP user interface has one required language: Simplified Chinese (`zh-CN`). Navigation, imports, history, comparisons, data quality, metric provenance, opportunities, priority tiers, form help, accessibility labels, and common feedback use Chinese. No language switcher, internationalization framework, or new reporting export is introduced.
MVP 用户界面仅要求支持一种语言：简体中文（`zh-CN`）。导航、导入、历史、周期对比、数据质量、指标来源、SEO 机会、优先级、表单说明、无障碍标签及常见操作反馈统一使用中文。不引入语言切换器、国际化框架或新的报告导出功能。

Localization belongs to frontend presentation. Backend API paths, field names, response schemas, stable codes, database models, and Alembic migrations retain their existing identities. GSC parsing, normalization, scope validation, duplicate handling, transactional persistence, comparison selection, readiness, provenance, opportunity detection, priority thresholds, filtering, and candidate-based pagination retain their Phase 1–8 behavior.
本地化属于前端展示职责。后端 API 路径、字段名、响应结构、稳定代码、数据库模型及 Alembic 迁移保持原有身份。GSC 解析、标准化、范围校验、重复处理、事务持久化、对比选择、就绪度、来源追踪、机会检测、优先级阈值、筛选及按候选分页保持第一至八阶段的行为。

There are no backend presentation changes, database migrations, AI calls, recommendations, opportunity persistence, production deployment, or changes to real SEO data in this task. Important technical documentation and non-trivial code comments remain bilingual, English first and Chinese second; this convention is separate from the Chinese-only user interface.
本次任务不包含后端展示变更、数据库迁移、AI 调用、建议生成、机会持久化、生产部署或真实 SEO 数据修改。重要技术文档及非简单代码注释仍使用英文在前、中文在后的双语形式；这一约定与仅使用中文的用户界面分别适用。

## Messages and factual analysis
## 文案与事实分析

A small centralized frontend label and message mapping keeps repeated concepts consistent. Known observation and reason codes select Chinese explanations using their structured evidence. Bilingual backend prose is not split at `/`; that character may belong to a URL or an exact numerical ratio. An unknown code receives a conservative Chinese fallback without inventing a cause, threshold result, or recommended action.
轻量集中式前端标签与文案映射保持重复概念的一致性。已知观察代码及原因代码根据对应结构化证据选择中文解释。不按 `/` 拆分后端双语文本，因为该字符可能属于 URL 或准确数值比率。未知代码使用审慎的中文兜底，不编造原因、阈值判断或建议行动。

Priority views display the backend-supplied tier, `priority-v1` version, reason code, inputs, and thresholds. The browser does not re-evaluate opportunity rules or recalculate High/Medium/Low tiers. A priority tier describes the existing attention heuristic; it does not guarantee business value, establish causation, or predict recovery.
优先级视图展示后端提供的层级、`priority-v1` 版本、原因代码、输入值及阈值。浏览器不重新判断机会规则，也不重新计算高、中、低优先级。优先级描述已有的关注启发式规则，不保证商业价值、不证明原因，也不预测恢复效果。

Workbook-observed scope facts remain distinct from user declarations. Unknown scope or incomplete observed date coverage is explained as a limitation rather than presented as verified evidence. Existing import preview and explicit Apply confirmation requirements remain in place.
工作簿观察到的范围事实与用户声明保持区分。未知范围或不完整的已观察日期覆盖会说明为限制，不会展示为已验证证据。原有导入预览及明确确认后应用的要求保持不变。

## Measurements and technical details
## 指标与技术详情

Metric labels and units are Chinese. CTR values are percentages, while absolute CTR changes are percentage points. A larger average-position number indicates worse ranking. The presentation uses supplied differences and evidence rather than deriving new analytical results.
指标标签与单位使用中文。点击率（CTR）数值使用百分比，而点击率绝对变化使用百分点。平均排名数值越大表示排名越靠后。展示使用已有差值与证据，不推导新的分析结果。

Reporting-period dates retain their exact source date values. Import timestamps use Chinese presentation in the browser's existing timezone without changing the stored timestamp. Exact metrics, thresholds, source snapshot identities, and integer ratio strings remain available in evidence details; localization does not substitute translated data for stored values.
报告周期日期保留准确的来源日期值。导入时间在浏览器现有时区中采用中文展示，不修改已存储时间戳。准确指标、阈值、来源快照身份及整数比率字符串仍可在证据详情中查看；本地化不会用翻译后的数据替代存储值。

SEO, GSC, CTR, URL, UUID, CSV, XLSX, API, and other useful technical abbreviations may remain English. Actual URLs, filenames, original workbook sheet/header names, UUIDs, API paths, rule versions, machine-readable codes, and raw evidence keys remain unchanged when shown as source data or diagnostic details. Their surrounding headings and explanations are Chinese.
SEO、GSC、CTR、URL、UUID、CSV、XLSX、API 等有用技术缩写可以保留英文。实际 URL、文件名、原始工作簿工作表及列名、UUID、API 路径、规则版本、机器代码及原始证据键作为来源数据或诊断详情展示时保持不变。对应标题与说明使用中文。

## Errors, empty states, and accessibility
## 错误、空状态与无障碍

Common import, request, response, filter, and pagination failures use understandable Chinese feedback. Unrecognized backend errors use safe messages instead of exposing raw server prose, stack traces, credentials, private paths, or database internals. Stable diagnostic codes can remain available where useful.
常见导入、请求、响应、筛选及分页失败使用易于理解的中文反馈。无法识别的后端错误采用安全文案，不暴露原始服务端文本、堆栈、凭据、私有路径或数据库内部信息。在有助于诊断时可以保留稳定错误代码。

Empty states distinguish no imports, unavailable comparison evidence, insufficient readiness, eligible pages without detected signals, and filters without matching candidates. Chinese labels, browser language metadata, keyboard interaction, form associations, wrapping, and horizontally scrollable tables support the existing restrained interface across desktop, tablet, and mobile widths.
空状态区分尚无导入、缺少对比证据、证据不足、具备资格但未检测到信号，以及筛选条件下没有匹配候选。中文标签、浏览器语言元数据、键盘操作、表单关联、换行及可横向滚动的表格共同支持现有简洁界面在桌面、平板及手机宽度下使用。

## Validation and next milestone
## 验证与下一里程碑

Localization validation covers frontend lint, TypeScript checks, production build, and synthetic browser workflows for import preview/apply, errors, history, readiness, provenance, all four opportunity types, all three priority tiers, filters, candidate pagination, empty states, unavailable backend, accessibility, and narrow layouts. Existing regression checks verify that numerical evidence, reporting dates, source identities, eligibility, and tiers are unchanged. Private exports and browser artifacts are not committed as fixtures.
本地化验证覆盖前端 lint、TypeScript 检查、生产构建，以及导入预览与应用、错误、历史、就绪度、来源、全部四种机会类型、全部三个优先级、筛选、按候选分页、空状态、后端不可用、无障碍及窄屏布局的合成浏览器流程。已有回归检查用于验证数值证据、报告日期、来源身份、检测资格及层级保持不变。私有导出及浏览器产物不会作为测试数据提交。

Validation completed on 2026-10-08: all 826 backend tests passed against PostgreSQL; Ruff checks, frontend lint, TypeScript checks, and production build passed. All 119 grouped browser checks passed: 13 real-server integration, 37 prioritized-view, 23 neutral-view, 14 Chinese presentation/safety/accessibility, 13 import-validation, and 19 read-only/responsive checks. The six application routes fit 1440, 768, and 390 px viewports. All 38 existing frontend validation functions remained unchanged.
2026-10-08 验证结果：全部 826 项后端测试在 PostgreSQL 上通过；Ruff 检查、前端 lint、TypeScript 检查及生产构建通过。全部 119 项分组浏览器检查通过，包括 13 项真实服务集成、37 项优先级视图、23 项原始信号视图、14 项中文展示与安全及无障碍、13 项导入校验、19 项只读与响应式检查。六个应用页面均适配 1440、768 和 390 像素宽度。原有 38 个前端校验函数保持不变。

Browser imports used only synthetic exports in a disposable PostgreSQL schema with a separate role. Existing public-table row fingerprints remained unchanged, and read-only requests preserved all six isolated application tables. The only recorded incidental issues were the existing backend Starlette/httpx deprecation warning and optional `/favicon.ico` 404; no application JavaScript errors were found.
浏览器导入仅使用合成导出文件，并在具有独立角色的临时 PostgreSQL 架构中执行。已有公共表的行指纹保持不变，只读请求也保留了隔离环境中全部六张应用表的内容。记录到的附带问题仅为原有后端 Starlette/httpx 弃用提示，以及可选的 `/favicon.ico` 404；未发现应用 JavaScript 错误。

The next milestone is an authorized private MVP local trial with real TuffPlus GSC exports. It requires two non-overlapping complete 28-day reports under the same explicit scope, as described in the [existing acceptance procedure](opportunity-prioritization.md#real-tuffplus-acceptance-procedure--真实-tuffplus-验收流程). Synthetic workflow validation is not real-site calibration. Localization does not authorize deployment, production data changes, or Phase 9.
下一里程碑是经授权使用真实 TuffPlus GSC 导出进行私有 MVP 本地试用。按照[已有验收流程](opportunity-prioritization.md#real-tuffplus-acceptance-procedure--真实-tuffplus-验收流程)，需要相同明确范围下两个互不重叠、日期覆盖完整的 28 天报告。合成流程验证不等于真实站点校准。本地化不授权部署、生产数据修改或第九阶段开发。
