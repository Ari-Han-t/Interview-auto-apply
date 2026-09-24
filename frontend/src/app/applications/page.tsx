"use client";

import { useState, useEffect } from "react";
import { apiFetch, apiPost } from "@/lib/api";
import { toast } from "react-hot-toast";
import { Search, ExternalLink, ChevronDown, Clock, Eye, Play, CornerDownRight, CheckCircle2 } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "generating", label: "Generating", color: "bg-amber-100 text-amber-700" },
  { value: "generated", label: "Generated", color: "bg-blue-100 text-blue-700" },
  { value: "applying", label: "Applying", color: "bg-purple-100 text-purple-700" },
  { value: "applied", label: "Applied", color: "bg-indigo-100 text-indigo-700" },
  { value: "interview", label: "Interview", color: "bg-emerald-100 text-emerald-700" },
  { value: "oa", label: "OA", color: "bg-cyan-100 text-cyan-700" },
  { value: "rejected", label: "Rejected", color: "bg-red-100 text-red-700" },
  { value: "offer", label: "Offer", color: "bg-green-100 text-green-800" },
  { value: "intervention_required", label: "Needs Action", color: "bg-orange-100 text-orange-700" },
];

function getStatusStyle(status: string) {
  return STATUS_OPTIONS.find((s) => s.value === status)?.color || "bg-zinc-100 text-zinc-600";
}

function getStatusLabel(status: string) {
  return STATUS_OPTIONS.find((s) => s.value === status)?.label || status;
}

interface AppData {
  id: number;
  job_id: number;
  status: string;
  applied_at: string | null;
  resume_version_url: string | null;
  cover_letter_url: string | null;
  next_action: string | null;
  company: string;
  role: string;
  job_url: string;
}

interface HistoryItem {
  id: number;
  status: string;
  notes: string;
  created_at: string;
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<AppData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [openDropdownId, setOpenDropdownId] = useState<number | null>(null);

  // Timeline drawer state
  const [selectedApp, setSelectedApp] = useState<AppData | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  useEffect(() => {
    fetchApps();
  }, []);

  const fetchApps = async () => {
    try {
      const data = await apiFetch<AppData[]>("/api/v1/applications/");
      setApps(data);
    } catch (err: any) {
      if (err.message !== "Unauthorized") {
        toast.error("Failed to load applications");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleStatusChange = async (appId: number, newStatus: string) => {
    try {
      await apiPost(`/api/v1/applications/${appId}/status`, { status: newStatus });
      setApps(apps.map((app) => (app.id === appId ? { ...app, status: newStatus } : app)));
      toast.success(`Status updated to ${getStatusLabel(newStatus)}`);
      
      // If the timeline is open for this application, refresh it
      if (selectedApp && selectedApp.id === appId) {
        fetchHistory(appId);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to update status");
    }
    setOpenDropdownId(null);
  };

  const handleTriggerAutoApply = async (appId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const toastId = toast.loading("Launching autopilot browser submission...");
    try {
      await apiPost(`/api/v1/applications/${appId}/submit`);
      toast.success("Autopilot application triggered successfully!", { id: toastId });
      fetchApps();
    } catch (err: any) {
      toast.error(err.message || "Failed to trigger auto apply", { id: toastId });
    }
  };

  const handleResumeAutomation = async (appId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiPost(`/api/v1/applications/${appId}/resume`);
      toast.success("Autopilot resumed successfully!");
      fetchApps();
    } catch (err: any) {
      toast.error(err.message || "Failed to resume autopilot");
    }
  };

  const fetchHistory = async (appId: number) => {
    setIsLoadingHistory(true);
    try {
      const data = await apiFetch<HistoryItem[]>(`/api/v1/applications/${appId}/history`);
      setHistory(data);
    } catch (err: any) {
      toast.error("Failed to load application history");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleOpenTimeline = (app: AppData) => {
    setSelectedApp(app);
    fetchHistory(app.id);
  };

  const filteredApps = apps
    .filter((app) => {
      const matchesSearch =
        app.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
        app.role.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = !statusFilter || app.status === statusFilter;
      return matchesSearch && matchesStatus;
    });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Application Tracker</h1>
        <div className="bg-white rounded-xl border border-zinc-200 shadow-sm divide-y">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-5 flex items-center gap-4 animate-pulse">
              <div className="h-4 bg-zinc-200 rounded w-1/4"></div>
              <div className="h-4 bg-zinc-200 rounded w-1/4"></div>
              <div className="h-4 bg-zinc-200 rounded w-1/6"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Application Tracker</h1>
          <p className="text-sm text-zinc-500 mt-1">{apps.length} applications total</p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search by company or role..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-zinc-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white shadow-sm"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2.5 border border-zinc-200 rounded-xl text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        >
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Table Column */}
        <div className={`${selectedApp ? "lg:col-span-2" : "lg:col-span-3"} bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden`}>
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50/80 border-b border-zinc-200">
              <tr>
                <th className="px-5 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Company</th>
                <th className="px-5 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Role</th>
                <th className="px-5 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Actions</th>
                <th className="px-5 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider text-right">Job Url</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {filteredApps.map((app) => (
                <tr key={app.id} className="hover:bg-zinc-50/50 transition-colors">
                  <td className="px-5 py-4 font-medium text-zinc-900">{app.company}</td>
                  <td className="px-5 py-4 text-zinc-600">{app.role}</td>
                  <td className="px-5 py-4 relative">
                    <button
                      onClick={() => setOpenDropdownId(openDropdownId === app.id ? null : app.id)}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusStyle(app.status)}`}
                    >
                      {getStatusLabel(app.status)}
                      <ChevronDown size={10} />
                    </button>
                    {openDropdownId === app.id && (
                      <div className="absolute z-10 mt-1 bg-white border border-zinc-200 rounded-lg shadow-lg py-1 w-40">
                        {STATUS_OPTIONS.map((s) => (
                          <button
                            key={s.value}
                            onClick={() => handleStatusChange(app.id, s.value)}
                            className="w-full text-left px-3 py-1.5 text-xs hover:bg-zinc-50 text-zinc-700"
                          >
                            {s.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-4 flex items-center gap-2">
                    {app.status === "intervention_required" ? (
                      <button
                        onClick={(e) => handleResumeAutomation(app.id, e)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-orange-600 hover:bg-orange-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors"
                      >
                        <CheckCircle2 size={12} /> Confirm Recaptcha
                      </button>
                    ) : (
                      <button
                        onClick={(e) => handleTriggerAutoApply(app.id, e)}
                        disabled={app.status === "applying" || app.status === "applied"}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg disabled:opacity-50 shadow-sm transition-colors"
                      >
                        <Play size={12} /> Auto Apply
                      </button>
                    )}
                    <button
                      onClick={() => handleOpenTimeline(app)}
                      className="p-1.5 border border-zinc-200 rounded-lg hover:bg-zinc-50 text-zinc-600"
                      title="View Timeline History"
                    >
                      <Clock size={14} />
                    </button>
                  </td>
                  <td className="px-5 py-4 text-right">
                    {app.job_url && (
                      <a
                        href={app.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-700 text-xs font-medium"
                      >
                        Open <ExternalLink size={12} />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
              {filteredApps.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-zinc-400">
                    {searchTerm || statusFilter
                      ? "No applications match your search."
                      : "No applications yet. Analyze and generate from the Job Feed!"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Timeline Sidebar Column */}
        {selectedApp && (
          <div className="lg:col-span-1 bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-6">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-zinc-900">{selectedApp.company} Timeline</h3>
                <p className="text-xs text-zinc-500 mt-0.5">{selectedApp.role}</p>
              </div>
              <button
                onClick={() => setSelectedApp(null)}
                className="text-xs text-zinc-400 hover:text-zinc-600"
              >
                Close
              </button>
            </div>

            {isLoadingHistory ? (
              <div className="py-8 text-center text-zinc-400 text-xs animate-pulse">Loading history timeline...</div>
            ) : (
              <div className="relative pl-4 border-l border-zinc-200 space-y-6 text-xs">
                {history.map((h, index) => (
                  <div key={h.id} className="relative">
                    {/* Circle Node */}
                    <div className={`absolute -left-[21px] top-0.5 w-3.5 h-3.5 rounded-full border-2 bg-white ${
                      h.status === "applied" || h.status === "offer"
                        ? "border-emerald-500"
                        : h.status === "failed" || h.status === "rejected"
                        ? "border-red-500"
                        : "border-indigo-500"
                    }`} />
                    
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-900 capitalize">{getStatusLabel(h.status)}</span>
                        <span className="text-[10px] text-zinc-400">
                          {new Date(h.created_at).toLocaleDateString()} {new Date(h.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-zinc-600 leading-relaxed pl-1.5 flex items-start gap-1">
                        <CornerDownRight size={10} className="mt-1 text-zinc-400 flex-shrink-0" />
                        {h.notes}
                      </p>
                    </div>
                  </div>
                ))}
                {history.length === 0 && (
                  <div className="text-zinc-400 py-4 text-center">No history logs recorded yet.</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
