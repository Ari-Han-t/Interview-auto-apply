"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Sparkles,
  Send,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Award,
  ArrowRight,
  Bookmark,
  CheckSquare,
  FileText,
  ChevronRight,
  ExternalLink,
  Layers,
  GraduationCap
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DashboardData {
  metrics: {
    new_opportunities: number;
    total_jobs_tracked: number;
    strongly_matching: number;
    saved_jobs: number;
    applications_submitted: number;
    interviews_scheduled: number;
    assessments_due: number;
    followups_due: number;
    offers_received: number;
    rejections: number;
  };
  onboarding: {
    readiness_percentage: number;
    has_profile: boolean;
    has_experience: boolean;
    has_projects: boolean;
    has_resume: boolean;
    has_preferences: boolean;
    has_jobs_discovered: boolean;
    next_recommended_action: string;
    next_recommended_link: string;
  };
  upcoming_events: Array<{
    type: "interview" | "assessment";
    title: string;
    subtitle: string;
    date: string;
    application_id: number;
    job_id: number;
  }>;
  recent_applications: Array<{
    id: number;
    job_id: number;
    company: string;
    role: string;
    status: string;
    applied_at: string | null;
    updated_at: string | null;
    source: string;
    submission_confirmed: boolean;
  }>;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch<DashboardData>("/api/v1/analytics/dashboard");
      setData(res);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.message || "Failed to load dashboard metrics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading dashboard metrics">
        <div className="flex flex-col gap-1">
          <div className="h-7 w-48 bg-zinc-200 rounded animate-pulse" />
          <div className="h-4 w-72 bg-zinc-100 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="bg-white p-5 rounded-xl border border-zinc-200 shadow-sm animate-pulse h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Dashboard</h1>
        <div className="bg-red-50 border border-red-200 text-red-800 p-6 rounded-xl flex flex-col gap-3">
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle size={18} className="text-red-600" />
            <span>Unable to load dashboard data</span>
          </div>
          <p className="text-sm text-red-700">{error || "Backend service unreachable."}</p>
          <button
            onClick={fetchDashboard}
            className="w-fit px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const { metrics, onboarding, upcoming_events, recent_applications } = data;

  const statCards = [
    {
      label: "New Opportunities",
      value: metrics.new_opportunities,
      detail: `${metrics.total_jobs_tracked} total in database`,
      icon: Sparkles,
      color: "text-blue-600",
      bg: "bg-blue-50",
      link: "/jobs",
    },
    {
      label: "Strong Matches",
      value: metrics.strongly_matching,
      detail: "Match score ≥ 75%",
      icon: TrendingUp,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
      link: "/jobs",
    },
    {
      label: "Saved Roles",
      value: metrics.saved_jobs,
      detail: "In shortlist",
      icon: Bookmark,
      color: "text-amber-600",
      bg: "bg-amber-50",
      link: "/applications",
    },
    {
      label: "Applications Submitted",
      value: metrics.applications_submitted,
      detail: "Confirmed submissions",
      icon: Send,
      color: "text-indigo-600",
      bg: "bg-indigo-50",
      link: "/applications",
    },
    {
      label: "Interviews Scheduled",
      value: metrics.interviews_scheduled,
      detail: "Active interview loops",
      icon: Calendar,
      color: "text-purple-600",
      bg: "bg-purple-50",
      link: "/applications",
    },
    {
      label: "Assessments Due",
      value: metrics.assessments_due,
      detail: "Coding & take-home tasks",
      icon: Clock,
      color: "text-rose-600",
      bg: "bg-rose-50",
      link: "/applications",
    },
    {
      label: "Follow-ups Due",
      value: metrics.followups_due,
      detail: "Outreach checklist items",
      icon: CheckSquare,
      color: "text-cyan-600",
      bg: "bg-cyan-50",
      link: "/applications",
    },
    {
      label: "Offers & Outcomes",
      value: `${metrics.offers_received} / ${metrics.rejections}`,
      detail: "Offers vs Rejections",
      icon: Award,
      color: "text-emerald-700",
      bg: "bg-emerald-50",
      link: "/analytics",
    },
  ];

  const onboardingSteps = [
    { label: "Master Resume Uploaded", done: onboarding.has_resume, link: "/profile" },
    { label: "Profile Contact Info", done: onboarding.has_profile, link: "/profile" },
    { label: "Verified Experiences", done: onboarding.has_experience, link: "/experience" },
    { label: "Target Job Preferences", done: onboarding.has_preferences, link: "/settings" },
    { label: "Jobs Discovered", done: onboarding.has_jobs_discovered, link: "/jobs" },
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Real-time pipeline metrics, upcoming deadlines, and verified application tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/jobs"
            className="px-3.5 py-2 bg-zinc-900 text-white rounded-lg text-sm font-medium hover:bg-zinc-800 transition-colors shadow-sm flex items-center gap-1.5"
          >
            <Briefcase size={15} />
            Discover Jobs
          </Link>
          <Link
            href="/applications"
            className="px-3.5 py-2 bg-white border border-zinc-300 text-zinc-700 rounded-lg text-sm font-medium hover:bg-zinc-50 transition-colors shadow-sm"
          >
            Applications CRM
          </Link>
        </div>
      </div>

      {/* Onboarding Readiness Guidance */}
      {onboarding.readiness_percentage < 100 && (
        <section aria-labelledby="onboarding-heading" className="bg-gradient-to-r from-zinc-50 to-indigo-50/40 border border-zinc-200/80 rounded-xl p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-100/60 px-2 py-0.5 rounded">
                  Onboarding Checklist
                </span>
                <span className="text-xs text-zinc-500">
                  {onboarding.readiness_percentage}% Setup Completed
                </span>
              </div>
              <h2 id="onboarding-heading" className="text-base font-bold text-zinc-900 mt-1">
                Calibrate Your Career Engine
              </h2>
            </div>
            <Link
              href={onboarding.next_recommended_link}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 w-fit"
            >
              Take Action <ArrowRight size={14} />
            </Link>
          </div>

          <div className="w-full bg-zinc-200 h-1.5 rounded-full overflow-hidden mb-5">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${onboarding.readiness_percentage}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {onboardingSteps.map((step, idx) => (
              <Link
                key={idx}
                href={step.link}
                className={`p-3 rounded-lg border text-xs font-medium flex items-center gap-2 transition-colors ${
                  step.done
                    ? "bg-white border-zinc-200 text-zinc-800"
                    : "bg-white/80 border-dashed border-zinc-300 text-zinc-500 hover:border-indigo-400 hover:text-indigo-600"
                }`}
              >
                {step.done ? (
                  <CheckCircle2 size={15} className="text-emerald-600 flex-shrink-0" />
                ) : (
                  <div className="w-3.5 h-3.5 rounded-full border border-zinc-300 flex-shrink-0" />
                )}
                <span className="truncate">{step.label}</span>
              </Link>
            ))}
          </div>

          <div className="mt-4 pt-3 border-t border-zinc-200/60 text-xs text-zinc-600 flex items-center gap-2">
            <span className="font-semibold text-zinc-800">Next Step:</span>
            <span>{onboarding.next_recommended_action}</span>
          </div>
        </section>
      )}

      {/* 8 Primary Metrics Cards */}
      <section aria-labelledby="metrics-heading" className="space-y-3">
        <h2 id="metrics-heading" className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
          Core Pipeline Metrics
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <Link
                key={idx}
                href={card.link}
                className="bg-white p-5 rounded-xl border border-zinc-200/80 shadow-sm hover:border-zinc-300 hover:shadow transition-all flex flex-col justify-between group min-h-[115px]"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                    {card.label}
                  </span>
                  <div className={`w-8 h-8 ${card.bg} rounded-lg flex items-center justify-center transition-transform group-hover:scale-105`}>
                    <Icon size={16} className={card.color} />
                  </div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-zinc-900 tracking-tight">
                    {card.value}
                  </div>
                  <div className="text-xs text-zinc-500 mt-0.5">
                    {card.detail}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Two Column Section: Upcoming Deadlines + Recent Applications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upcoming Deadlines & Interviews (1 Col) */}
        <div className="bg-white rounded-xl border border-zinc-200/80 shadow-sm p-6 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-zinc-100 mb-4">
            <div className="flex items-center gap-2">
              <Calendar size={18} className="text-indigo-600" />
              <h3 className="font-bold text-sm text-zinc-900">Upcoming Schedule</h3>
            </div>
            <Link href="/applications" className="text-xs text-zinc-500 hover:text-zinc-800">
              View all
            </Link>
          </div>

          <div className="flex-1 space-y-3">
            {upcoming_events.length > 0 ? (
              upcoming_events.map((ev, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border border-zinc-200/80 bg-zinc-50/40 hover:bg-zinc-50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className={`inline-block text-[10px] uppercase font-bold px-1.5 py-0.5 rounded mb-1 ${
                        ev.type === "interview" ? "bg-purple-100 text-purple-700" : "bg-rose-100 text-rose-700"
                      }`}>
                        {ev.type}
                      </span>
                      <h4 className="text-xs font-semibold text-zinc-900">{ev.title}</h4>
                      <p className="text-[11px] text-zinc-500 mt-0.5">{ev.subtitle}</p>
                    </div>
                    <span className="text-[10px] text-zinc-500 font-mono whitespace-nowrap">
                      {new Date(ev.date).toLocaleDateString([], { month: "short", day: "numeric" })}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-400">
                <CheckCircle2 size={28} className="text-zinc-300 mb-2" />
                <p className="text-xs font-medium text-zinc-600">No events in next 14 days</p>
                <p className="text-[11px] text-zinc-400 mt-1">
                  Scheduled interviews and assessment deadlines will automatically appear here.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Applications Activity (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-zinc-200/80 shadow-sm p-6 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-zinc-100 mb-4">
            <div className="flex items-center gap-2">
              <Layers size={18} className="text-indigo-600" />
              <h3 className="font-bold text-sm text-zinc-900">Recent Applications</h3>
            </div>
            <Link href="/applications" className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
              Open CRM <ChevronRight size={13} />
            </Link>
          </div>

          <div className="flex-1 overflow-x-auto">
            {recent_applications.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-zinc-100 text-zinc-400 font-medium">
                    <th className="pb-2">Company & Role</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Source</th>
                    <th className="pb-2">Applied</th>
                    <th className="pb-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {recent_applications.map((app) => (
                    <tr key={app.id} className="hover:bg-zinc-50/60 transition-colors">
                      <td className="py-2.5 pr-2">
                        <div className="font-semibold text-zinc-900">{app.company}</div>
                        <div className="text-[11px] text-zinc-500 truncate max-w-[180px]">{app.role}</div>
                      </td>
                      <td className="py-2.5 pr-2">
                        <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-100 text-zinc-800">
                          {app.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-2 text-zinc-500 capitalize">
                        {app.source}
                      </td>
                      <td className="py-2.5 pr-2 text-zinc-500 whitespace-nowrap">
                        {app.applied_at ? new Date(app.applied_at).toLocaleDateString([], { month: "short", day: "numeric" }) : "—"}
                      </td>
                      <td className="py-2.5 text-right">
                        <Link
                          href="/applications"
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-zinc-400">
                <Briefcase size={28} className="text-zinc-300 mb-2" />
                <p className="text-xs font-medium text-zinc-600">No applications recorded yet</p>
                <p className="text-[11px] text-zinc-400 mt-1 max-w-sm">
                  Discover roles in your feed, review requirements, and confirm your submissions to track them here.
                </p>
                <Link
                  href="/jobs"
                  className="mt-4 px-3.5 py-1.5 bg-zinc-900 text-white rounded-lg text-xs font-semibold hover:bg-zinc-800 transition-colors"
                >
                  Discover Matching Roles
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
