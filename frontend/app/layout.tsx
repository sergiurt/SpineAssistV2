import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SpineAssist",
  description: "AI-powered lumbar spine degenerative condition analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-white antialiased">{children}</body>
    </html>
  );
}
