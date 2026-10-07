import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO Tool · Phase 4",
  description: "SEO Tool development foundation / SEO Tool 开发基础",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <nav className="site-nav" aria-label="Main navigation / 主导航">
          <Link href="/">SEO Tool · Home / 首页</Link>
          <Link href="/imports/gsc">Import GSC / 导入 GSC</Link>
          <Link href="/pages">Pages / 页面</Link>
          <Link href="/imports/history">Import history / 导入历史</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
