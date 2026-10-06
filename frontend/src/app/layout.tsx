import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO Tool · Phase 1",
  description: "SEO Tool development foundation / SEO Tool 开发基础",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
