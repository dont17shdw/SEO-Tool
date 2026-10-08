import {
  formatCoverage, formatFilter, SEARCH_TYPE_LABELS,
  type DateCoverage, type ReportScope, type ScopeDeclaration,
} from "@/lib/report-scope";

const UNKNOWN = "Unknown / 未知";

function ScopeEvidence({ declaration, workbook = false }: { declaration: ScopeDeclaration; workbook?: boolean }) {
  return (
    <dl className="mapping-list">
      <div><dt>GSC property / GSC 属性</dt><dd>{declaration.property_id ?? UNKNOWN}</dd></div>
      <div><dt>Search type / 搜索类型</dt><dd>{declaration.search_type ? SEARCH_TYPE_LABELS[declaration.search_type] : UNKNOWN}</dd></div>
      <div><dt>Non-date filters / 非日期筛选</dt><dd>{declaration.filters === null ? UNKNOWN : declaration.filters.length === 0
        ? workbook ? "No supported filter rows observed / 未观察到受支持筛选行" : "Explicitly none / 明确无筛选"
        : declaration.filters.map((filter, index) => <p key={index}>{formatFilter(filter)}</p>)}
        {workbook && <p>Workbook rows alone do not establish a complete filter list. 仅凭工作簿行不能证明完整筛选列表。</p>}
      </dd></div>
    </dl>
  );
}

/**
 * Display recorded scope and coverage without treating declared evidence as verified ownership.
 * 展示已记录范围与覆盖，不将声明证据视为经过验证的所有权。
 */
export function ReportScopeSummary({ scope, coverage, showEvidence = false }: {
  scope: ReportScope;
  coverage: DateCoverage;
  showEvidence?: boolean;
}) {
  return (
    <div className="report-scope" data-scope-status={scope.status} data-coverage-status={coverage.coverage_status}>
      <dl className="mapping-list">
        <div><dt>Site identity / 站点身份</dt><dd>{scope.site_identifier ?? UNKNOWN}</dd></div>
        <div><dt>Site identity status / 站点身份状态</dt><dd>{scope.site_identifier ? "Recorded property identity / 已记录属性身份" : UNKNOWN}</dd></div>
        <div><dt>GSC property / GSC 属性</dt><dd>{scope.property_id ?? UNKNOWN}</dd></div>
        <div><dt>Property identity status / 属性身份状态</dt><dd>{scope.property_status === "known" ? "Explicitly known / 明确已知" : UNKNOWN}</dd></div>
        <div><dt>Search type / 搜索类型</dt><dd>{scope.search_type ? SEARCH_TYPE_LABELS[scope.search_type] : UNKNOWN}</dd></div>
        <div><dt>Non-date filters / 非日期筛选</dt><dd>{scope.filters.length > 0
          ? scope.filters.map((filter, index) => <p key={index}>{formatFilter(filter)}</p>)
          : scope.filters_complete ? "Explicitly none / 明确无筛选" : UNKNOWN}
          {scope.filters.length > 0 && !scope.filters_complete && <p>Complete filter scope unknown / 完整筛选范围未知</p>}
        </dd></div>
        <div><dt>Report scope / 报告范围</dt><dd>{scope.status === "known" ? "Explicitly known / 明确已知" : UNKNOWN}</dd></div>
        <div><dt>Date coverage / 日期覆盖</dt><dd>{formatCoverage(coverage)}</dd></div>
        {coverage.dates_consecutive !== null && <div><dt>Observed dates consecutive / 已观察日期连续</dt><dd>{coverage.dates_consecutive ? "Yes / 是" : "No / 否"}</dd></div>}
      </dl>
      {scope.issues.length > 0 && <p className="notice">Scope evidence caveats / 范围证据限制：{scope.issues.join(", ")}</p>}
      {showEvidence && <details className="quality-details">
        <summary>Scope evidence origins / 范围证据来源</summary>
        <h3>Workbook-observed / 工作簿已观察</h3><ScopeEvidence declaration={scope.workbook_observed} workbook />
        <h3>User-declared / 用户声明</h3><ScopeEvidence declaration={scope.user_declared} />
        <p>Canonical scope fingerprint / 规范范围指纹：<code>{scope.fingerprint}</code></p>
        <p>Scope records observed or declared metadata. It does not verify property ownership or source accuracy. 范围记录已观察或已声明的元数据，不验证属性所有权或数据源准确性。</p>
      </details>}
    </div>
  );
}
