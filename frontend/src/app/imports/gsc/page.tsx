import { GscImport } from "@/components/gsc-import";

export default function GscImportPage() {
  return (
    <main className="wide">
      <header>
        <p className="eyebrow">Phase 3 · Development interface / 第三阶段 · 开发界面</p>
        <h1>Import GSC pages / 导入 GSC 网页</h1>
        <p className="intro">File → Validate → Preview → Confirm → Persist / 文件 → 校验 → 预览 → 确认 → 保存</p>
      </header>
      <GscImport />
    </main>
  );
}
