import { OpportunitiesList } from "@/components/opportunities-list";

export default function OpportunitiesPage() {
  return <main className="wide">
    <header>
      <p className="eyebrow">Phase 7 · Read-only signals / 第七阶段 · 只读信号</p>
      <h1>SEO opportunity candidates / SEO 机会候选</h1>
      <p className="intro">Factual signals from trusted historical GSC comparisons. Candidates are computed when requested. 基于可信历史 GSC 对比的事实信号。候选在请求时计算。</p>
    </header>
    <OpportunitiesList />
  </main>;
}
