import Link from "next/link";

export default function NotFound() {
  return (
    <main>
      <header>
        <h1>未找到页面</h1>
        <p className="intro">访问地址不存在，请检查地址或返回概览。</p>
      </header>
      <Link href="/">返回概览</Link>
    </main>
  );
}
