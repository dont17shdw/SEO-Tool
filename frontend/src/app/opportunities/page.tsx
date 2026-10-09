import { OpportunitiesWorkspace } from "@/components/opportunities-workspace";

export default function OpportunitiesPage() {
  return <main className="wide">
    <header>
      <p className="eyebrow">历史表现分析</p>
      <h1>SEO 机会</h1>
      <p className="intro">根据历史 GSC 数据识别事实信号，并展示透明的优先级。分析结果在查询时生成，仅供查看。</p>
    </header>
    <OpportunitiesWorkspace />
  </main>;
}
