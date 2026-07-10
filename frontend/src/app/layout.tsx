import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Briefcase, LayoutDashboard, Settings, FileText, Bot, Menu, Sparkles } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AutoApply | AI Internship Assistant",
  description: "Production-grade AI internship application autopilot.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-[#fafafa] text-zinc-900 antialiased`}>
        <div className="flex h-screen overflow-hidden">
          {/* Sleek Sidebar (Linear style) */}
          <aside className="w-[260px] bg-[#fbfbfb] border-r border-zinc-200 hidden md:flex flex-col">
            <div className="h-14 flex items-center px-6 border-b border-zinc-200/50">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-black flex items-center justify-center text-white">
                  <Sparkles size={14} />
                </div>
                <span className="font-semibold text-sm tracking-tight">AutoApply</span>
              </div>
            </div>
            
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
              <div className="text-xs font-medium text-zinc-500 mb-2 px-3 mt-4">Platform</div>
              <a href="/" className="flex items-center gap-3 px-3 py-2 rounded-md bg-zinc-100 text-zinc-900 text-sm font-medium">
                <LayoutDashboard size={16} className="text-zinc-500" />
                Dashboard
              </a>
              <a href="/jobs" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-zinc-100/50 text-zinc-600 text-sm font-medium transition-colors">
                <Briefcase size={16} className="text-zinc-400" />
                Job Feed
              </a>
              <a href="/applications" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-zinc-100/50 text-zinc-600 text-sm font-medium transition-colors">
                <Bot size={16} className="text-zinc-400" />
                Autopilot
              </a>
              
              <div className="text-xs font-medium text-zinc-500 mb-2 px-3 mt-8">Configuration</div>
              <a href="/profile" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-zinc-100/50 text-zinc-600 text-sm font-medium transition-colors">
                <FileText size={16} className="text-zinc-400" />
                Resume Manager
              </a>
              <a href="/settings" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-zinc-100/50 text-zinc-600 text-sm font-medium transition-colors">
                <Settings size={16} className="text-zinc-400" />
                Settings
              </a>
            </nav>
            
            <div className="p-4 border-t border-zinc-200/50">
              <div className="flex items-center gap-3 px-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white flex items-center justify-center font-semibold text-xs shadow-sm">
                  AG
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-zinc-900 leading-none">Arihant Gupta</span>
                  <span className="text-xs text-zinc-500 mt-1">Free Plan</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Workspace */}
          <div className="flex-1 flex flex-col min-w-0 bg-white shadow-[-10px_0_15px_-3px_rgba(0,0,0,0.02)] z-10 relative">
            
            {/* Glassmorphism Header */}
            <header className="h-14 bg-white/80 backdrop-blur-md border-b border-zinc-200/50 flex items-center justify-between px-6 sticky top-0 z-20">
              <div className="flex items-center gap-4">
                <button className="md:hidden text-zinc-500">
                  <Menu size={20} />
                </button>
                <div className="text-sm font-medium text-zinc-600 capitalize">
                  {/* Breadcrumb could go here */}
                  Workspace
                </div>
              </div>
              <div className="flex items-center gap-4">
                <button className="text-sm px-3 py-1.5 bg-black text-white rounded-md font-medium hover:bg-zinc-800 transition-colors shadow-sm">
                  Upgrade
                </button>
              </div>
            </header>
            
            <main className="flex-1 overflow-y-auto">
              <div className="max-w-6xl mx-auto p-8">
                {children}
              </div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
