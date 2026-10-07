import { PagesList } from "@/components/pages-list";

export default function PagesPage() {
  return (
    <main className="wide">
      <header>
        <p className="eyebrow">Phase 3 · Read-only view / 第三阶段 · 只读视图</p>
        <h1>Website pages / 网站页面</h1>
        <p className="intro">Imported GSC page-performance records. 已导入的 GSC 网页表现记录。</p>
      </header>
      <PagesList />
    </main>
  );
}
