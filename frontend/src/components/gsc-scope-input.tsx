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
      <legend>Optional user-declared report scope / 可选的用户声明报告范围</legend>
      <p>Enter only metadata you know from this export. Blank fields remain unknown. Workbook evidence will be shown separately in preview; conflicting declarations are rejected. 仅填写您明确知道属于此导出的元数据。空白字段保持未知。预览将单独显示工作簿证据；冲突声明会被拒绝。</p>
      <label className="field-label" htmlFor="gsc-property">GSC property identifier / GSC 属性标识符</label>
      <input id="gsc-property" type="text" value={scope.property_id ?? ""} placeholder="sc-domain:example.com or https://example.com/"
        autoComplete="off" onChange={(event) => onChange({ ...scope, property_id: event.target.value || null })} />
      <p><small>Use an explicit Domain property or URL-prefix property. Site identity follows this recorded property; page URLs and filenames do not establish it. 使用明确的网域属性或网址前缀属性。站点身份跟随该已记录属性；页面 URL 与文件名不能证明身份。</small></p>
      <label className="field-label" htmlFor="gsc-search-type">Search type / 搜索类型</label>
      <select id="gsc-search-type" value={scope.search_type ?? ""}
        onChange={(event) => onChange({ ...scope, search_type: event.target.value ? event.target.value as ScopeDeclaration["search_type"] : null })}>
        <option value="">Unknown / 未知</option>
        {Object.entries(SEARCH_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <label className="checkbox-label">
        <input id="gsc-filters-complete" type="checkbox" checked={scope.filters !== null}
          onChange={(event) => onChange({ ...scope, filters: event.target.checked ? [] : null })} />
        <span>I can declare the complete non-date filter list. An empty list explicitly means no non-date filters. 我可以声明完整的非日期筛选列表。空列表明确表示没有非日期筛选。</span>
      </label>
      {scope.filters === null ? <p>Complete non-date filter scope remains unknown until you explicitly declare the complete list. 完整非日期筛选范围保持未知，直到您明确声明完整列表。</p> : (
        <>
          {filters.length === 0 && <p>No non-date filters declared / 已声明无非日期筛选</p>}
          {filters.map((filter, index) => {
            const textDimension = filter.dimension === "query" || filter.dimension === "page";
            return (
              <div className="scope-filter" key={index}>
                <label>Dimension / 维度
                  <select aria-label={`Filter ${index + 1} dimension / 筛选 ${index + 1} 维度`} value={filter.dimension}
                    onChange={(event) => updateFilter(index, { dimension: event.target.value as ScopeFilter["dimension"], operator: "equals", value: "" })}>
                    {dimensions.filter((dimension) => dimension === filter.dimension || !filters.some((item) => item.dimension === dimension))
                      .map((dimension) => <option key={dimension} value={dimension}>{FILTER_DIMENSION_LABELS[dimension]}</option>)}
                  </select>
                </label>
                <label>Operator / 运算符
                  <select aria-label={`Filter ${index + 1} operator / 筛选 ${index + 1} 运算符`} value={filter.operator}
                    onChange={(event) => updateFilter(index, { operator: event.target.value as ScopeFilter["operator"] })}>
                    {Object.entries(FILTER_OPERATOR_LABELS).filter(([operator]) => textDimension || ["equals", "not_equals"].includes(operator))
                      .map(([operator, label]) => <option key={operator} value={operator}>{label}</option>)}
                  </select>
                </label>
                <label>Value / 值
                  {filter.dimension === "device" ? (
                    <select aria-label={`Filter ${index + 1} value / 筛选 ${index + 1} 值`} value={filter.value}
                      onChange={(event) => updateFilter(index, { value: event.target.value })}>
                      <option value="">Select device / 选择设备</option>
                      <option value="mobile">Mobile / 移动设备</option><option value="desktop">Desktop / 桌面设备</option><option value="tablet">Tablet / 平板设备</option>
                    </select>
                  ) : <input type="text" aria-label={`Filter ${index + 1} value / 筛选 ${index + 1} 值`} value={filter.value}
                    placeholder={filter.dimension === "country" ? "USA / CHN" : filter.dimension === "search_appearance" ? "product_snippets" : ""} onChange={(event) => updateFilter(index, { value: event.target.value })} />}
                </label>
                <button type="button" onClick={() => onChange({ ...scope, filters: filters.filter((_, position) => position !== index) })}
                  aria-label={`Remove filter ${index + 1} / 移除筛选 ${index + 1}`}>Remove / 移除</button>
              </div>
            );
          })}
          <button type="button" disabled={filters.length >= dimensions.length} onClick={() => {
            const dimension = dimensions.find((candidate) => !filters.some((filter) => filter.dimension === candidate));
            if (dimension) onChange({ ...scope, filters: [...filters, { dimension, operator: "equals", value: "" }] });
          }}>Add non-date filter / 添加非日期筛选</button>
        </>
      )}
      <p><small>Changing any declaration invalidates the preview and requires previewing again. 更改任何声明都会使预览失效，需要重新预览。</small></p>
    </fieldset>
  );
}
