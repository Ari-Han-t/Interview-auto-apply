import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";
import { LayoutClient } from "@/components/LayoutClient";


export const metadata: Metadata = {
  title: "AutoApply | AI Job Application Assistant",
  description: "Production-grade AI job application autopilot. Scrape jobs, optimize resumes, generate cover letters, and track applications.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-[#fafafa] text-zinc-900 antialiased">
        <Toaster position="bottom-right" />
        <LayoutClient>{children}</LayoutClient>
      </body>
    </html>
  );
}
