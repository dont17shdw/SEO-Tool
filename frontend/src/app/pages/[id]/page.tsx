import { PagePerformance } from "@/components/page-performance";

export default async function PageHistoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="wide">
      <header><p className="eyebrow">Phase 7 · Read-only history and signals / 第七阶段 · 只读历史与信号</p><h1>Page performance history / 页面表现历史</h1></header>
      <PagePerformance key={id} pageId={id} />
    </main>
  );
}
