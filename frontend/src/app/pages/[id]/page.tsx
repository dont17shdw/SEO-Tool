import { PagePerformance } from "@/components/page-performance";

export default async function PageHistoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="wide">
      <header><p className="eyebrow">历史指标与分析依据</p><h1>页面表现历史</h1></header>
      <PagePerformance key={id} pageId={id} />
    </main>
  );
}
