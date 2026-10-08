import { OpportunitiesWorkspace } from "@/components/opportunities-workspace";

export default function OpportunitiesPage() {
  return <main className="wide">
    <header>
      <p className="eyebrow">Phase 8 · Read-only analysis / 第八阶段 · 只读分析</p>
      <h1>SEO opportunities / SEO 机会</h1>
      <p className="intro">Historical GSC evidence → Factual signals → Transparent attention tiers. Candidates and priorities are computed when requested. 历史 GSC 证据 → 事实信号 → 透明关注等级。候选与优先级在请求时计算。</p>
    </header>
    <OpportunitiesWorkspace />
  </main>;
}
