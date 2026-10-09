import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO 分析工具",
  description: "导入 GSC 数据，查看历史表现、分析依据与 SEO 机会优先级。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <nav className="site-nav" aria-label="主导航">
          <Link href="/">SEO 分析工具 · 概览</Link>
          <Link href="/imports/gsc">导入 GSC 数据</Link>
          <Link href="/pages">网站页面</Link>
          <Link href="/imports/history">导入历史</Link>
          <Link href="/opportunities">SEO 机会</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
