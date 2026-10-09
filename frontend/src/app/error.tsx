"use client";

import Link from "next/link";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main>
      <section className="card" role="alert">
        <h1>页面暂时无法加载</h1>
        <p>请重试；若问题持续，请检查服务状态后再访问。</p>
        <div className="toolbar">
          <button type="button" onClick={reset}>重试</button>
          <Link href="/">返回概览</Link>
        </div>
      </section>
    </main>
  );
}
