import { ImportHistory } from "@/components/import-history";

export default function ImportHistoryPage() {
  return (
    <main className="wide">
      <header><p className="eyebrow">已保存的报告</p><h1>导入历史</h1></header>
      <ImportHistory />
    </main>
  );
}
