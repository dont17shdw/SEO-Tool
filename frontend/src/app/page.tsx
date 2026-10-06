import { BackendHealth } from "@/components/backend-health";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">Phase 1 · Development foundation / 第一阶段 · 开发基础</p>
        <h1>SEO Tool</h1>
        <p className="intro">
          A foundation for data, analysis, prioritization, and recommendations.
          <span lang="zh"> 为数据、分析、优先级排序与建议构建基础。</span>
        </p>
      </header>

      <section className="card" aria-labelledby="frontend-heading">
        <div className="status-label">Running / 运行中</div>
        <h2 id="frontend-heading">Frontend is running / 前端已启动</h2>
        <p>Next.js, React, and TypeScript are ready. 开发基础已就绪。</p>
      </section>

      <BackendHealth />
    </main>
  );
}
