"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  Search,
  Sparkles,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  ShieldAlert,
  HelpCircle,
  Briefcase,
  Layers,
  Code2,
  GraduationCap,
  Calendar,
  ChevronRight,
  Info
} from "lucide-react";
import { toast } from "react-hot-toast";
import { apiFetch, apiPost } from "@/lib/api";

interface ResearchBrief {
  id: number;
  job_id: number;
  company_name: string;
  role: string;
  job_location: string | null;
  job_url: string | null;
  company_overview: string;
  products_and_services: string[];
  industry_and_business_model: string;
  target_customers_or_markets: string;
  recent_announcements: string[];
  engineering_challenges: string[];
  key_skills_in_position: string[];
  candidate_relevant_experience: string[];
  interview_topics_to_prep: string[];
  verified_facts: Array<{ claim: string; source: string; date: string }>;
  inferred_insights: Array<{ insight: string; rationale: string }>;
  unavailable_fields: string[];
  sources: Array<{ label: string; url?: string; type?: string }>;
  retrieval_date: string;
}

interface AvailableJob {
  id: number;
  title: string;
  company: string;
  location: string | null;
  work_arrangement: string | null;
  has_research: boolean;
}

export default function CompanyResearchPage() {
  const [briefs, setBriefs] = useState<ResearchBrief[]>([]);
  const [availableJobs, setAvailableJobs] = useState<AvailableJob[]>([]);
  const [selectedBrief, setSelectedBrief] = useState<ResearchBrief | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "engineering" | "candidate" | "epistemic">("overview");

  const fetchResearchList = async () => {
    setIsLoading(true);
    try {
      const res = await apiFetch<any>(`/api/v1/company-research/?q=${encodeURIComponent(searchQuery)}`);
      setBriefs(res.briefs || []);
      setAvailableJobs(res.available_jobs || []);
      if (res.briefs && res.briefs.length > 0 && !selectedBrief) {
        setSelectedBrief(res.briefs[0]);
      }
    } catch (e: any) {
      console.error("Failed to load company research:", e);
      toast.error(e.message || "Failed to load company research");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResearchList();
  }, [searchQuery]);

  const handleGenerateResearch = async (jobId: number, forceRefresh = false) => {
    setIsGenerating(true);
    const toastId = toast.loading(forceRefresh ? "Refreshing company research..." : "Analyzing company & role attributes...");
    try {
      const res = await apiPost<ResearchBrief>(`/api/v1/company-research/job/${jobId}`, {
        force_refresh: forceRefresh,
      });
      setSelectedBrief(res);
      toast.success("Research brief ready!", { id: toastId });
      fetchResearchList();
    } catch (e: any) {
      toast.error(e.message || "Research generation failed", { id: toastId });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Company Research</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Truthful company briefs, architectural challenges, candidate alignments, and epistemic fact audits.
          </p>
        </div>
        {selectedBrief && (
          <button
            onClick={() => handleGenerateResearch(selectedBrief.job_id, true)}
            disabled={isGenerating}
            className="px-3.5 py-2 bg-white border border-zinc-200 hover:bg-zinc-50 text-zinc-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={isGenerating ? "animate-spin" : ""} />
            Refresh Brief
          </button>
        )}
      </div>

      {/* Main 2-Column Split Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Left Column: Briefs & Available Jobs Selector (4 Cols) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-zinc-200/80 shadow-sm p-4 flex flex-col space-y-4">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              placeholder="Search companies or roles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-zinc-50 border border-zinc-200 rounded-lg text-xs text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-900"
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 max-h-[550px] pr-1">
            <div className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 px-1 mb-1">
              Saved Research Briefs ({briefs.length})
            </div>

            {briefs.map((b) => (
              <button
                key={b.id}
                onClick={() => setSelectedBrief(b)}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  selectedBrief?.id === b.id
                    ? "bg-zinc-900 text-white border-zinc-900 shadow-sm"
                    : "bg-white border-zinc-200/80 text-zinc-800 hover:bg-zinc-50 hover:border-zinc-300"
                }`}
              >
                <div className="font-bold text-xs truncate">{b.company_name}</div>
                <div className={`text-[11px] truncate mt-0.5 ${selectedBrief?.id === b.id ? "text-zinc-300" : "text-zinc-500"}`}>
                  {b.role}
                </div>
                <div className={`text-[10px] mt-2 font-mono flex items-center justify-between ${selectedBrief?.id === b.id ? "text-zinc-400" : "text-zinc-400"}`}>
                  <span>{b.job_location || "Remote"}</span>
                  <span>{new Date(b.retrieval_date).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                </div>
              </button>
            ))}

            {briefs.length === 0 && (
              <div className="p-4 text-center text-xs text-zinc-400">
                No company briefs generated yet.
              </div>
            )}

            {/* Quick Generator from Tracked Jobs */}
            <div className="pt-4 border-t border-zinc-100">
              <div className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 px-1 mb-2">
                Generate for Tracked Roles
              </div>
              <div className="space-y-1.5">
                {availableJobs.filter((j) => !j.has_research).slice(0, 8).map((job) => (
                  <div
                    key={job.id}
                    className="p-2.5 rounded-lg border border-zinc-100 bg-zinc-50/60 hover:bg-zinc-100/60 flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-zinc-900 truncate">{job.company}</div>
                      <div className="text-[11px] text-zinc-500 truncate">{job.title}</div>
                    </div>
                    <button
                      onClick={() => handleGenerateResearch(job.id)}
                      disabled={isGenerating}
                      className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-white rounded text-[11px] font-semibold whitespace-nowrap transition-colors"
                    >
                      Research
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Comprehensive Research Brief View (8 Cols) */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-zinc-200/80 shadow-sm p-6 flex flex-col justify-between">
          {selectedBrief ? (
            <div className="space-y-6">
              {/* Brief Title Bar */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-4 border-b border-zinc-200">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      Company Intelligence Brief
                    </span>
                    <span className="text-xs text-zinc-400">
                      Verified {new Date(selectedBrief.retrieval_date).toLocaleDateString()}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-zinc-900 mt-1">
                    {selectedBrief.company_name}
                  </h2>
                  <p className="text-xs text-zinc-600 mt-0.5">
                    Target Role: <strong className="text-zinc-900">{selectedBrief.role}</strong>
                    {selectedBrief.job_location && ` · ${selectedBrief.job_location}`}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    href="/interview-prep"
                    className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <GraduationCap size={14} />
                    Practice Interview
                  </Link>
                  {selectedBrief.job_url && (
                    <a
                      href={selectedBrief.job_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 border border-zinc-200 hover:bg-zinc-50 rounded-lg text-zinc-600"
                      title="Open job posting"
                    >
                      <ExternalLink size={15} />
                    </a>
                  )}
                </div>
              </div>

              {/* Sub-Tabs */}
              <div className="flex items-center gap-1 border-b border-zinc-100 pb-2 text-xs">
                <button
                  onClick={() => setActiveTab("overview")}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                    activeTab === "overview" ? "bg-zinc-100 text-zinc-900" : "text-zinc-500 hover:text-zinc-800"
                  }`}
                >
                  Overview & Product
                </button>
                <button
                  onClick={() => setActiveTab("engineering")}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                    activeTab === "engineering" ? "bg-zinc-100 text-zinc-900" : "text-zinc-500 hover:text-zinc-800"
                  }`}
                >
                  Engineering & Stack
                </button>
                <button
                  onClick={() => setActiveTab("candidate")}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                    activeTab === "candidate" ? "bg-zinc-100 text-zinc-900" : "text-zinc-500 hover:text-zinc-800"
                  }`}
                >
                  Candidate Alignment
                </button>
                <button
                  onClick={() => setActiveTab("epistemic")}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                    activeTab === "epistemic" ? "bg-zinc-100 text-zinc-900" : "text-zinc-500 hover:text-zinc-800"
                  }`}
                >
                  Facts & Epistemic Audit
                </button>
              </div>

              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <div className="space-y-5 text-xs text-zinc-700">
                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-1.5">Executive Overview</h3>
                    <p className="leading-relaxed bg-zinc-50/60 p-4 rounded-xl border border-zinc-200/70">
                      {selectedBrief.company_overview}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-zinc-200/70 bg-white">
                      <h4 className="font-bold text-zinc-900 mb-2">Products & Core Services</h4>
                      <ul className="space-y-1.5 list-disc list-inside text-zinc-600">
                        {selectedBrief.products_and_services.map((p, idx) => (
                          <li key={idx}>{p}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="p-4 rounded-xl border border-zinc-200/70 bg-white">
                      <h4 className="font-bold text-zinc-900 mb-2">Business Model & Markets</h4>
                      <p className="text-zinc-600 leading-relaxed mb-2">
                        {selectedBrief.industry_and_business_model}
                      </p>
                      <div className="text-[11px] text-zinc-500 pt-2 border-t border-zinc-100">
                        <strong>Target Customers:</strong> {selectedBrief.target_customers_or_markets}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Engineering & Stack */}
              {activeTab === "engineering" && (
                <div className="space-y-5 text-xs">
                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-2">Known Technical Challenges</h3>
                    <div className="space-y-2">
                      {selectedBrief.engineering_challenges.map((c, idx) => (
                        <div key={idx} className="p-3 rounded-lg border border-zinc-200 bg-zinc-50/50 flex items-start gap-2">
                          <Code2 size={15} className="text-indigo-600 mt-0.5 flex-shrink-0" />
                          <span className="text-zinc-700 leading-relaxed">{c}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-2">Key Competencies in Position</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedBrief.key_skills_in_position.map((s, idx) => (
                        <span key={idx} className="px-2.5 py-1 bg-zinc-100 text-zinc-800 rounded font-mono text-xs">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-2">Recommended Interview Topics</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {selectedBrief.interview_topics_to_prep.map((t, idx) => (
                        <div key={idx} className="p-3 rounded-lg border border-zinc-200 bg-white text-zinc-700">
                          {t}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Candidate Alignment */}
              {activeTab === "candidate" && (
                <div className="space-y-5 text-xs">
                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-1.5">Relevant Experience Matches</h3>
                    <p className="text-zinc-500 mb-3">
                      Cross-referenced against verified projects and work history in your Career Profile.
                    </p>
                    <div className="space-y-2">
                      {selectedBrief.candidate_relevant_experience.map((exp, idx) => (
                        <div key={idx} className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50/30 text-zinc-800 flex items-start gap-2.5">
                          <CheckCircle2 size={16} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                          <span className="leading-relaxed">{exp}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Facts & Epistemic Audit */}
              {activeTab === "epistemic" && (
                <div className="space-y-5 text-xs">
                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-1.5">Verified Truthful Facts</h3>
                    <p className="text-zinc-500 mb-2">
                      Facts derived strictly from verified job descriptions and authentic company announcements.
                    </p>
                    <div className="space-y-2">
                      {selectedBrief.verified_facts.map((fact, idx) => (
                        <div key={idx} className="p-3 rounded-lg border border-zinc-200 bg-white">
                          <div className="font-semibold text-zinc-900">{fact.claim}</div>
                          <div className="text-[10px] text-zinc-500 mt-1 flex items-center justify-between">
                            <span>Source: {fact.source}</span>
                            <span>{fact.date}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-1.5">Inferred Architectural Insights</h3>
                    <p className="text-zinc-500 mb-2">
                      Explicit engineering deductions clearly distinguished from unverified assumptions.
                    </p>
                    <div className="space-y-2">
                      {selectedBrief.inferred_insights.map((ins, idx) => (
                        <div key={idx} className="p-3 rounded-lg border border-indigo-200 bg-indigo-50/20">
                          <div className="font-semibold text-zinc-900">{ins.insight}</div>
                          <div className="text-[11px] text-zinc-600 mt-1">
                            <em>Rationale:</em> {ins.rationale}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm mb-1.5">Unavailable / Non-Disclosed Data</h3>
                    <p className="text-zinc-500 mb-2">
                      Honest boundaries: items that are confidential or cannot be verified from public data.
                    </p>
                    <div className="space-y-1.5">
                      {selectedBrief.unavailable_fields.map((un, idx) => (
                        <div key={idx} className="p-2.5 rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600 flex items-center gap-2">
                          <HelpCircle size={14} className="text-zinc-400 flex-shrink-0" />
                          <span>{un}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-12 text-zinc-400">
              <Building2 size={36} className="text-zinc-300 mb-3" />
              <h3 className="text-base font-bold text-zinc-800">Select or Generate a Company Brief</h3>
              <p className="text-xs text-zinc-500 mt-1 max-w-sm">
                Choose any tracked role on the left to review verified company facts, products, engineering challenges, and candidate alignments.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
