"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { PageMetricsTable } from "@/components/page-metrics-table";
import { GscScopeInput } from "@/components/gsc-scope-input";
import { ReportScopeSummary } from "@/components/report-scope-summary";
import { formatPeriod } from "@/lib/history-api";
import { type ScopeDeclaration } from "@/lib/report-scope";
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
        ? "Select a CSV or XLSX file. 请选择 CSV 或 XLSX 文件。"
        : nextFile && nextFile.size > MAX_FILE_BYTES
          ? "The file exceeds the 5 MiB upload limit. 文件超过 5 MiB 上传限制。"
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
        <h2 id="upload-heading">1. Select and preview / 选择并预览</h2>
        <p>
          Export the GSC Pages report for the latest 28 days. English and Chinese CSV/XLSX exports are supported.
          <span lang="zh"> 请导出最近 28 天的 GSC 网页报告。支持英文和中文 CSV/XLSX 导出。</span>
        </p>
        <p>
          Preview validates only; it does not save any pages. Limit: 5 MiB and 10,000 data rows.
          <span lang="zh"> 预览仅做校验，不会保存页面。限制为 5 MiB 和 10,000 行数据。</span>
        </p>
        <label className="field-label" htmlFor="gsc-file">GSC Pages export / GSC 网页导出文件</label>
        <input id="gsc-file" type="file" accept=".csv,.xlsx" onChange={selectFile} disabled={stage === "applying"} />
        {file && <p className="selected-file">Selected / 已选择：{file.name}</p>}
        <GscScopeInput scope={scope} onChange={updateScope} disabled={stage === "applying"} />
        <button type="button" onClick={uploadPreview} disabled={!fileIsSupported || stage !== "idle"}>
          {stage === "previewing" ? "Validating… / 校验中……" : "Upload / Preview · 上传 / 预览"}
        </button>
      </section>

      {error && <p className="notice error" role="alert">{error}</p>}
      {stage !== "idle" && <p role="status">{stage === "previewing" ? "Preparing preview… / 正在生成预览……" : "Importing pages… / 正在导入页面……"}</p>}

      {preview && (
        <section className="card" aria-labelledby="preview-heading">
          <h2 id="preview-heading">2. Review preview / 检查预览</h2>
          <dl className="summary-grid">
            <div><dt>Source / 数据源</dt><dd>Google Search Console Pages / 网页</dd></div>
            <div><dt>Sheet / 工作表</dt><dd>{preview.detected_sheet ?? "CSV (no sheet) / CSV（无工作表）"}</dd></div>
            <div><dt>Window / 时间窗口</dt><dd>Latest 28 days / 最近 28 天</dd></div>
            <div><dt>Exact report dates / 精确报告日期</dt><dd>{formatPeriod(preview)}</dd></div>
            <div><dt>Total rows / 总行数</dt><dd>{preview.total_rows}</dd></div>
            <div><dt>Valid rows / 有效行</dt><dd>{preview.valid_rows}</dd></div>
            <div><dt>Invalid rows / 无效行</dt><dd>{preview.invalid_rows}</dd></div>
            <div><dt>Duplicate rows / 重复行</dt><dd>{preview.duplicate_rows}</dd></div>
          </dl>

          <h3>Report scope and observed coverage / 报告范围与已观察覆盖</h3>
          <ReportScopeSummary scope={preview.report_scope} coverage={preview} showEvidence />
          <p>Known endpoints alone do not establish complete coverage. Unknown scope may be imported, but it cannot prove that reports are scope-compatible. 仅有已知起止日期不能证明完整覆盖。未知范围可以导入，但无法证明报告范围兼容。</p>

          <h3>Detected column mapping / 已识别的列映射</h3>
          <dl className="mapping-list">
            {Object.entries(preview.column_mapping).map(([field, header]) => (
              <div key={field}><dt><code>{field}</code></dt><dd>{header}</dd></div>
            ))}
          </dl>

          {preview.errors.length > 0 && (
            <>
              <h3>Validation errors / 校验错误</h3>
              <p>Showing up to 100 errors. Row numbers refer to the source file, including the header. 显示最多 100 条错误。行号对应源文件，并包含标题行。</p>
              <div className="table-scroll" tabIndex={0} role="region" aria-label="Validation errors / 校验错误">
                <table>
                  <thead><tr><th scope="col">Row / 行</th><th scope="col">Field / 字段</th><th scope="col">Error / 错误</th></tr></thead>
                  <tbody>{preview.errors.map((error, index) => (
                    <tr key={`${error.row}-${error.field}-${error.code}-${index}`}>
                      <td>{error.row}</td><td><code>{error.field}</code></td><td>{error.message}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </>
          )}

          <h3>Normalized sample / 标准化样本</h3>
          <p>Up to 10 valid rows. Unknown metrics remain NULL (shown as —); CTR is displayed as a percentage. 最多 10 条有效行。未知指标保持 NULL（显示为 —）；CTR 显示为百分比。</p>
          {preview.sample_rows.length > 0
            ? <PageMetricsTable rows={preview.sample_rows} showRowNumber />
            : <p>No valid sample rows. 没有有效样本行。</p>}

          {!preview.can_apply ? (
            <p className="notice error" role="status">
              Import blocked. Correct every invalid or duplicate row, then select the corrected file and preview again. Duplicate URLs are not aggregated.
              <span lang="zh"> 导入已阻止。请修正所有无效或重复行，重新选择修正后的文件并预览。重复 URL 不会合并。</span>
            </p>
          ) : (
            <div className="confirmation">
              <h3>3. Confirm import / 确认导入</h3>
              <p>Within the recorded site namespace, new URLs create records; matched URLs update only supplied GSC metrics. 在已记录站点命名空间内，新 URL 创建记录；匹配 URL 仅更新所提供的 GSC 指标。</p>
              <p>Blank metrics stay NULL for new pages and preserve existing values for matched URLs. 空白指标在新页面中保持 NULL，在匹配到的现有 URL 中保留原值。</p>
              <label className="checkbox-label">
                <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={stage !== "idle" || result !== null} />
                <span>I confirm this is the latest 28-day Pages report and want to import the previewed file with the scope shown above. 我确认这是最近 28 天的网页报告，并希望使用上方显示的范围导入当前预览文件。</span>
              </label>
              <button type="button" onClick={importFile} disabled={!confirmed || stage !== "idle" || result !== null}>
                {stage === "applying" ? "Importing… / 导入中……" : "Import / 导入"}
              </button>
            </div>
          )}
        </section>
      )}

      {result && (
        <section className="card" role="status" aria-labelledby="result-heading">
          <h2 id="result-heading">{result.already_processed ? "Already processed / 已处理" : "Import complete / 导入完成"}</h2>
          {result.already_processed && <p>This exact file was already imported under the same canonical scope. No new history, snapshots, page changes, or provenance updates were applied. 此文件此前已在相同规范范围下导入。本次未新增历史、快照、页面变更或来源更新。</p>}
          <dl className="summary-grid">
            <div><dt>Created / 新建</dt><dd>{result.created_count}</dd></div>
            <div><dt>Updated / 更新</dt><dd>{result.updated_count}</dd></div>
            <div><dt>Skipped / 跳过</dt><dd>{result.skipped_count}</dd></div>
            <div><dt>Errors / 错误</dt><dd>{result.error_count}</dd></div>
          </dl>
          <Link href="/pages">View imported pages / 查看已导入页面 →</Link>
          <p><Link href="/imports/history">View import history / 查看导入历史 →</Link></p>
          <p><small>Import ID / 导入 ID：{result.import_run_id}</small></p>
        </section>
      )}
    </>
  );
}
