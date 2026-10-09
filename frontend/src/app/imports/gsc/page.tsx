import { GscImport } from "@/components/gsc-import";

export default function GscImportPage() {
  return (
    <main className="wide">
      <header>
        <p className="eyebrow">GSC 数据导入</p>
        <h1>导入 GSC 数据</h1>
        <p className="intro">选择文件 → 校验与预览 → 确认导入 → 保存</p>
      </header>
      <GscImport />
    </main>
  );
}
