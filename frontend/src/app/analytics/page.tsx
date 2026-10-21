"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  TrendingUp,
  Clock,
  Calendar,
  Layers,
  Award,
  AlertTriangle,
  Info,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  Target,
  FileText,
  Briefcase
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface AnalyticsResponse {
  summary: {
    total_applications: number;
    submitted_applications: number;
    interviews_scheduled: number;
    offers_received: number;
    assessments_received: number;
    rejections: number;
  };
  pipeline_distribution: Array<{
    status: string;
    count: number;
    percentage: number;
  }>;
  weekly_activity: Array<{
    week_label: string;
    count: number;
    start_date: string;
  }>;
  conversion_rates: {
    interview_rate: {
      count: number;
      denominator: number;
      percentage: number;
      label: string;
      is_small_sample: boolean;
      caveat: string | null;
    };
    offer_rate: {
      count: number;
      denominator: number;
      percentage: number;
      label: string;
      is_small_sample: boolean;
      caveat: string | null;
    };
    assessment_rate: {
      count: number;
      denominator: number;
      percentage: number;
      label: string;
      is_small_sample: boolean;
      caveat: string | null;
    };
  };
  response_time_stats: {
    has_enough_data: boolean;
    observations_count: number;
    average_days: number | null;
    median_days: number | null;
    min_days: number | null;
    max_days: number | null;
    notice: string;
  };
  match_brackets: Record<string, { discovered: number; applied: number }>;
  top_technologies: Array<{
    technology: string;
    frequency: number;
  }>;
  outcomes_by_source: Array<{
    source: string;
    applied: number;
    interviews: number;
    offers: number;
    interview_rate: number;
    sample_warning: string | null;
  }>;
  resume_performance: Array<{
    version_name: string;
    applied: number;
    interviews: number;
    offers: number;
    interview_rate: number;
    is_statistically_adequate: boolean;
    sample_warning: string | null;
  }>;
  actionable_insights: Array<{
    type: string;
    title: string;
    description: string;
  }>;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch<AnalyticsResponse>("/api/v1/analytics/overview");
      setData(res);
    } catch (err: any) {
      console.error("Analytics fetch error:", err);
      setError(err.message || "Failed to load career analytics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading analytics data">
        <div className="h-7 w-52 bg-zinc-200 rounded animate-pulse" />
        <div className="h-4 w-96 bg-zinc-100 rounded animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm animate-pulse h-32" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Analytics</h1>
        <div className="bg-red-50 border border-red-200 text-red-800 p-6 rounded-xl flex flex-col gap-3">
          <p className="font-semibold text-sm">Failed to load analytics data</p>
          <p className="text-xs text-red-700">{error || "Backend service unreachable."}</p>
          <button
            onClick={fetchAnalytics}
            className="w-fit px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const {
    summary,
    pipeline_distribution,
    weekly_activity,
    conversion_rates,
    response_time_stats,
    match_brackets,
    top_technologies,
    outcomes_by_source,
    resume_performance,
    actionable_insights,
  } = data;

  const maxWeeklyCount = Math.max(...weekly_activity.map((w) => w.count), 1);
  const maxTechFrequency = Math.max(...top_technologies.map((t) => t.frequency), 1);

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Analytics</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Database-backed pipeline conversion, timing distribution, and empirical variant metrics.
          </p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="px-3.5 py-2 bg-white border border-zinc-200 hover:bg-zinc-50 text-zinc-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors w-fit"
        >
          <RefreshCw size={13} />
          Refresh Calculations
        </button>
      </div>

      {/* Conversion Rates with Denominators */}
      <section aria-labelledby="conversion-heading" className="space-y-3">
        <h2 id="conversion-heading" className="text-xs font-bold uppercase tracking-wider text-zinc-500">
          Stage Conversion Rates (with Explicit Denominators)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Interview Rate */}
          <div className="bg-white p-5 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              <span>Interview Conversion</span>
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
            </div>
            <div className="my-2">
              <div className="text-3xl font-extrabold text-zinc-900 tracking-tight">
                {conversion_rates.interview_rate.percentage}%
              </div>
              <div className="text-xs font-medium text-zinc-600 mt-1">
                {conversion_rates.interview_rate.label}
              </div>
            </div>
            {conversion_rates.interview_rate.caveat && (
              <div className="text-[11px] text-amber-700 bg-amber-50 p-2 rounded border border-amber-200/60 mt-1">
                {conversion_rates.interview_rate.caveat}
              </div>
            )}
          </div>

          {/* Offer Rate */}
          <div className="bg-white p-5 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              <span>Offer Conversion</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            </div>
            <div className="my-2">
              <div className="text-3xl font-extrabold text-zinc-900 tracking-tight">
                {conversion_rates.offer_rate.percentage}%
              </div>
              <div className="text-xs font-medium text-zinc-600 mt-1">
                {conversion_rates.offer_rate.label}
              </div>
            </div>
            {conversion_rates.offer_rate.caveat && (
              <div className="text-[11px] text-amber-700 bg-amber-50 p-2 rounded border border-amber-200/60 mt-1">
                {conversion_rates.offer_rate.caveat}
              </div>
            )}
          </div>

          {/* Assessment Rate */}
          <div className="bg-white p-5 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              <span>Assessment Conversion</span>
              <span className="w-2 h-2 rounded-full bg-blue-500" />
            </div>
            <div className="my-2">
              <div className="text-3xl font-extrabold text-zinc-900 tracking-tight">
                {conversion_rates.assessment_rate.percentage}%
              </div>
              <div className="text-xs font-medium text-zinc-600 mt-1">
                {conversion_rates.assessment_rate.label}
              </div>
            </div>
            <div className="text-[11px] text-zinc-500 mt-1">
              Coding & take-home invitations
            </div>
          </div>

          {/* Total Pipeline Size */}
          <div className="bg-white p-5 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              <span>Total Pipeline Volume</span>
              <span className="w-2 h-2 rounded-full bg-zinc-400" />
            </div>
            <div className="my-2">
              <div className="text-3xl font-extrabold text-zinc-900 tracking-tight">
                {summary.total_applications}
              </div>
              <div className="text-xs font-medium text-zinc-600 mt-1">
                {summary.submitted_applications} submitted to employers
              </div>
            </div>
            <div className="text-[11px] text-zinc-500 mt-1">
              Across all 13 canonical CRM statuses
            </div>
          </div>
        </div>
      </section>

      {/* Pipeline Distribution & Weekly Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Distribution */}
        <section aria-labelledby="pipeline-dist-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-100">
              <h3 id="pipeline-dist-heading" className="font-bold text-sm text-zinc-900">
                Application Pipeline Distribution
              </h3>
              <span className="text-xs text-zinc-500">
                {summary.total_applications} total tracked
              </span>
            </div>

            <div className="space-y-3">
              {pipeline_distribution
                .filter((item) => item.count > 0 || ["Preparing", "Applied", "Interview Scheduled", "Offer Received"].includes(item.status))
                .map((item, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-zinc-800">{item.status}</span>
                      <span className="text-zinc-500 font-mono">
                        {item.count} ({item.percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-zinc-100 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-zinc-800 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(item.percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </section>

        {/* Weekly Activity */}
        <section aria-labelledby="weekly-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-100">
              <h3 id="weekly-heading" className="font-bold text-sm text-zinc-900">
                Weekly Application Activity (Past 8 Weeks)
              </h3>
              <span className="text-xs text-zinc-500">
                Submissions per week
              </span>
            </div>

            <div className="h-44 flex items-end justify-between gap-2 pt-6 pb-2 px-2 border-b border-zinc-100">
              {weekly_activity.map((week, idx) => {
                const heightPct = Math.round((week.count / maxWeeklyCount) * 100);
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end group">
                    <span className="text-[10px] font-mono font-semibold text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity">
                      {week.count}
                    </span>
                    <div
                      className="w-full max-w-[28px] bg-indigo-600 rounded-t transition-all group-hover:bg-indigo-700 min-h-[4px]"
                      style={{ height: `${Math.max(heightPct, 4)}%` }}
                    />
                    <span className="text-[10px] text-zinc-400 truncate w-full text-center">
                      {week.week_label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3">
            Counts reflect applications explicitly confirmed as submitted during each seven-day window.
          </p>
        </section>
      </div>

      {/* Response Times & Match-Score Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Response Times */}
        <section aria-labelledby="response-times-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-100">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-indigo-600" />
                <h3 id="response-times-heading" className="font-bold text-sm text-zinc-900">
                  Application Response Times
                </h3>
              </div>
            </div>

            {response_time_stats.has_enough_data ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                    <span className="text-[10px] uppercase font-bold text-zinc-500">Average</span>
                    <div className="text-lg font-bold text-zinc-900 mt-1">
                      {response_time_stats.average_days} days
                    </div>
                  </div>
                  <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                    <span className="text-[10px] uppercase font-bold text-zinc-500">Median</span>
                    <div className="text-lg font-bold text-zinc-900 mt-1">
                      {response_time_stats.median_days} days
                    </div>
                  </div>
                  <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                    <span className="text-[10px] uppercase font-bold text-zinc-500">Fastest</span>
                    <div className="text-lg font-bold text-zinc-900 mt-1">
                      {response_time_stats.min_days} days
                    </div>
                  </div>
                  <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                    <span className="text-[10px] uppercase font-bold text-zinc-500">Longest</span>
                    <div className="text-lg font-bold text-zinc-900 mt-1">
                      {response_time_stats.max_days} days
                    </div>
                  </div>
                </div>
                <p className="text-xs text-zinc-600">{response_time_stats.notice}</p>
              </div>
            ) : (
              <div className="p-6 bg-zinc-50 rounded-lg border border-dashed border-zinc-200 text-center">
                <Info size={24} className="text-zinc-400 mx-auto mb-2" />
                <h4 className="text-xs font-bold text-zinc-800">Insufficient Response Observations</h4>
                <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
                  {response_time_stats.notice}
                </p>
                <p className="text-[11px] text-zinc-400 mt-2">
                  Avoids displaying skewed or misleading timing averages prior to adequate empirical observations.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Match-Score Distribution */}
        <section aria-labelledby="match-score-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-100">
              <div className="flex items-center gap-2">
                <Target size={16} className="text-emerald-600" />
                <h3 id="match-score-heading" className="font-bold text-sm text-zinc-900">
                  Match-Score Alignment Distribution
                </h3>
              </div>
            </div>

            <div className="space-y-3.5">
              {Object.entries(match_brackets).map(([bracket, counts], idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-800">{bracket}</span>
                    <span className="text-zinc-500 font-mono text-[11px]">
                      {counts.applied} applied / {counts.discovered} discovered
                    </span>
                  </div>
                  <div className="w-full bg-zinc-100 h-2 rounded-full flex overflow-hidden">
                    <div
                      className="bg-emerald-600 h-full transition-all"
                      style={{
                        width: counts.discovered > 0 ? `${(counts.applied / counts.discovered) * 100}%` : "0%",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3">
            Comparison between positions discovered in feed versus positions targeted with submitted applications.
          </p>
        </section>
      </div>

      {/* Frequently Requested Technologies */}
      <section aria-labelledby="tech-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
          <h3 id="tech-heading" className="font-bold text-sm text-zinc-900">
            Frequently Requested Technologies in Target Roles
          </h3>
          <span className="text-xs text-zinc-500">
            Based on required competencies in tracked jobs
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {top_technologies.map((item, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg border border-zinc-200/80 bg-zinc-50/50 flex flex-col justify-between hover:bg-zinc-50 transition-colors"
            >
              <span className="font-bold text-xs text-zinc-900 truncate">{item.technology}</span>
              <div className="flex items-center justify-between text-[11px] text-zinc-500 mt-2">
                <span>Frequency</span>
                <span className="font-mono font-bold text-zinc-800">{item.frequency}×</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Outcomes by Job Source & Resume Variant Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Outcomes by Job Source */}
        <section aria-labelledby="source-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-zinc-100 mb-4">
              <h3 id="source-heading" className="font-bold text-sm text-zinc-900">
                Outcomes by Job Source
              </h3>
              <span className="text-xs text-zinc-500">
                {outcomes_by_source.length} sources tracked
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-zinc-100 text-zinc-400 font-medium">
                    <th className="pb-2">Source</th>
                    <th className="pb-2">Applied</th>
                    <th className="pb-2">Interviews</th>
                    <th className="pb-2">Offers</th>
                    <th className="pb-2 text-right">Int. Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {outcomes_by_source.map((src, idx) => (
                    <tr key={idx} className="hover:bg-zinc-50/60">
                      <td className="py-2.5 font-semibold text-zinc-800">
                        {src.source}
                        {src.sample_warning && (
                          <span className="block text-[10px] font-normal text-amber-700">
                            {src.sample_warning}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 font-mono text-zinc-600">{src.applied}</td>
                      <td className="py-2.5 font-mono text-zinc-600">{src.interviews}</td>
                      <td className="py-2.5 font-mono text-zinc-600">{src.offers}</td>
                      <td className="py-2.5 font-mono font-bold text-zinc-900 text-right">
                        {src.interview_rate}%
                      </td>
                    </tr>
                  ))}
                  {outcomes_by_source.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-zinc-400 text-xs">
                        No submitted applications recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Resume Variant Performance */}
        <section aria-labelledby="resume-perf-heading" className="bg-white p-6 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-zinc-100 mb-4">
              <h3 id="resume-perf-heading" className="font-bold text-sm text-zinc-900">
                Resume Version Performance
              </h3>
              <span className="text-xs text-zinc-500">
                Observed interview rates
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-zinc-100 text-zinc-400 font-medium">
                    <th className="pb-2">Resume Variant</th>
                    <th className="pb-2">Applied</th>
                    <th className="pb-2">Interviews</th>
                    <th className="pb-2 text-right">Interview Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {resume_performance.map((res, idx) => (
                    <tr key={idx} className="hover:bg-zinc-50/60">
                      <td className="py-2.5 pr-2">
                        <span className="font-semibold text-zinc-800">{res.version_name}</span>
                        {res.sample_warning && (
                          <span className="block text-[10px] text-amber-700 leading-tight mt-0.5">
                            {res.sample_warning}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 font-mono text-zinc-600">{res.applied}</td>
                      <td className="py-2.5 font-mono text-zinc-600">{res.interviews}</td>
                      <td className="py-2.5 font-mono font-bold text-zinc-900 text-right">
                        {res.interview_rate}%
                      </td>
                    </tr>
                  ))}
                  {resume_performance.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-zinc-400 text-xs">
                        No variant applications recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <div className="mt-4 p-2.5 bg-zinc-50 rounded border border-zinc-200/80 text-[11px] text-zinc-500">
            <strong>Statistical Standard:</strong> Distinguishes correlation from causation. Variant comparisons require ≥ 15 observations per version to establish statistical relevance.
          </div>
        </section>
      </div>

      {/* Actionable Insights */}
      <section aria-labelledby="insights-heading" className="space-y-3">
        <h2 id="insights-heading" className="text-xs font-bold uppercase tracking-wider text-zinc-500">
          Actionable Career Insights
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {actionable_insights.map((ins, idx) => (
            <div
              key={idx}
              className="bg-white p-5 rounded-xl border border-zinc-200/80 shadow-sm flex flex-col justify-between"
            >
              <div>
                <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-zinc-100 text-zinc-700 mb-2">
                  {ins.type}
                </span>
                <h4 className="text-sm font-bold text-zinc-900">{ins.title}</h4>
                <p className="text-xs text-zinc-600 mt-1.5 leading-relaxed">
                  {ins.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
