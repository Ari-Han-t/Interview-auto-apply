"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Briefcase,
  LayoutDashboard,
  Settings,
  FileText,
  Bot,
  Sparkles,
  LogOut,
  Mail,
  Database,
  Layers,
  GraduationCap,
  Building2,
  BarChart3,
  Code2,
  X
} from "lucide-react";
import { API_BASE } from "@/lib/api";

export interface NavItem {
  href: string;
  label: string;
  icon: any;
  section: "Core Workspace" | "Preparation & Content" | "System";
}

export const navItems: NavItem[] = [
  // Core Workspace
  { href: "/", label: "Dashboard", icon: LayoutDashboard, section: "Core Workspace" },
  { href: "/jobs", label: "Discover Jobs", icon: Briefcase, section: "Core Workspace" },
  { href: "/applications", label: "Applications", icon: Bot, section: "Core Workspace" },
  { href: "/analytics", label: "Analytics", icon: BarChart3, section: "Core Workspace" },

  // Preparation & Content
  { href: "/profile", label: "Career Profile", icon: FileText, section: "Preparation & Content" },
  { href: "/experience", label: "Projects & Experience", icon: Code2, section: "Preparation & Content" },
  { href: "/content-library", label: "Content Library", icon: Database, section: "Preparation & Content" },
  { href: "/resumes/modular", label: "Resume Studio", icon: Layers, section: "Preparation & Content" },
  { href: "/cover-letters", label: "Cover Letters", icon: Mail, section: "Preparation & Content" },
  { href: "/interview-prep", label: "Interview Preparation", icon: GraduationCap, section: "Preparation & Content" },
  { href: "/company-research", label: "Company Research", icon: Building2, section: "Preparation & Content" },

  // System
  { href: "/settings", label: "Settings & Integrations", icon: Settings, section: "System" },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
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

  const renderNavContent = () => {
    let currentSection = "";

    return (
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const showSection = item.section !== currentSection;
          currentSection = item.section;

          return (
            <div key={item.href}>
              {showSection && (
                <div className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500 mb-2 px-3 mt-4 first:mt-2">
                  {item.section}
                </div>
              )}
              <Link
                href={item.href}
                onClick={onMobileClose}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive(item.href)
                    ? "bg-zinc-900 text-white shadow-sm"
                    : "text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900"
                }`}
              >
                <item.icon
                  size={16}
                  className={isActive(item.href) ? "text-white" : "text-zinc-500"}
                />
                {item.label}
              </Link>
            </div>
          );
        })}
      </nav>
    );
  };

  return (
    <>
      {/* Desktop Static Sidebar */}
      <aside className="w-[260px] bg-[#fbfbfb] border-r border-zinc-200 hidden md:flex flex-col flex-shrink-0 select-none">
        <div className="h-14 flex items-center justify-between px-6 border-b border-zinc-200/60">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-zinc-900 flex items-center justify-center text-white shadow-sm">
              <Sparkles size={13} />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-zinc-900">AutoApply</span>
              <span className="text-[10px] text-zinc-600 font-medium -mt-0.5">Career Manager</span>
            </div>
          </Link>
        </div>

        {renderNavContent()}

        <div className="p-3 border-t border-zinc-200/60">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-red-50 hover:text-red-700 transition-colors w-full text-left"
          >
            <LogOut size={16} className="text-zinc-500" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Navigation drawer"
          className="fixed inset-0 z-50 md:hidden flex"
        >
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={onMobileClose}
            aria-hidden="true"
          />

          {/* Drawer content */}
          <div className="relative w-[280px] max-w-[85vw] bg-white h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-left duration-200">
            <div className="h-14 flex items-center justify-between px-5 border-b border-zinc-200">
              <Link href="/" onClick={onMobileClose} className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-zinc-900 flex items-center justify-center text-white">
                  <Sparkles size={13} />
                </div>
                <span className="font-bold text-sm tracking-tight text-zinc-900">AutoApply</span>
              </Link>
              <button
                type="button"
                onClick={onMobileClose}
                aria-label="Close navigation"
                className="p-1.5 text-zinc-500 hover:text-zinc-800 rounded-md hover:bg-zinc-100"
              >
                <X size={18} />
              </button>
            </div>

            {renderNavContent()}

            <div className="p-3 border-t border-zinc-200">
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-red-50 hover:text-red-700 transition-colors w-full text-left"
              >
                <LogOut size={16} className="text-zinc-500" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
