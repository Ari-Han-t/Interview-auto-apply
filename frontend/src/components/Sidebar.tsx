"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Briefcase, LayoutDashboard, Settings, FileText, Bot, Sparkles, LogOut, Mail } from "lucide-react";
import { API_BASE } from "@/lib/api";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, section: "Platform" },
  { href: "/jobs", label: "Job Feed", icon: Briefcase, section: "Platform" },
  { href: "/applications", label: "Applications", icon: Bot, section: "Platform" },
  { href: "/cover-letters", label: "Cover Letters", icon: Mail, section: "Configuration" },
  { href: "/profile", label: "Resume Manager", icon: FileText, section: "Configuration" },
  { href: "/settings", label: "Settings", icon: Settings, section: "Configuration" },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const handleLogout = async () => {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    window.location.href = "/login";
  };

  let currentSection = "";

  return (
    <aside className="w-[260px] bg-[#fbfbfb] border-r border-zinc-200 hidden md:flex flex-col">
      <div className="h-14 flex items-center px-6 border-b border-zinc-200/50">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-zinc-900 flex items-center justify-center text-white">
            <Sparkles size={14} />
          </div>
          <span className="font-semibold text-sm tracking-tight">AutoApply</span>
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const showSection = item.section !== currentSection;
          currentSection = item.section;

          return (
            <div key={item.href}>
              {showSection && (
                <div className="text-xs font-medium text-zinc-500 mb-2 px-3 mt-4 first:mt-2">
                  {item.section}
                </div>
              )}
              <Link
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive(item.href)
                    ? "bg-zinc-100 text-zinc-900"
                    : "text-zinc-600 hover:bg-zinc-100/50 hover:text-zinc-800"
                }`}
              >
                <item.icon
                  size={16}
                  className={isActive(item.href) ? "text-zinc-700" : "text-zinc-400"}
                />
                {item.label}
              </Link>
            </div>
          );
        })}
      </nav>

      <div className="p-4 border-t border-zinc-200/50">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-zinc-500 hover:bg-red-50 hover:text-red-600 transition-colors w-full"
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
