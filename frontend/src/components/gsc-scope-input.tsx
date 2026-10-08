import {
  FILTER_DIMENSION_LABELS, FILTER_OPERATOR_LABELS, SEARCH_TYPE_LABELS,
  type ScopeDeclaration, type ScopeFilter,
} from "@/lib/report-scope";

/**
 * Collect explicit declarations while keeping blank identity and unconfirmed filter scope unknown.
 * 收集明确声明，同时将空白身份及未确认的筛选范围保持为未知。
 */
export function GscScopeInput({ scope, onChange, disabled }: {
  scope: ScopeDeclaration;
  onChange: (scope: ScopeDeclaration) => void;
  disabled: boolean;
}) {
  const filters = scope.filters ?? [];
  const dimensions = Object.keys(FILTER_DIMENSION_LABELS) as ScopeFilter["dimension"][];

  function updateFilter(index: number, change: Partial<ScopeFilter>) {
    onChange({ ...scope, filters: filters.map((filter, position) => position === index ? { ...filter, ...change } : filter) });
  }

  return (
    <fieldset className="scope-input" disabled={disabled}>
      <legend>报告范围声明（可选）</legend>
      <p>请只填写您明确知道属于本次导出的信息。空白字段保持未知。预览会分别展示工作簿观察证据和您的声明；两者冲突时会阻止导入。</p>
      <label className="field-label" htmlFor="gsc-property">GSC 属性标识</label>
      <input id="gsc-property" type="text" value={scope.property_id ?? ""} placeholder="sc-domain:example.com 或 https://example.com/" aria-describedby="gsc-property-help"
        autoComplete="off" onChange={(event) => onChange({ ...scope, property_id: event.target.value || null })} />
      <p id="gsc-property-help"><small>请填写网域属性或网址前缀属性。网站身份以记录的 GSC 属性为依据，页面 URL 或文件名不能证明网站身份。</small></p>
      <label className="field-label" htmlFor="gsc-search-type">搜索类型</label>
      <select id="gsc-search-type" value={scope.search_type ?? ""}
        onChange={(event) => onChange({ ...scope, search_type: event.target.value ? event.target.value as ScopeDeclaration["search_type"] : null })}>
        <option value="">未知</option>
        {Object.entries(SEARCH_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <label className="checkbox-label">
        <input id="gsc-filters-complete" type="checkbox" checked={scope.filters !== null} aria-describedby="gsc-filters-help"
          onChange={(event) => onChange({ ...scope, filters: event.target.checked ? [] : null })} />
        <span>我能完整声明本报告使用的非日期筛选条件；勾选后不添加条件，表示明确声明没有非日期筛选。</span>
      </label>
      <p id="gsc-filters-help">只有明确声明完整列表，才能确认非日期筛选范围。工作簿中观察到的部分筛选行不能证明列表完整。</p>
      {scope.filters === null ? <p>尚未声明完整的非日期筛选条件，筛选范围保持未知。</p> : (
        <>
          {filters.length === 0 && <p>已声明没有非日期筛选条件。</p>}
          {filters.map((filter, index) => {
            const textDimension = filter.dimension === "query" || filter.dimension === "page";
            return (
              <div className="scope-filter" key={index}>
                <label>筛选维度
                  <select aria-label={`第 ${index + 1} 项筛选的维度`} value={filter.dimension}
                    onChange={(event) => updateFilter(index, { dimension: event.target.value as ScopeFilter["dimension"], operator: "equals", value: "" })}>
                    {dimensions.filter((dimension) => dimension === filter.dimension || !filters.some((item) => item.dimension === dimension))
                      .map((dimension) => <option key={dimension} value={dimension}>{FILTER_DIMENSION_LABELS[dimension]}</option>)}
                  </select>
                </label>
                <label>匹配方式
                  <select aria-label={`第 ${index + 1} 项筛选的匹配方式`} value={filter.operator}
                    onChange={(event) => updateFilter(index, { operator: event.target.value as ScopeFilter["operator"] })}>
                    {Object.entries(FILTER_OPERATOR_LABELS).filter(([operator]) => textDimension || ["equals", "not_equals"].includes(operator))
                      .map(([operator, label]) => <option key={operator} value={operator}>{label}</option>)}
                  </select>
                </label>
                <label>筛选值
                  {filter.dimension === "device" ? (
                    <select aria-label={`第 ${index + 1} 项筛选的值`} value={filter.value}
                      onChange={(event) => updateFilter(index, { value: event.target.value })}>
                      <option value="">请选择设备</option>
                      <option value="mobile">移动设备</option><option value="desktop">桌面设备</option><option value="tablet">平板设备</option>
                    </select>
                  ) : <input type="text" aria-label={`第 ${index + 1} 项筛选的值`} value={filter.value}
                    placeholder={filter.dimension === "country" ? "例如：CHN、USA" : filter.dimension === "search_appearance" ? "例如：product_snippets" : ""} onChange={(event) => updateFilter(index, { value: event.target.value })} />}
                </label>
                <button type="button" onClick={() => onChange({ ...scope, filters: filters.filter((_, position) => position !== index) })}
                  aria-label={`移除第 ${index + 1} 项筛选`}>移除</button>
              </div>
            );
          })}
          <button type="button" disabled={filters.length >= dimensions.length} onClick={() => {
            const dimension = dimensions.find((candidate) => !filters.some((filter) => filter.dimension === candidate));
            if (dimension) onChange({ ...scope, filters: [...filters, { dimension, operator: "equals", value: "" }] });
          }}>添加非日期筛选</button>
        </>
      )}
      <p><small>更改任何声明都会使当前预览和导入确认失效，请重新预览。</small></p>
    </fieldset>
  );
}
