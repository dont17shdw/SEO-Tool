import {
  formatCoverage, formatFilter, SEARCH_TYPE_LABELS,
  type DateCoverage, type ReportScope, type ScopeDeclaration,
} from "@/lib/report-scope";
import { scopeIssueLabel } from "@/lib/zh-cn";

const UNKNOWN = "未知";

function ScopeEvidence({ declaration, workbook = false }: { declaration: ScopeDeclaration; workbook?: boolean }) {
  return (
    <dl className="mapping-list">
      <div><dt>GSC 属性</dt><dd>{declaration.property_id ?? UNKNOWN}</dd></div>
      <div><dt>搜索类型</dt><dd>{declaration.search_type ? SEARCH_TYPE_LABELS[declaration.search_type] : UNKNOWN}</dd></div>
      <div><dt>非日期筛选</dt><dd>{declaration.filters === null ? UNKNOWN : declaration.filters.length === 0
        ? workbook ? "未观察到受支持的筛选行" : "已明确声明无筛选"
        : declaration.filters.map((filter, index) => <p key={index}>{formatFilter(filter)}</p>)}
        {workbook && <p>仅凭工作簿中的筛选行，无法证明非日期筛选列表完整。</p>}
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
        <div><dt>网站身份</dt><dd>{scope.site_identifier ?? UNKNOWN}</dd></div>
        <div><dt>网站身份状态</dt><dd>{scope.site_identifier ? "已记录属性身份" : UNKNOWN}</dd></div>
        <div><dt>GSC 属性</dt><dd>{scope.property_id ?? UNKNOWN}</dd></div>
        <div><dt>属性身份状态</dt><dd>{scope.property_status === "known" ? "已明确记录" : UNKNOWN}</dd></div>
        <div><dt>搜索类型</dt><dd>{scope.search_type ? SEARCH_TYPE_LABELS[scope.search_type] : UNKNOWN}</dd></div>
        <div><dt>非日期筛选</dt><dd>{scope.filters.length > 0
          ? scope.filters.map((filter, index) => <p key={index}>{formatFilter(filter)}</p>)
          : scope.filters_complete ? "已明确声明无筛选" : UNKNOWN}
          {scope.filters.length > 0 && !scope.filters_complete && <p>已记录以上条件，但完整筛选范围仍未知。</p>}
        </dd></div>
        <div><dt>报告范围</dt><dd>{scope.status === "known" ? "已明确记录" : UNKNOWN}</dd></div>
        <div><dt>日期覆盖</dt><dd>{formatCoverage(coverage)}</dd></div>
        {coverage.dates_consecutive !== null && <div><dt>已观察日期是否连续</dt><dd>{coverage.dates_consecutive ? "是" : "否"}</dd></div>}
      </dl>
      {scope.issues.length > 0 && <div className="notice">
        <p>范围证据存在以下限制：</p>
        <ul>{scope.issues.map((issue) => <li key={issue}>{scopeIssueLabel(issue)}</li>)}</ul>
        <details><summary>查看范围问题标识</summary><p>{scope.issues.map((issue, index) => <span key={issue}>{index > 0 && "、"}<code>{issue}</code></span>)}</p></details>
      </div>}
      {showEvidence && <details className="quality-details">
        <summary>查看范围证据来源</summary>
        <h3>工作簿观察证据</h3><ScopeEvidence declaration={scope.workbook_observed} workbook />
        <h3>用户声明</h3><ScopeEvidence declaration={scope.user_declared} />
        <p>规范报告范围指纹：<code>{scope.fingerprint}</code></p>
        <p>这些信息记录了工作簿中观察到或用户声明的报告范围，不代表已验证 GSC 属性所有权或数据源准确性。</p>
      </details>}
    </div>
  );
}
