import { PagePerformance } from "@/components/page-performance";

export default async function PageHistoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="wide">
      <header><p className="eyebrow">Phase 5 · Read-only history / 第五阶段 · 只读历史</p><h1>Page performance history / 页面表现历史</h1></header>
      <PagePerformance key={id} pageId={id} />
    </main>
  );
}
