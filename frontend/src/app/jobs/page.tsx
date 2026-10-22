"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiPost } from "@/lib/api";
import { toast } from "react-hot-toast";
import {
  Search,
  MapPin,
  Briefcase,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  X,
  Check,
  Globe,
  Bookmark,
  BookmarkCheck,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Clock,
  PlusCircle,
  Link as LinkIcon,
  Activity,
  DollarSign,
  Building,
  Filter
} from "lucide-react";
import Link from "next/link";

interface JobData {
  id: number;
  title: string;
  company: string;
  url: string | null;
  application_url: string | null;
  location: string | null;
  description?: string | null;
  status: string;
  salary_range: string | null;
  compensation_min: number | null;
  compensation_max: number | null;
  currency: string | null;
  work_arrangement: string | null;
  employment_type: string | null;
  is_remote: boolean;
  tech_stack_json: string[] | null;
  required_skills_json: string[] | null;
  preferred_skills_json: string[] | null;
  responsibilities_json: string[] | null;
  company_logo_url: string | null;
  source: string | null;
  posted_at: string | null;
  last_verified_at: string | null;
  deadline: string | null;
  is_expired: boolean;
  eligible?: boolean;
  rejection_reason?: string | null;
  match_percentage?: number | null;
  is_saved?: boolean;
  created_at: string;
}

interface SourceHealth {
  source_id: string;
  display_name: string;
  auth_status: string;
  can_fetch_catalog: boolean;
  access_requirement: string;
  last_sync_at: string | null;
  is_healthy: boolean;
  total_jobs_indexed: number;
  recent_sync_status: string | null;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedWorkArrangement, setSelectedWorkArrangement] = useState("all");
  const [selectedJobType, setSelectedJobType] = useState("all");
  const [selectedSkills, setSelectedSkills] = useState("");
  const [showSavedOnly, setShowSavedOnly] = useState(false);
  const [showExpired, setShowExpired] = useState(false);
  const [sortBy, setSortBy] = useState("match_score");
  const [matchResume, setMatchResume] = useState(true);
  const [showEligibleOnly, setShowEligibleOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Modals
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [showImportUrlModal, setShowImportUrlModal] = useState(false);
  const [showManualAddModal, setShowManualAddModal] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [importUrlInput, setImportUrlInput] = useState("");
  const [isImporting, setIsImporting] = useState(false);

  // Source health & logs
  const [sourceHealth, setSourceHealth] = useState<SourceHealth[]>([]);
  const [syncLogs, setSyncLogs] = useState<any[]>([]);

  // Manual Job Form
  const [manualForm, setManualForm] = useState({
    title: "",
    company: "",
    url: "",
    location: "Remote",
    work_arrangement: "remote",
    employment_type: "internship",
    salary_range: "",
    tech_stack_input: "Python, PostgreSQL, FastAPI",
    description: "",
  });

  const router = useRouter();

  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append("q", searchTerm);
      if (selectedSource !== "all") params.append("source", selectedSource);
      if (selectedWorkArrangement !== "all") params.append("work_arrangement", selectedWorkArrangement);
      if (selectedJobType !== "all") params.append("job_type", selectedJobType);
      if (selectedSkills) params.append("skills", selectedSkills);
      if (showSavedOnly) params.append("saved_only", "true");
      if (showExpired) params.append("exclude_expired", "false");
      params.append("match_profile", matchResume ? "true" : "false");
      if (showEligibleOnly) params.append("eligible_only", "true");
      params.append("sort_by", sortBy);

      const data = await apiFetch<JobData[]>(`/api/v1/jobs/?${params.toString()}`);
      setJobs(data);
    } catch (err: any) {
      if (err.message !== "Unauthorized") {
        toast.error("Failed to load jobs");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSourceHealthAndLogs = async () => {
    try {
      const health = await apiFetch<SourceHealth[]>("/api/v1/jobs/sources/health");
      setSourceHealth(health);
      const logs = await apiFetch<any[]>("/api/v1/jobs/sources/logs?limit=15");
      setSyncLogs(logs);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [
    selectedSource,
    selectedWorkArrangement,
    selectedJobType,
    showSavedOnly,
    showExpired,
    sortBy,
    matchResume,
    showEligibleOnly,
  ]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  const handleToggleSave = async (jobId: number, currentSaved: boolean) => {
    // Optimistic update
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, is_saved: !currentSaved } : j))
    );

    try {
      if (currentSaved) {
        await apiFetch(`/api/v1/jobs/${jobId}/save`, { method: "DELETE" });
        toast.success("Removed from saved bookmarks");
      } else {
        await apiPost(`/api/v1/jobs/${jobId}/save`, {});
        toast.success("Job bookmarked");
      }
    } catch (e) {
      // Revert on error
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, is_saved: currentSaved } : j))
      );
      toast.error("Could not update bookmark");
    }
  };

  const handleTriggerSync = async (sourceId = "all") => {
    setIsSyncing(true);
    try {
      const res = await apiPost<any>(`/api/v1/jobs/sync?source=${sourceId}`, {});
      toast.success(res.message || "Sync triggered successfully!");
      await fetchJobs();
      await fetchSourceHealthAndLogs();
    } catch (err: any) {
      toast.error(err.message || "Sync failed");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleImportUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrlInput) return;
    setIsImporting(true);
    try {
      const imported = await apiPost<JobData>("/api/v1/jobs/import-url", {
        url: importUrlInput,
      });
      toast.success(`Successfully imported: ${imported.title} at ${imported.company}`);
      setImportUrlInput("");
      setShowImportUrlModal(false);
      fetchJobs();
    } catch (err: any) {
      toast.error(err.message || "Failed to import job from URL");
    } finally {
      setIsImporting(false);
    }
  };

  const handleManualAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const skillsArray = manualForm.tech_stack_input
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      await apiPost<JobData>("/api/v1/jobs/manual", {
        title: manualForm.title,
        company: manualForm.company,
        url: manualForm.url,
        location: manualForm.location,
        work_arrangement: manualForm.work_arrangement,
        employment_type: manualForm.employment_type,
        salary_range: manualForm.salary_range || null,
        tech_stack_json: skillsArray,
        required_skills_json: skillsArray.slice(0, 4),
        description: manualForm.description,
      });

      toast.success("Job created successfully!");
      setShowManualAddModal(false);
      fetchJobs();
    } catch (err: any) {
      toast.error(err.message || "Failed to add job");
    }
  };

  const sampleNlQueries = [
    "Backend engineering internships in India requiring Python, APIs, PostgreSQL",
    "Remote AI/ML engineer internships with PyTorch and Python",
    "Full-stack entry-level roles requiring React, TypeScript, and Node",
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
              Job Discovery & Ingestion
            </h1>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 font-semibold tracking-wide">
              Live Aggregator
            </span>
          </div>
          <p className="text-zinc-500 text-sm mt-1">
            Search vetted opportunities across Greenhouse, Lever, Ashby, Y Combinator, Internshala, and official career pages.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => {
              fetchSourceHealthAndLogs();
              setShowSyncModal(true);
            }}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-white hover:bg-zinc-50 border border-zinc-200 text-zinc-700 transition shadow-2xs"
          >
            <Activity className="w-3.5 h-3.5 text-indigo-600" />
            Source Health & Sync
          </button>

          <button
            onClick={() => setShowImportUrlModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-white hover:bg-zinc-50 border border-zinc-200 text-zinc-700 transition shadow-2xs"
          >
            <LinkIcon className="w-3.5 h-3.5 text-blue-600" />
            Import Job URL
          </button>

          <button
            onClick={() => setShowManualAddModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white transition shadow-sm"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Add Job
          </button>
        </div>
      </div>

      {/* Natural Language / Keyword Search Box */}
      <div className="bg-white border border-zinc-200/90 rounded-xl p-5 shadow-xs space-y-4">
        <form onSubmit={handleSearchSubmit} className="space-y-4">
          <div className="relative flex items-center">
            <Search className="absolute left-3.5 w-4 h-4 text-zinc-400" />
            <input
              type="text"
              placeholder="Ask in natural language or search keywords (e.g., 'Find backend internships in India requiring Python and PostgreSQL')..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-zinc-50/70 border border-zinc-200 rounded-xl pl-10 pr-24 py-3 text-xs sm:text-sm text-zinc-900 placeholder-zinc-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 transition"
            />
            <button
              type="submit"
              className="absolute right-2 px-3.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold rounded-lg transition shadow-xs"
            >
              Search
            </button>
          </div>

          {/* Natural language suggestion chips */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-zinc-500 font-medium flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Try Prompt:
            </span>
            {sampleNlQueries.map((query, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setSearchTerm(query);
                }}
                className="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-zinc-200/80 text-zinc-700 border border-zinc-200/70 transition truncate max-w-xs text-xs font-medium"
              >
                {query}
              </button>
            ))}
          </div>

          {/* Filter Toggle & Quick Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-zinc-100 text-xs">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Work arrangement */}
              <select
                value={selectedWorkArrangement}
                onChange={(e) => setSelectedWorkArrangement(e.target.value)}
                className="bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-zinc-700 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 shadow-2xs"
              >
                <option value="all">All Locations (Any)</option>
                <option value="remote">Remote Only</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>

              {/* Job type */}
              <select
                value={selectedJobType}
                onChange={(e) => setSelectedJobType(e.target.value)}
                className="bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-zinc-700 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 shadow-2xs"
              >
                <option value="all">All Employment Types</option>
                <option value="internship">Internships Only</option>
                <option value="fulltime">Full-time Roles</option>
                <option value="contract">Contract / Freelance</option>
              </select>

              {/* Source selector */}
              <select
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                className="bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-zinc-700 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 shadow-2xs"
              >
                <option value="all">All Sources</option>
                <option value="greenhouse">Greenhouse</option>
                <option value="lever">Lever</option>
                <option value="ashby">Ashby</option>
                <option value="yc">Y Combinator</option>
                <option value="internshala">Internshala</option>
                <option value="career_page">Company Career Sites</option>
                <option value="linkedin">LinkedIn</option>
                <option value="custom_feed">Remote Feeds</option>
              </select>

              {/* Match CS Resume toggle */}
              <button
                type="button"
                onClick={() => setMatchResume(!matchResume)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition shadow-2xs ${
                  matchResume
                    ? "bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold"
                    : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                }`}
                title="Filter to roles matching Computer Science & Software Engineering resume"
              >
                <Sparkles className={`w-3.5 h-3.5 ${matchResume ? "text-indigo-600 fill-indigo-200" : "text-zinc-400"}`} />
                Match CS Resume
              </button>

              {/* Eligible only toggle */}
              <button
                type="button"
                onClick={() => setShowEligibleOnly(!showEligibleOnly)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition shadow-2xs ${
                  showEligibleOnly
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700 font-semibold"
                    : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                }`}
                title="Only show jobs where you meet eligibility criteria"
              >
                <ShieldCheck className={`w-3.5 h-3.5 ${showEligibleOnly ? "text-emerald-600" : "text-zinc-400"}`} />
                Eligible Only
              </button>

              {/* Saved only button */}
              <button
                type="button"
                onClick={() => setShowSavedOnly(!showSavedOnly)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition shadow-2xs ${
                  showSavedOnly
                    ? "bg-rose-50 border-rose-200 text-rose-700 font-semibold"
                    : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                }`}
              >
                <Bookmark className={`w-3.5 h-3.5 ${showSavedOnly ? "fill-rose-500 text-rose-500" : "text-zinc-400"}`} />
                Saved Only
              </button>

              {/* Show expired toggle */}
              <label className="flex items-center gap-2 cursor-pointer text-zinc-600 select-none text-xs ml-1">
                <input
                  type="checkbox"
                  checked={showExpired}
                  onChange={(e) => setShowExpired(e.target.checked)}
                  className="rounded border-zinc-300 text-zinc-900 focus:ring-0"
                />
                <span>Include Expired</span>
              </label>
            </div>

            {/* Sorting */}
            <div className="flex items-center gap-2">
              <span className="text-zinc-500 text-xs">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-zinc-700 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 shadow-2xs"
              >
                <option value="match_score">⚡ Best Match (Resume)</option>
                <option value="newest">Newest First</option>
                <option value="compensation">Highest Compensation</option>
                <option value="deadline">Approaching Deadline</option>
              </select>
            </div>
          </div>
        </form>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        {matchResume && (
          <div className="flex items-center justify-between p-3 rounded-xl bg-indigo-50/70 border border-indigo-200/80 text-xs text-indigo-900 shadow-2xs">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
              <span>
                <strong>Smart Resume Filter Active:</strong> Showing verified Computer Science, Software Engineering & Tech opportunities matching your background. Marketing, sales, and non-technical listings are filtered out.
              </span>
            </div>
            <button
              onClick={() => setMatchResume(false)}
              className="text-xs font-semibold text-indigo-700 hover:text-indigo-900 underline ml-3 shrink-0"
            >
              Show All Roles
            </button>
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-zinc-500 px-1">
          <span>
            Showing <strong className="text-zinc-900 font-semibold">{jobs.length}</strong> opportunities
          </span>
          <span>Canonical records verified against live source boards</span>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 text-zinc-400 space-y-3 bg-white border border-zinc-200/80 rounded-xl shadow-xs">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
            <p className="text-sm text-zinc-600 font-medium">Querying searchable canonical jobs...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-12 text-center rounded-xl bg-white border border-zinc-200 shadow-xs space-y-4">
            <Building className="w-10 h-10 text-zinc-400 mx-auto" />
            <h3 className="text-base font-semibold text-zinc-900">No matching jobs found</h3>
            <p className="text-sm text-zinc-500 max-w-md mx-auto">
              Try widening your search terms or trigger synchronization from Greenhouse, Ashby, Lever, or YC boards.
            </p>
            <button
              onClick={() => handleTriggerSync("all")}
              className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold rounded-lg transition shadow-xs"
            >
              Sync All Active Sources Now
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3.5">
            {jobs.map((job) => (
              <div
                key={job.id}
                className={`p-5 sm:p-6 rounded-xl border transition-all duration-200 ${
                  job.is_expired
                    ? "bg-zinc-50/70 border-zinc-200 opacity-75"
                    : "bg-white hover:border-zinc-300 border-zinc-200/90 shadow-xs hover:shadow-sm"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Left: Job Info */}
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200 font-medium">
                        #{job.id}
                      </span>

                      {/* Match Score Badge */}
                      {job.match_percentage !== undefined && job.match_percentage !== null && (
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                            job.match_percentage >= 80
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200/80"
                              : job.match_percentage >= 60
                              ? "bg-indigo-50 text-indigo-700 border border-indigo-200/80"
                              : "bg-zinc-100 text-zinc-600 border border-zinc-200"
                          }`}
                        >
                          ⚡ {job.match_percentage}% Match
                        </span>
                      )}

                      {/* Source Tag */}
                      <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/60 uppercase tracking-wider">
                        {job.source || "Direct"}
                      </span>

                      {/* Employment type */}
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700 border border-blue-200/60 capitalize">
                        {job.employment_type || "Role"}
                      </span>

                      {/* Work Arrangement */}
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/60 capitalize">
                        {job.work_arrangement || (job.is_remote ? "Remote" : "Onsite")}
                      </span>

                      {/* Status / Expiration */}
                      {job.is_expired ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1 font-medium">
                          <AlertTriangle className="w-3 h-3" /> Expired
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 font-medium">
                          <ShieldCheck className="w-3 h-3" /> Active
                        </span>
                      )}

                      {/* Eligibility indicator */}
                      {job.eligible === false && (
                        <span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                          {job.rejection_reason || "Check requirements"}
                        </span>
                      )}
                    </div>

                    {/* Job Title and Company */}
                    <div>
                      <Link
                        href={`/jobs/${job.id}`}
                        className="text-base sm:text-lg font-bold text-zinc-900 hover:text-indigo-600 transition-colors"
                      >
                        {job.title}
                      </Link>
                      <div className="flex flex-wrap items-center gap-2.5 text-xs text-zinc-500 mt-1">
                        <span className="font-semibold text-zinc-800">{job.company}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-zinc-400" />
                          {job.location || "Remote"}
                        </span>
                        {job.salary_range && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                              <DollarSign className="w-3 h-3 text-emerald-600" />
                              {job.salary_range}
                            </span>
                          </>
                        )}
                        {job.last_verified_at && (
                          <>
                            <span>•</span>
                            <span className="text-zinc-500 flex items-center gap-1">
                              <Clock className="w-3 h-3 text-zinc-400" />
                              Verified {new Date(job.last_verified_at).toLocaleDateString()}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Brief description snippet */}
                    <p className="text-xs text-zinc-600 line-clamp-2 mt-2 leading-relaxed">
                      {job.description || "Structured job details cataloged."}
                    </p>

                    {/* Skills tags */}
                    {((job.required_skills_json && job.required_skills_json.length > 0) ||
                      (job.tech_stack_json && job.tech_stack_json.length > 0)) && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-2">
                        {(job.required_skills_json || job.tech_stack_json || [])
                          .slice(0, 6)
                          .map((skill, sIdx) => (
                            <span
                              key={sIdx}
                              className="text-[11px] px-2.5 py-0.5 rounded-md bg-zinc-100 text-zinc-700 border border-zinc-200/80 font-medium"
                            >
                              {skill}
                            </span>
                          ))}
                      </div>
                    )}
                  </div>

                  {/* Right: Actions */}
                  <div className="flex md:flex-col items-center md:items-end justify-between gap-2.5 self-stretch md:self-auto border-t md:border-t-0 pt-3 md:pt-0 border-zinc-100">
                    {/* Bookmark button */}
                    <button
                      onClick={() => handleToggleSave(job.id, !!job.is_saved)}
                      title={job.is_saved ? "Remove bookmark" : "Save job"}
                      className={`p-2 rounded-lg border transition shadow-2xs ${
                        job.is_saved
                          ? "bg-rose-50 border-rose-200 text-rose-600 hover:bg-rose-100/60"
                          : "bg-white border-zinc-200 text-zinc-500 hover:text-zinc-800 hover:bg-zinc-50"
                      }`}
                    >
                      <Bookmark className={`w-4 h-4 ${job.is_saved ? "fill-rose-500 text-rose-500" : ""}`} />
                    </button>

                    <div className="flex items-center gap-2">
                      {job.url && (
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-lg bg-white hover:bg-zinc-50 border border-zinc-200 text-zinc-500 hover:text-zinc-800 transition shadow-2xs"
                          title="Open original posting"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      )}

                      <Link
                        href={`/jobs/${job.id}`}
                        className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition shadow-2xs"
                      >
                        View Details & Tailor
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MODAL 1: Source Health & Synchronize */}
      {showSyncModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-zinc-200 rounded-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col shadow-xl">
            <div className="p-5 border-b border-zinc-100 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-600" />
                  Job Source Health & Sync Center
                </h3>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Inspect source status, authentication limits, and trigger multi-source sync.
                </p>
              </div>
              <button
                onClick={() => setShowSyncModal(false)}
                className="text-zinc-400 hover:text-zinc-700 p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Sync Actions Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-zinc-50 border border-zinc-200/80">
                <div>
                  <h4 className="text-xs font-semibold text-zinc-900">Synchronize All Public Catalog Sources</h4>
                  <p className="text-[11px] text-zinc-500 mt-0.5">
                    Runs Greenhouse, Lever, Ashby, YC, Internshala, and public feeds with error isolation.
                  </p>
                </div>
                <button
                  disabled={isSyncing}
                  onClick={() => handleTriggerSync("all")}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition flex items-center gap-2 shadow-xs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin" : ""}`} />
                  {isSyncing ? "Syncing..." : "Sync All Sources"}
                </button>
              </div>

              {/* Source Adapters Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-zinc-800 uppercase tracking-wider">
                  Configured Sources & Access Status
                </h4>
                <div className="divide-y divide-zinc-100 border border-zinc-200 rounded-xl overflow-hidden bg-white shadow-2xs">
                  {sourceHealth.map((src) => (
                    <div key={src.source_id} className="p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-900">{src.display_name}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              src.auth_status === "available"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : src.auth_status === "limited"
                                ? "bg-amber-50 text-amber-700 border border-amber-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {src.auth_status.replace("_", " ")}
                          </span>
                        </div>
                        <p className="text-zinc-500 text-[11px] leading-relaxed">
                          {src.access_requirement}
                        </p>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-[11px] text-zinc-500">
                          Indexed: <strong className="text-zinc-800">{src.total_jobs_indexed}</strong>
                        </span>
                        {src.can_fetch_catalog && (
                          <button
                            disabled={isSyncing}
                            onClick={() => handleTriggerSync(src.source_id)}
                            className="px-2.5 py-1 bg-white hover:bg-zinc-50 text-zinc-700 text-[11px] font-medium rounded border border-zinc-200 transition shadow-2xs"
                          >
                            Sync Source
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Sync Logs */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-zinc-800 uppercase tracking-wider">
                  Recent Synchronization Audit Logs
                </h4>
                {syncLogs.length === 0 ? (
                  <p className="text-xs text-zinc-500">No synchronization logs recorded yet.</p>
                ) : (
                  <div className="divide-y divide-zinc-100 border border-zinc-200 rounded-xl overflow-hidden bg-white text-[11px] shadow-2xs">
                    {syncLogs.map((log) => (
                      <div key={log.id} className="p-3 flex items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-zinc-900 capitalize">{log.source_id}</span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                log.status === "success"
                                  ? "text-emerald-700 bg-emerald-50 border border-emerald-200/60"
                                  : log.status === "blocked"
                                  ? "text-amber-700 bg-amber-50 border border-amber-200/60"
                                  : "text-rose-700 bg-rose-50 border border-rose-200/60"
                              }`}
                            >
                              {log.status}
                            </span>
                            <span className="text-zinc-400">{log.duration_ms}ms</span>
                          </div>
                          {log.error_message && (
                            <p className="text-rose-600 text-[10px] mt-0.5 truncate max-w-md">
                              {log.error_message}
                            </p>
                          )}
                        </div>
                        <div className="text-right text-zinc-500 text-[10px]">
                          <span>
                            +{log.items_imported} new / {log.items_updated} updated
                          </span>
                          <div className="text-zinc-400">
                            {new Date(log.started_at).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Import Job from URL */}
      {showImportUrlModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-zinc-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <h3 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                <LinkIcon className="w-4 h-4 text-blue-600" />
                Import Job by URL
              </h3>
              <button
                onClick={() => setShowImportUrlModal(false)}
                className="text-zinc-400 hover:text-zinc-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-zinc-500 leading-relaxed">
              Paste any job link from Greenhouse, Lever, Ashby, Y Combinator, Internshala, LinkedIn, or official company career sites. We automatically extract structured fields and deduplicate records.
            </p>

            <form onSubmit={handleImportUrl} className="space-y-4">
              <input
                type="url"
                required
                placeholder="https://boards.greenhouse.io/stripe/jobs/12345 or company link..."
                value={importUrlInput}
                onChange={(e) => setImportUrlInput(e.target.value)}
                className="w-full bg-zinc-50 border border-zinc-200 rounded-xl px-4 py-2.5 text-xs text-zinc-900 placeholder-zinc-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 transition"
              />

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowImportUrlModal(false)}
                  className="px-4 py-2 text-xs text-zinc-600 hover:text-zinc-900 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isImporting}
                  className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition shadow-xs"
                >
                  {isImporting ? "Extracting..." : "Import & Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Add Job Manually */}
      {showManualAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-zinc-200 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-xl p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <h3 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                <PlusCircle className="w-4 h-4 text-emerald-600" />
                Add Canonical Job Manually
              </h3>
              <button
                onClick={() => setShowManualAddModal(false)}
                className="text-zinc-400 hover:text-zinc-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleManualAddSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-700 font-medium mb-1">Job Title *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Backend Engineering Intern"
                    value={manualForm.title}
                    onChange={(e) => setManualForm({ ...manualForm, title: e.target.value })}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                  />
                </div>
                <div>
                  <label className="block text-zinc-700 font-medium mb-1">Company *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Acme AI"
                    value={manualForm.company}
                    onChange={(e) => setManualForm({ ...manualForm, company: e.target.value })}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-700 font-medium mb-1">Application or Posting URL</label>
                <input
                  type="url"
                  placeholder="https://company.com/jobs/..."
                  value={manualForm.url}
                  onChange={(e) => setManualForm({ ...manualForm, url: e.target.value })}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-zinc-700 font-medium mb-1">Location</label>
                  <input
                    type="text"
                    placeholder="Remote / City"
                    value={manualForm.location}
                    onChange={(e) => setManualForm({ ...manualForm, location: e.target.value })}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                  />
                </div>
                <div>
                  <label className="block text-zinc-700 font-medium mb-1">Work Arrangement</label>
                  <select
                    value={manualForm.work_arrangement}
                    onChange={(e) => setManualForm({ ...manualForm, work_arrangement: e.target.value })}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                  >
                    <option value="remote">Remote</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="onsite">Onsite</option>
                  </select>
                </div>
                <div>
                  <label className="block text-zinc-700 font-medium mb-1">Type</label>
                  <select
                    value={manualForm.employment_type}
                    onChange={(e) => setManualForm({ ...manualForm, employment_type: e.target.value })}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                  >
                    <option value="internship">Internship</option>
                    <option value="fulltime">Full-time</option>
                    <option value="contract">Contract</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-zinc-700 font-medium mb-1">Compensation / Stipend</label>
                <input
                  type="text"
                  placeholder="e.g. $120,000 - $140,000 /yr or ₹25,000 /month"
                  value={manualForm.salary_range}
                  onChange={(e) => setManualForm({ ...manualForm, salary_range: e.target.value })}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                />
              </div>

              <div>
                <label className="block text-zinc-700 font-medium mb-1">Key Technologies & Skills (comma-separated)</label>
                <input
                  type="text"
                  placeholder="Python, FastAPI, PostgreSQL, Docker"
                  value={manualForm.tech_stack_input}
                  onChange={(e) => setManualForm({ ...manualForm, tech_stack_input: e.target.value })}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                />
              </div>

              <div>
                <label className="block text-zinc-700 font-medium mb-1">Job Description</label>
                <textarea
                  rows={4}
                  placeholder="Paste job description or key expectations..."
                  value={manualForm.description}
                  onChange={(e) => setManualForm({ ...manualForm, description: e.target.value })}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-100">
                <button
                  type="button"
                  onClick={() => setShowManualAddModal(false)}
                  className="px-4 py-2 text-zinc-600 hover:text-zinc-900 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold rounded-lg transition shadow-xs"
                >
                  Save Canonical Job
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
