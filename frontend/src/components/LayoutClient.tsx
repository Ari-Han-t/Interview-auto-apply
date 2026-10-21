"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";

export function LayoutClient({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    return <div className="min-h-screen bg-[#fafafa]">{children}</div>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-white text-zinc-900">
      <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 bg-white shadow-[-10px_0_15px_-3px_rgba(0,0,0,0.02)] z-10 relative">
        <Header onToggleMobileMenu={() => setMobileOpen((prev) => !prev)} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-4 sm:p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
