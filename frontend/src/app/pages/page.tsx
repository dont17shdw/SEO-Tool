import { PagesList } from "@/components/pages-list";

export default function PagesPage() {
  return (
    <main className="wide">
      <header>
        <p className="eyebrow">已保存的页面指标</p>
        <h1>网站页面</h1>
        <p className="intro">查看已导入的 GSC 网页表现记录，或打开单个页面的表现历史。</p>
      </header>
      <PagesList />
    </main>
  );
}
