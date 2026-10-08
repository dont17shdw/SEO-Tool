import { BackendHealth } from "@/components/backend-health";
import Link from "next/link";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">Phase 7 · Development interface / 第七阶段 · 开发界面</p>
        <h1>SEO Tool</h1>
        <p className="intro">
          Import Google Search Console data, inspect comparison evidence, and view factual opportunity signals.
          <span lang="zh"> 导入 Google Search Console 数据，检查对比证据，并查看事实机会信号。</span>
        </p>
      </header>

      <section className="card" aria-labelledby="frontend-heading">
        <div className="status-label">Running / 运行中</div>
        <h2 id="frontend-heading">Frontend is running / 前端已启动</h2>
        <p>Next.js, React, and TypeScript are ready. 开发基础已就绪。</p>
      </section>

      <BackendHealth />
      <section className="card" aria-labelledby="data-heading">
        <h2 id="data-heading">GSC data workflow / GSC 数据流程</h2>
        <p>Preview a latest-28-day Pages export, confirm import, then view stored metrics. 预览最近 28 天的网页导出文件，确认导入后查看已保存指标。</p>
        <p><Link href="/imports/gsc">Import GSC pages / 导入 GSC 网页 →</Link></p>
        <p><Link href="/pages">View stored pages / 查看已保存页面 →</Link></p>
        <p><Link href="/imports/history">View import history / 查看导入历史 →</Link></p>
        <p><Link href="/opportunities">View opportunity candidates / 查看机会候选 →</Link></p>
      </section>
    </main>
  );
}
