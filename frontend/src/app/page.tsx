import { BackendHealth } from "@/components/backend-health";
import Link from "next/link";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">概览</p>
        <h1>SEO 分析工具</h1>
        <p className="intro">
          导入 GSC 数据，查看页面的历史表现与周期对比，并根据透明的规则了解 SEO 机会及其优先级。
        </p>
      </header>

      <section className="card" aria-labelledby="frontend-heading">
        <div className="status-label">运行中</div>
        <h2 id="frontend-heading">前端已启动</h2>
        <p>页面已正常加载，可以检查后端连接并开始导入报告。</p>
      </section>

      <BackendHealth />
      <section className="card" aria-labelledby="data-heading">
        <h2 id="data-heading">GSC 数据流程</h2>
        <p>预览最近 28 天或受支持的自定义 28 天网页表现报告，确认导入后查看已保存的页面指标、历史分析依据与 SEO 机会。</p>
        <p><Link href="/imports/gsc">导入 GSC 数据 →</Link></p>
        <p><Link href="/pages">查看网站页面 →</Link></p>
        <p><Link href="/imports/history">查看导入历史 →</Link></p>
        <p><Link href="/opportunities">查看 SEO 机会优先级与原始信号 →</Link></p>
      </section>
    </main>
  );
}
