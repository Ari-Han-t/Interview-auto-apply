"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { TrendingUp, Send, BarChart3, Activity } from "lucide-react";

interface AnalyticsData {
  total_applications: number;
  total_jobs: number;
  eligible_jobs: number;
  ineligible_jobs: number;
  response_rate: number;
  interview_rate: number;
  ab_testing: { keyword: string; usage_count: number; success_rate: number }[];
}

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const data = await apiFetch<AnalyticsData>("/api/v1/analytics/overview");
        setAnalytics(data);
      } catch (err: any) {
        setError(err.message || "Failed to load analytics");
      } finally {
        setIsLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Dashboard</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm animate-pulse">
              <div className="h-4 bg-zinc-200 rounded w-1/2 mb-4"></div>
              <div className="h-8 bg-zinc-200 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Dashboard</h1>
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl">
          <p className="font-medium">Failed to load analytics</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!analytics) return null;

  const stats = [
    {
      label: "Eligible Jobs",
      value: analytics.eligible_jobs,
      icon: Activity,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
    },
    {
      label: "Total Applications",
      value: analytics.total_applications,
      icon: Send,
      color: "text-indigo-600",
      bg: "bg-indigo-50",
    },
    {
      label: "Rejected By Filters",
      value: analytics.ineligible_jobs,
      icon: BarChart3,
      color: "text-rose-600",
      bg: "bg-rose-50",
    },
    {
      label: "Response Rate",
      value: `${analytics.response_rate.toFixed(1)}%`,
      icon: BarChart3,
      color: "text-indigo-650",
      bg: "bg-indigo-50/50",
    },
    {
      label: "Interview Conversion",
      value: `${analytics.interview_rate.toFixed(1)}%`,
      icon: TrendingUp,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">Overview of your application pipeline.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {stats.map((stat, i) => (
          <div
            key={i}
            className="bg-white p-5 rounded-xl border border-zinc-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between min-h-[120px]"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">{stat.label}</h3>
              <div className={`w-8 h-8 ${stat.bg} rounded-lg flex items-center justify-center`}>
                <stat.icon size={16} className={stat.color} />
              </div>
            </div>
            <p className="text-2xl font-black text-zinc-900 mt-2">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-1">
          <Activity size={18} className="text-zinc-400" />
          <h2 className="text-lg font-semibold text-zinc-900">Keyword Performance</h2>
        </div>
        <p className="text-sm text-zinc-500 mb-6">
          Tracking which keywords in your resume result in the highest interview rates.
        </p>

        <div className="space-y-5">
          {analytics.ab_testing.map((item, index) => (
            <div key={index}>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-zinc-700">
                  {item.keyword}{" "}
                  <span className="text-zinc-400 font-normal">
                    (Used {item.usage_count}×)
                  </span>
                </span>
                <span className="font-semibold text-zinc-900">
                  {item.success_rate}%
                </span>
              </div>
              <div className="w-full bg-zinc-100 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    item.success_rate > 70
                      ? "bg-emerald-500"
                      : item.success_rate > 50
                        ? "bg-blue-500"
                        : "bg-amber-500"
                  }`}
                  style={{ width: `${item.success_rate}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
