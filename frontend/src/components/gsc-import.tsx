"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { PageMetricsTable } from "@/components/page-metrics-table";
import { GscScopeInput } from "@/components/gsc-scope-input";
import { ReportScopeSummary } from "@/components/report-scope-summary";
import { formatPeriod } from "@/lib/history-api";
import { type ScopeDeclaration } from "@/lib/report-scope";
import { fieldLabel, importRowErrorMessage } from "@/lib/zh-cn";
import {
  applyGscFile,
  previewGscFile,
  requestErrorMessage,
  type ImportPreview,
  type ImportResult,
} from "@/lib/gsc-api";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

/**
 * Keep file preview and explicit persistence separate in the development import workflow.
 * 在开发用导入流程中，将文件预览与明确确认后的持久化分开。
 */
export function GscImport() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [scope, setScope] = useState<ScopeDeclaration>({ property_id: null, search_type: null, filters: null });
  const [previewScope, setPreviewScope] = useState<ScopeDeclaration | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [stage, setStage] = useState<"idle" | "previewing" | "applying">("idle");
  const [error, setError] = useState<string | null>(null);
  const requestVersion = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  /**
   * Clear all preview state when the file changes and ignore any older in-flight result.
   * 文件变化时清空全部预览状态，并忽略此前尚未完成的请求结果。
   */
  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    controller.current?.abort();
    requestVersion.current += 1;
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setPreview(null);
    setPreviewScope(null);
    setResult(null);
    setConfirmed(false);
    setStage("idle");
    setError(
      nextFile && !/\.(csv|xlsx)$/i.test(nextFile.name)
        ? "请选择 CSV 或 XLSX 文件。"
        : nextFile && nextFile.size > MAX_FILE_BYTES
          ? "文件超过 5 MiB 上传限制，请选择较小的导出文件。"
          : null,
    );
  }

  /**
   * Invalidate confirmation on every scope edit, including while an earlier preview is pending.
   * 每次范围编辑都使确认失效，包括此前预览请求仍在等待时。
   */
  function updateScope(nextScope: ScopeDeclaration) {
    controller.current?.abort();
    requestVersion.current += 1;
    setScope(nextScope);
    setPreview(null);
    setPreviewScope(null);
    setResult(null);
    setConfirmed(false);
    setStage("idle");
    setError(null);
  }

  /**
   * Preview the retained File without writing records and guard against selection races.
   * 预览保留的 File 而不写入记录，并防止文件选择变化造成请求竞争。
   */
  async function uploadPreview() {
    if (!file || stage !== "idle") return;
    controller.current?.abort();
    const active = new AbortController();
    controller.current = active;
    const version = ++requestVersion.current;
    setPreview(null);
    setPreviewScope(null);
    setResult(null);
    setConfirmed(false);
    setError(null);
    setStage("previewing");
    const submittedScope = structuredClone(scope);
    try {
      const response = await previewGscFile(file, submittedScope, active.signal);
      if (version === requestVersion.current) {
        setPreview(response);
        setPreviewScope(submittedScope);
      }
    } catch (error) {
      if (version === requestVersion.current) setError(requestErrorMessage(error));
    } finally {
      if (version === requestVersion.current) setStage("idle");
    }
  }

  /**
   * Persist only after confirmation, resubmitting the exact File that produced the preview.
   * 仅在明确确认后持久化，重新提交产生当前预览的同一个 File。
   */
  async function importFile() {
    if (!file || !preview?.can_apply || !previewScope || !confirmed || stage !== "idle" || result) return;
    const active = new AbortController();
    controller.current = active;
    const version = ++requestVersion.current;
    setError(null);
    setStage("applying");
    try {
      const response = await applyGscFile(file, preview.preview_hash, previewScope, active.signal);
      if (version === requestVersion.current) {
        setResult(response);
        setConfirmed(false);
      }
    } catch (error) {
      if (version === requestVersion.current) setError(requestErrorMessage(error));
    } finally {
      if (version === requestVersion.current) setStage("idle");
    }
  }

  const fileIsSupported = file && /\.(csv|xlsx)$/i.test(file.name) && file.size <= MAX_FILE_BYTES;

  return (
    <>
      <section className="card" aria-labelledby="upload-heading">
        <h2 id="upload-heading">1. 选择文件并预览</h2>
        <p>
          请选择 GSC 导出的完整 28 天网页表现报告。支持英文或中文 CSV/XLSX 文件，以及最近 28 天或受支持的自定义 28 个日历日范围。
        </p>
        <p>分析 SEO 机会需要两个互不重叠的 28 天 XLSX 报告，且 GSC 属性、搜索类型和完整的非日期筛选条件一致。两个报告的预览都必须显示 28 个连续的已观察日期。仅声明起止日期不能证明日期覆盖完整；CSV 文件不提供可核验的逐日日期依据。</p>
        <p>
          预览只校验文件，不会保存任何页面。文件大小上限为 5 MiB，数据行数上限为 10,000 行。
        </p>
        <label className="field-label" htmlFor="gsc-file">GSC 网页导出文件</label>
        <input ref={fileInput} id="gsc-file" className="visually-hidden" type="file" accept=".csv,.xlsx" aria-label="选择 GSC 网页导出文件" tabIndex={-1} onChange={selectFile} disabled={stage === "applying"} />
        <button type="button" onClick={() => fileInput.current?.click()} disabled={stage === "applying"}>选择文件</button>
        <p className="selected-file" aria-live="polite">{file ? <>已选择：{file.name}</> : "尚未选择文件"}</p>
        <GscScopeInput scope={scope} onChange={updateScope} disabled={stage === "applying"} />
        <button type="button" onClick={uploadPreview} disabled={!fileIsSupported || stage !== "idle"}>
          {stage === "previewing" ? "正在校验……" : "上传并预览"}
        </button>
      </section>

      {error && <p className="notice error" role="alert">{error}</p>}
      {stage !== "idle" && <p role="status">{stage === "previewing" ? "正在生成预览……" : "正在导入页面……"}</p>}

      {preview && (
        <section className="card" aria-labelledby="preview-heading">
          <h2 id="preview-heading">2. 检查预览</h2>
          <dl className="summary-grid">
            <div><dt>数据来源</dt><dd>GSC 网页表现报告</dd></div>
            <div><dt>源工作表</dt><dd>{preview.detected_sheet ?? "CSV（无工作表）"}</dd></div>
            <div><dt>报告窗口</dt><dd>28 天报告</dd></div>
            <div><dt>精确报告日期</dt><dd>{formatPeriod(preview)}</dd></div>
            <div><dt>总行数</dt><dd>{preview.total_rows}</dd></div>
            <div><dt>有效行数</dt><dd>{preview.valid_rows}</dd></div>
            <div><dt>无效行数</dt><dd>{preview.invalid_rows}</dd></div>
            <div><dt>重复行数</dt><dd>{preview.duplicate_rows}</dd></div>
          </dl>

          <h3>报告范围与已观察日期覆盖</h3>
          <ReportScopeSummary scope={preview.report_scope} coverage={preview} showEvidence />
          <p>仅有已知起止日期不能证明日期覆盖完整。报告范围未知时仍可导入，但无法证明两个报告的范围兼容。</p>

          <details className="quality-details">
            <summary>查看已识别的数据列与源文件字段</summary>
            <dl className="mapping-list">
              {Object.entries(preview.column_mapping).map(([field, header]) => (
                <div key={field}><dt>{fieldLabel(field)}（<code>{field}</code>）</dt><dd>{header}</dd></div>
              ))}
            </dl>
            <p>源文件列名保留原文，便于核对导出文件。</p>
          </details>

          {preview.errors.length > 0 && (
            <>
              <h3>校验错误</h3>
              <p>最多显示 100 条错误。行号对应源文件的位置，包含标题行。</p>
              <div className="table-scroll" tabIndex={0} role="region" aria-label="文件校验错误">
                <table>
                  <thead><tr><th scope="col">行号</th><th scope="col">字段</th><th scope="col">错误说明</th></tr></thead>
                  <tbody>{preview.errors.map((error, index) => (
                    <tr key={`${error.row}-${error.field}-${error.code}-${index}`}>
                      <td>{error.row}</td><td>{fieldLabel(error.field)}</td><td>{importRowErrorMessage(error.code)}
                        <details><summary>查看错误标识</summary><p>错误代码：<code>{error.code}</code>；字段：<code>{error.field}</code></p></details>
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </>
          )}

          <h3>标准化数据样本</h3>
          <p>最多显示 10 条有效数据。未知指标保持为空（显示为 —），点击率（CTR）显示为百分比。</p>
          {preview.sample_rows.length > 0
            ? <PageMetricsTable rows={preview.sample_rows} showRowNumber />
            : <p>没有可显示的有效样本。</p>}

          {!preview.can_apply ? (
            <p className="notice error" role="status">
              当前文件无法导入。请修正所有无效或重复行，然后重新选择修正后的文件并预览。重复 URL 的数据不会自动合并。
            </p>
          ) : (
            <div className="confirmation">
              <h3>3. 确认导入</h3>
              <p>系统会在已记录站点范围内为新 URL 创建页面记录；匹配到现有 URL 时，只更新本次文件提供的 GSC 指标。</p>
              <p>空白指标在新页面中保持为空，匹配到现有页面时则保留原值。</p>
              <label className="checkbox-label">
                <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={stage !== "idle" || result !== null} />
                <span>我确认这是受支持的 28 天网页报告，并同意按上方显示的日期和报告范围导入当前预览文件。</span>
              </label>
              <button type="button" onClick={importFile} disabled={!confirmed || stage !== "idle" || result !== null}>
                {stage === "applying" ? "正在导入……" : "确认导入"}
              </button>
            </div>
          )}
        </section>
      )}

      {result && (
        <section className="card" role="status" aria-labelledby="result-heading">
          <h2 id="result-heading">{result.already_processed ? "此文件已导入" : "导入完成"}</h2>
          {result.already_processed && <p>此文件此前已按相同的规范报告范围导入，本次未新增导入历史或快照，也未更改页面指标或指标来源。</p>}
          <dl className="summary-grid">
            <div><dt>新建页面</dt><dd>{result.created_count}</dd></div>
            <div><dt>更新页面</dt><dd>{result.updated_count}</dd></div>
            <div><dt>跳过行数</dt><dd>{result.skipped_count}</dd></div>
            <div><dt>错误数</dt><dd>{result.error_count}</dd></div>
          </dl>
          <Link href="/pages">查看网站页面 →</Link>
          <p><Link href="/imports/history">查看导入历史 →</Link></p>
          <details><summary>查看导入标识</summary><p>导入 ID：<code>{result.import_run_id}</code></p></details>
        </section>
      )}
    </>
  );
}
