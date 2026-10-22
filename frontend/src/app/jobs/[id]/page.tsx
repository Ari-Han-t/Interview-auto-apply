"use client";

import { useState, useEffect, use } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "react-hot-toast";
import { apiFetch, apiPost, API_BASE } from "@/lib/api";
import {
  Download,
  ArrowLeft,
  GitBranch,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  BookOpen,
  HelpCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  ExternalLink,
  Bookmark,
  Layers,
  Copy,
  Check,
  RotateCcw,
  History,
  SlidersHorizontal,
  RefreshCw,
  Building2,
  Target,
  Cpu,
  FileCheck,
  CheckCheck,
  X,
  Plus,
  Eye,
  Code,
  FileCode,
} from "lucide-react";
import Link from "next/link";

interface Job {
  id: number;
  title: string;
  company: string;
  url: string | null;
  application_url: string | null;
  location: string | null;
  description: string | null;
  salary_range?: string | null;
  work_arrangement?: string | null;
  employment_type?: string | null;
  source?: string | null;
  posted_at?: string | null;
  last_verified_at?: string | null;
  deadline?: string | null;
  is_expired?: boolean;
  source_provenance?: any;
  tech_stack_json?: string[] | null;
  required_skills_json?: string[] | null;
  preferred_skills_json?: string[] | null;
  responsibilities_json?: string[] | null;
  graduation_restrictions?: string[] | null;
  eligible?: boolean;
  rejection_reason?: string | null;
  requirements_json?: any;
}

export default function JobTailoringRoom({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const id = resolvedParams.id;
  const searchParams = useSearchParams();
  const searchAppId = searchParams.get("application_id");
  const forceAnalyze = searchParams.get("analyze") === "true";

  const [githubUsername, setGithubUsername] = useState("");
  const [jobInstructions, setJobInstructions] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [generated, setGenerated] = useState(false);
  const [applicationId, setApplicationId] = useState<number | null>(null);
  const [resumePreview, setResumePreview] = useState("");
  
  const [job, setJob] = useState<Job | null>(null);
  const [isLoadingJob, setIsLoadingJob] = useState(true);

  // Background analysis state
  const [appId, setAppId] = useState<number | null>(null);
  const [appStatus, setAppStatus] = useState<string>("");
  const [progress, setProgress] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, any>>({});
  const [expandedQa, setExpandedQa] = useState<Record<number, boolean>>({});

  // Cover Letter Studio state
  const [clData, setClData] = useState<any>(null);
  const [clContent, setClContent] = useState("");
  const [clStyle, setClStyle] = useState("concise");
  const [clMotivation, setClMotivation] = useState("");
  const [selectedProjects, setSelectedProjects] = useState<number[]>([]);
  const [candidateProjects, setCandidateProjects] = useState<any[]>([]);
  const [isClGenerating, setIsClGenerating] = useState(false);
  const [isClSaving, setIsClSaving] = useState(false);
  const [isClApproved, setIsClApproved] = useState(false);
  const [clVersions, setClVersions] = useState<any[]>([]);
  const [showClHistoryModal, setShowClHistoryModal] = useState(false);
  const [showClDiffModal, setShowClDiffModal] = useState(false);
  const [diffTokens, setDiffTokens] = useState<any[]>([]);
  const [copiedCl, setCopiedCl] = useState(false);

  // Tailored Resume Full-Page Hero state
  const [resumeViewMode, setResumeViewMode] = useState<"pdf" | "latex">("pdf");
  const [latexSource, setLatexSource] = useState<string>("");
  const [isLoadingLatex, setIsLoadingLatex] = useState(false);
  const [copiedTex, setCopiedTex] = useState(false);
  const [pdfRefreshKey, setPdfRefreshKey] = useState(Date.now());
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [isDownloadingTex, setIsDownloadingTex] = useState(false);

  // Company Research state
  const [researchData, setResearchData] = useState<any>(null);
  const [isResearchLoading, setIsResearchLoading] = useState(false);
  const [researchTab, setResearchTab] = useState<"overview" | "challenges" | "skills" | "alignment" | "interview" | "provenance">("overview");

  const checklistItems = [
    { key: "parsing_job", label: "Parsing Job Description & Salary" },
    { key: "matching_resume", label: "Matching Resume & Skill Gap" },
    { key: "tailoring_resume", label: "Tailoring Resume (LaTeX)" },
    { key: "cover_letter", label: "Generating Cover Letter" },
    { key: "company_research", label: "Company Research" },
    { key: "interview_prep", label: "Interview Questions Prep" },
  ];

  // Set appId from URL search parameter if present
  useEffect(() => {
    if (searchAppId) {
      const parsed = parseInt(searchAppId);
      setAppId(parsed);
      setApplicationId(parsed);
    }
  }, [searchAppId]);

  // Fetch candidate projects from library for granular project selection
  const fetchCandidateProjects = async () => {
    try {
      const res = await apiFetch<any>("/api/v1/modular-resume/candidate-modules");
      if (res && res.candidate_data && res.candidate_data.projects) {
        setCandidateProjects(res.candidate_data.projects);
      }
    } catch {
      // ignore
    }
  };

  // Fetch Cover Letter & Version history for this job
  const fetchJobCoverLetter = async () => {
    try {
      const cl = await apiFetch<any>(`/api/v1/cover_letters/job/${id}`);
      if (cl) {
        setClData(cl);
        setClContent(cl.content || "");
        setClStyle(cl.style || "concise");
        setClMotivation(cl.candidate_motivation || "");
        setIsClApproved(Boolean(cl.is_approved));
        if (cl.selected_projects && cl.selected_projects.length > 0) {
          setSelectedProjects(cl.selected_projects);
        }
      }
      const versions = await apiFetch<any[]>(`/api/v1/cover_letters/job/${id}/versions`);
      if (versions) setClVersions(versions);
    } catch {
      // not generated yet
    }
  };

  // Fetch Company Research for this job
  const fetchJobCompanyResearch = async () => {
    try {
      const res = await apiFetch<any>(`/api/v1/company-research/job/${id}`);
      if (res) {
        setResearchData(res);
      }
    } catch {
      // not generated yet
    }
  };

  // Load Job, profile context (GitHub + global instructions), and existing application
  useEffect(() => {
    const fetchJobAndInitialApp = async () => {
      try {
        const jobData = await apiFetch<Job>(`/api/v1/jobs/${id}`);
        setJob(jobData);
        
        // Prefill GitHub username + restore per-job instruction draft
        try {
          const profileData = await apiFetch<any>(`/api/v1/profile/`);
          const gh =
            profileData.github_username ||
            profileData.profile?.github?.replace("https://github.com/", "").replace("/", "") ||
            "";
          if (gh) setGithubUsername(gh);
        } catch {
          // profile may not exist yet
        }
        if (typeof window !== "undefined") {
          const draft = localStorage.getItem(`job_instructions_${id}`);
          if (draft) setJobInstructions(draft);
        }

        try {
          const appData = await apiFetch<any>(`/api/v1/applications/job/${id}`);
          if (appData) {
            setAppId(appData.id);
            setApplicationId(appData.id);
            setAppStatus(appData.status);
            if (appData.user_instructions) setJobInstructions(appData.user_instructions);
            if (appData.status === "generated" || appData.status === "applied" || appData.status === "interview") {
              setGenerated(true);
            }
          } else if (forceAnalyze) {
            handleStartAnalysis();
          }
        } catch (err) {
          if (forceAnalyze) {
            handleStartAnalysis();
          }
        }

        // Fetch Cover Letter, Research, and Candidate Projects concurrently
        fetchJobCoverLetter();
        fetchJobCompanyResearch();
        fetchCandidateProjects();
      } catch (err) {
        toast.error("Failed to load job details.");
      } finally {
        setIsLoadingJob(false);
      }
    };
    fetchJobAndInitialApp();
  }, [id]);

  // Persist instruction draft so a refresh doesn't lose it
  useEffect(() => {
    if (typeof window === "undefined") return;
    const t = setTimeout(() => {
      localStorage.setItem(`job_instructions_${id}`, jobInstructions);
    }, 400);
    return () => clearTimeout(t);
  }, [jobInstructions, id]);

  // Polling hook for background analyses
  useEffect(() => {
    if (!appId) return;

    const fetchProgress = async () => {
      try {
        const res = await apiFetch<any>(`/api/v1/applications/${appId}/progress`);
        setProgress(res.progress || {});
        setResults(res.results || {});
        setAppStatus(res.status);

        if (res.results?.tailoring_resume?.path) {
          setResumePreview(res.results.tailoring_resume.path);
        }
        if (res.results?.cover_letter?.preview && !clContent) {
          setClContent(res.results.cover_letter.preview);
        }

        if (res.status === "generated") {
          setGenerated(true);
          setApplicationId(appId);
          setIsGenerating(false);
          setStatusText("");
          setPdfRefreshKey(Date.now());
          fetchLatexSource();
          fetchJobCoverLetter();
          fetchJobCompanyResearch();
        }
      } catch (err) {
        console.error("Progress polling error:", err);
      }
    };

    if (appStatus === "generated" || appStatus === "applied" || appStatus === "applying") {
      fetchProgress();
      return;
    }

    setIsGenerating(true);
    setStatusText("Running background analyses concurrently...");

    fetchProgress();
    const intervalId = setInterval(fetchProgress, 1500);

    return () => clearInterval(intervalId);
  }, [appId, appStatus]);

  const handleStartAnalysis = async () => {
    setIsGenerating(true);
    setGenerated(false);
    setProgress({});
    setResults({});
    
    try {
      const body: Record<string, string> = {};
      if (jobInstructions.trim()) body.user_instructions = jobInstructions.trim();
      if (githubUsername.trim()) body.github_username = githubUsername.trim();
      const data = await apiPost<{ application_id: number; status: string }>(
        `/api/v1/applications/initialize/${id}`,
        Object.keys(body).length ? body : undefined
      );
      setAppId(data.application_id);
      setAppStatus(data.status);
      toast.success("Concurrently processing resume, cover letter, research, and Q&A!");
    } catch (err: any) {
      toast.error(err.message || "Failed to start analysis");
      setIsGenerating(false);
    }
  };

  const handleAnalyseAndApply = async () => {
    if (job && job.eligible === false) {
      toast(`Note: Role was flagged with eligibility considerations (${job.rejection_reason || "Check qualifications"}). Tailoring resume anyway...`, {
        icon: "ℹ️",
      });
    }
    await handleStartAnalysis();
  };

  const handleApplySubmission = async () => {
    if (!appId) return;
    setIsGenerating(true);
    setStatusText("Submitting application to automation engine...");
    try {
      await apiPost(`/api/v1/applications/${appId}/submit`);
      toast.success("Application generated and submitted successfully!");
      setAppStatus("applying");
    } catch (error: any) {
      toast.error("An error occurred: " + error.message);
    } finally {
      setIsGenerating(false);
      setStatusText("");
    }
  };

  const handleDownload = (content: string, filename: string) => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Downloaded ${filename}`);
  };

  const toggleQa = (idx: number) => {
    setExpandedQa(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleVerifyJobStatus = async () => {
    try {
      const res = await apiPost<{ status: string; last_verified_at: string }>(`/api/v1/jobs/${id}/verify-status`, {});
      toast.success(`Listing status: ${res.status.toUpperCase()}`);
      if (job) {
        setJob({
          ...job,
          is_expired: res.status === "expired",
          last_verified_at: res.last_verified_at
        });
      }
    } catch (e: any) {
      toast.error("Status check failed");
    }
  };

  // Cover Letter Generator Actions
  const handleGenerateCoverLetter = async () => {
    setIsClGenerating(true);
    try {
      const res = await apiPost<any>(`/api/v1/cover_letters/job/${id}/generate`, {
        style: clStyle,
        candidate_motivation: clMotivation,
        selected_project_ids: selectedProjects.length ? selectedProjects : undefined,
        application_id: appId || applicationId || undefined,
      });
      setClData(res);
      setClContent(res.content || "");
      setIsClApproved(Boolean(res.is_approved));
      toast.success(`Generated Version #${res.version_number} (${res.style.toUpperCase()} style)`);
      fetchJobCoverLetter();
    } catch (err: any) {
      toast.error(err.message || "Failed to generate cover letter");
    } finally {
      setIsClGenerating(false);
    }
  };

  const handleSaveCoverLetterVersion = async () => {
    if (!clData) return;
    setIsClSaving(true);
    try {
      const res = await apiPost<any>(`/api/v1/cover_letters/${clData.id}/save-version`, {
        content: clContent,
        style: clStyle,
        candidate_motivation: clMotivation,
        selected_projects: selectedProjects,
        is_approved: isClApproved,
        application_id: appId || applicationId || undefined,
      });
      toast.success(`Saved new Version #${res.version_number}`);
      fetchJobCoverLetter();
    } catch (err: any) {
      toast.error(err.message || "Failed to save version");
    } finally {
      setIsClSaving(false);
    }
  };

  const handleApproveCoverLetter = async () => {
    if (!clData) return;
    try {
      const res = await apiPost<any>(`/api/v1/cover_letters/${clData.id}/approve`);
      setIsClApproved(true);
      toast.success("Cover letter approved & attached to application!");
      fetchJobCoverLetter();
    } catch (err: any) {
      toast.error(err.message || "Failed to approve cover letter");
    }
  };

  const handleCopyCoverLetter = () => {
    if (!clContent) return;
    navigator.clipboard.writeText(clContent);
    setCopiedCl(true);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopiedCl(false), 2000);
  };

  const handleDownloadCoverLetter = (format: "pdf" | "md" | "txt") => {
    if (!clData) return;
    window.open(`${API_BASE}/api/v1/cover_letters/download/${clData.id}?format=${format}`, "_blank");
  };

  const handleCompareVersions = async (v1Id: number, v2Id: number) => {
    try {
      const diff = await apiFetch<any>(`/api/v1/cover_letters/version/${v1Id}/compare/${v2Id}`);
      setDiffTokens(diff.diff_tokens || []);
      setShowClDiffModal(true);
    } catch (err: any) {
      toast.error("Failed to compare versions");
    }
  };

  const handleRestoreVersion = async (verId: number) => {
    try {
      const res = await apiPost<any>(`/api/v1/cover_letters/version/${verId}/restore`);
      toast.success(res.message);
      setShowClHistoryModal(false);
      fetchJobCoverLetter();
    } catch (err: any) {
      toast.error(err.message || "Failed to restore version");
    }
  };

  const toggleProjectSelection = (projId: number) => {
    setSelectedProjects(prev =>
      prev.includes(projId) ? prev.filter(x => x !== projId) : [...prev, projId]
    );
  };

  // Company Research Actions
  const handleRefreshResearch = async () => {
    setIsResearchLoading(true);
    try {
      const res = await apiPost<any>(`/api/v1/company-research/job/${id}`, { force_refresh: true });
      setResearchData(res);
      toast.success("Company research brief updated!");
    } catch (err: any) {
      toast.error(err.message || "Failed to update company research");
    } finally {
      setIsResearchLoading(false);
    }
  };

  const fetchLatexSource = async () => {
    const targetId = applicationId || appId;
    if (!targetId) return;
    setIsLoadingLatex(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const res = await fetch(`${API_BASE}/api/v1/applications/${targetId}/resume.tex`, {
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const text = await res.text();
        setLatexSource(text);
      }
    } catch {
      // ignore
    } finally {
      setIsLoadingLatex(false);
    }
  };

  const handleDownloadPdf = async () => {
    const targetId = applicationId || appId;
    if (!targetId) {
      toast.error("Resume has not been generated yet.");
      return;
    }
    setIsDownloadingPdf(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const res = await fetch(`${API_BASE}/api/v1/applications/${targetId}/resume.pdf`, {
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Download failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${job?.company || "tailored"}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Downloaded tailored resume PDF!");
    } catch (err: any) {
      toast.error(err.message || "Failed to download PDF");
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handleDownloadTex = async () => {
    const targetId = applicationId || appId;
    if (!targetId) {
      toast.error("Resume has not been generated yet.");
      return;
    }
    setIsDownloadingTex(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const res = await fetch(`${API_BASE}/api/v1/applications/${targetId}/resume.tex`, {
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Download failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${job?.company || "tailored"}.tex`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Downloaded LaTeX source (.tex)!");
    } catch (err: any) {
      toast.error(err.message || "Failed to download LaTeX source");
    } finally {
      setIsDownloadingTex(false);
    }
  };

  const handleToggleViewMode = (mode: "pdf" | "latex") => {
    setResumeViewMode(mode);
    if (mode === "latex" && !latexSource) {
      fetchLatexSource();
    }
  };

  const handleCopyLatex = () => {
    if (!latexSource) return;
    navigator.clipboard.writeText(latexSource);
    setCopiedTex(true);
    toast.success("LaTeX source copied to clipboard!");
    setTimeout(() => setCopiedTex(false), 2000);
  };

  const scrollToDetails = () => {
    const el = document.getElementById("application-details");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between bg-white border border-zinc-200 shadow-sm p-4 rounded-xl">
        <div className="flex items-center gap-4">
          <Link
            href="/jobs"
            className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={18} />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Tailoring Room</h1>
              {job && (job.application_url || job.url) && (
                <a
                  href={job.application_url || job.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition shadow-2xs hover:shadow-xs"
                  title="Open original job posting in a new window"
                >
                  <span>View Original Job Posting</span>
                  <ExternalLink size={13} />
                </a>
              )}
            </div>
            <p className="text-sm text-zinc-500 flex items-center gap-2 mt-0.5">
              <span>{job ? `${job.title} at ${job.company}` : `Job #${id}`}</span>
              {job?.location && (
                <>
                  <span className="text-zinc-300">•</span>
                  <span className="text-xs text-zinc-400">{job.location}</span>
                </>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href={`/resumes/modular?job_id=${id}${appId ? `&app_id=${appId}` : ""}`}
            className="inline-flex items-center gap-1.5 bg-white border border-zinc-200 text-zinc-800 px-3.5 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-50 transition-colors shadow-2xs"
          >
            <Layers size={15} className="text-indigo-600" />
            <span>Modular Studio</span>
          </Link>
          {generated && (
            <button
              type="button"
              onClick={handleAnalyseAndApply}
              disabled={isGenerating || appStatus === "generating"}
              className="inline-flex items-center gap-1.5 bg-white border border-zinc-200 text-zinc-800 hover:text-zinc-950 px-3.5 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-50 disabled:opacity-50 transition-colors shadow-2xs cursor-pointer"
              title="Re-run AI tailoring for this job"
            >
              <RefreshCw size={14} className={isGenerating ? "animate-spin text-indigo-600" : "text-zinc-500"} />
              <span>{isGenerating ? "Tailoring..." : "Re-tailor Resume"}</span>
            </button>
          )}
          {appStatus === "generating" ? (
            <div className="flex items-center gap-2 bg-indigo-50 border border-indigo-100 text-indigo-700 px-4 py-2 rounded-lg text-sm font-medium">
              <Loader2 size={16} className="animate-spin" />
              <span>Analyzing & Tailoring...</span>
            </div>
          ) : generated ? (
            <button
              onClick={handleApplySubmission}
              disabled={isGenerating || appStatus === "applying" || appStatus === "applied"}
              className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 disabled:opacity-50 transition-colors shadow-md"
            >
              <Sparkles size={14} />
              {appStatus === "applying" ? "Applying..." : appStatus === "applied" ? "Applied ✓" : "Submit Tailored Application"}
            </button>
          ) : (
            <button
              onClick={handleAnalyseAndApply}
              disabled={Boolean(isLoadingJob || isGenerating)}
              className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 disabled:opacity-50 transition-colors shadow-md cursor-pointer"
            >
              <Sparkles size={14} />
              {isGenerating ? "Analyzing..." : "Analyse & Apply (Concurrent)"}
            </button>
          )}
        </div>
      </div>

      {/* ======================================================== */}
      {/* HERO HIGHLIGHT: Full-Page Tailored Resume (LaTeX & PDF) */}
      {/* ======================================================== */}
      <section aria-label="Tailored Resume Highlight" className="bg-white rounded-2xl border border-zinc-200/90 shadow-lg overflow-hidden flex flex-col h-[82vh] min-h-[720px] max-h-[960px] transition-all">
        {/* Top Control Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 border-b border-zinc-150 bg-zinc-50/80 backdrop-blur-xs">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/10 text-indigo-700 flex items-center justify-center font-bold shadow-2xs">
              <Layers size={19} className="text-indigo-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-zinc-900 tracking-tight">
                  Tailored Resume (LaTeX &amp; PDF)
                </h2>
                {(applicationId || appId) ? (
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold flex items-center gap-1 shadow-2xs">
                    <CheckCircle2 size={11} /> 100% ATS Optimized
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full bg-zinc-200/70 text-zinc-700 text-[10px] font-semibold">
                    Target Role: {job?.title || "Software Engineer"}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-zinc-500 font-medium">
                Single-column ATS format with quantified achievement metrics, targeted project highlights, and verified technical competencies.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* View Mode Switcher: PDF vs LaTeX Source */}
            {(applicationId || appId) && (
              <div className="inline-flex items-center p-0.5 bg-zinc-200/80 rounded-lg text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => handleToggleViewMode("pdf")}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
                    resumeViewMode === "pdf"
                      ? "bg-white text-zinc-900 shadow-2xs"
                      : "text-zinc-600 hover:text-zinc-900"
                  }`}
                >
                  <Eye size={13} />
                  <span>PDF Document</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleToggleViewMode("latex")}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
                    resumeViewMode === "latex"
                      ? "bg-white text-zinc-900 shadow-2xs"
                      : "text-zinc-600 hover:text-zinc-900"
                  }`}
                >
                  <Code size={13} />
                  <span>LaTeX Source</span>
                </button>
              </div>
            )}

            <Link
              href={`/resumes/modular?job_id=${id}${appId ? `&app_id=${appId}` : ""}`}
              className="inline-flex items-center gap-1 text-xs text-indigo-700 hover:text-indigo-900 font-bold bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg border border-indigo-200 transition shadow-2xs"
            >
              <Layers size={13} /> Open Modular Studio
            </Link>

            {job && (job.application_url || job.url) && (
              <a
                href={job.application_url || job.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-zinc-700 hover:text-indigo-600 font-semibold bg-white border border-zinc-200 hover:bg-zinc-50 px-3 py-1.5 rounded-lg transition shadow-2xs"
                title="Open original job posting"
              >
                <ExternalLink size={13} className="text-zinc-500" />
                <span>Job Link ↗</span>
              </a>
            )}

            {(applicationId || appId) && (
              <>
                <button
                  type="button"
                  onClick={handleAnalyseAndApply}
                  disabled={isGenerating || appStatus === "generating"}
                  className="inline-flex items-center gap-1 text-xs text-zinc-700 hover:text-zinc-900 font-semibold bg-white border border-zinc-200 hover:bg-zinc-50 px-3 py-1.5 rounded-lg transition shadow-2xs disabled:opacity-50 cursor-pointer"
                  title="Re-tailor resume with fresh directives"
                >
                  <RefreshCw size={13} className={isGenerating ? "animate-spin text-indigo-600" : "text-zinc-500"} />
                  <span>{isGenerating ? "Tailoring..." : "Re-tailor"}</span>
                </button>
                <button
                  type="button"
                  onClick={handleDownloadTex}
                  disabled={isDownloadingTex}
                  className="inline-flex items-center gap-1 text-xs text-zinc-700 hover:text-zinc-900 font-semibold bg-white border border-zinc-200 hover:bg-zinc-50 px-3 py-1.5 rounded-lg transition shadow-2xs disabled:opacity-50 cursor-pointer"
                  title="Download LaTeX resume source file (.tex)"
                >
                  {isDownloadingTex ? <Loader2 size={13} className="animate-spin text-zinc-500" /> : <Download size={13} />}
                  <span>Source (.tex)</span>
                </button>
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  disabled={isDownloadingPdf}
                  className="inline-flex items-center gap-1.5 text-xs text-white bg-zinc-900 hover:bg-zinc-800 font-bold px-3.5 py-1.5 rounded-lg transition shadow-sm disabled:opacity-50 cursor-pointer"
                  title="Download publication-grade ATS PDF"
                >
                  {isDownloadingPdf ? <Loader2 size={13} className="animate-spin text-white" /> : <Download size={13} />}
                  <span>Download PDF</span>
                </button>
              </>
            )}

            {/* Jump to Cover Letter & Details */}
            <button
              type="button"
              onClick={scrollToDetails}
              className="inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-semibold px-2.5 py-1.5 rounded-lg hover:bg-indigo-50/60 transition cursor-pointer"
              title="Scroll down to Cover Letter Studio and Company Brief"
            >
              <span>Scroll to Cover Letter &amp; Details</span>
              <ChevronDown size={14} className="animate-bounce" />
            </button>
          </div>
        </div>

        {/* Hero Workstation Canvas */}
        <div className="flex-1 bg-zinc-100/70 p-3.5 relative overflow-hidden flex flex-col items-center justify-center">
          {(applicationId || appId) ? (
            resumeViewMode === "pdf" ? (
              <div className="w-full h-full rounded-xl overflow-hidden shadow-md border border-zinc-200 bg-white">
                <iframe
                  src={`${API_BASE}/api/v1/applications/${applicationId || appId}/resume.pdf?t=${pdfRefreshKey}${
                    typeof window !== "undefined" && localStorage.getItem("access_token")
                      ? `&token=${encodeURIComponent(localStorage.getItem("access_token") || "")}`
                      : ""
                  }`}
                  className="w-full h-full border-0"
                  title="Tailored Resume Full-Page PDF Preview"
                />
              </div>
            ) : (
              <div className="w-full h-full bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800 flex flex-col shadow-md">
                <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900/90 text-xs text-zinc-400">
                  <div className="flex items-center gap-2">
                    <FileCode size={13} className="text-indigo-400" />
                    <span className="font-mono text-zinc-300">resume.tex</span>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">LaTeX • UTF-8</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyLatex}
                    className="inline-flex items-center gap-1 text-zinc-300 hover:text-white px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 transition font-medium"
                  >
                    {copiedTex ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    <span>{copiedTex ? "Copied!" : "Copy LaTeX"}</span>
                  </button>
                </div>
                {isLoadingLatex ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 text-xs gap-2">
                    <Loader2 size={24} className="animate-spin text-indigo-400" />
                    <span>Loading LaTeX source code...</span>
                  </div>
                ) : (
                  <pre className="flex-1 p-5 font-mono text-xs text-emerald-400/90 overflow-auto whitespace-pre leading-relaxed select-all">
                    {latexSource || resumePreview || "% LaTeX source compiling..."}
                  </pre>
                )}
              </div>
            )
          ) : (
            /* Pre-generation Blueprint Canvas */
            <div className="w-full h-full max-w-4xl bg-white rounded-xl shadow-md border border-zinc-200/90 p-8 flex flex-col justify-between relative overflow-hidden">
              {/* Ghost Resume Template preview */}
              <div className="space-y-6 opacity-30 filter blur-[0.4px] select-none pointer-events-none">
                <div className="text-center border-b border-zinc-300 pb-4">
                  <div className="h-6 w-48 bg-zinc-800 rounded mx-auto mb-2"></div>
                  <div className="h-3 w-72 bg-zinc-400 rounded mx-auto mb-1"></div>
                  <div className="h-3 w-96 bg-zinc-400 rounded mx-auto"></div>
                </div>
                <div>
                  <div className="h-4 w-36 bg-zinc-700 rounded mb-2 border-b border-zinc-400 pb-1"></div>
                  <div className="h-3 w-full bg-zinc-300 rounded mb-1"></div>
                  <div className="h-3 w-11/12 bg-zinc-300 rounded mb-1"></div>
                  <div className="h-3 w-4/5 bg-zinc-300 rounded"></div>
                </div>
                <div>
                  <div className="h-4 w-44 bg-zinc-700 rounded mb-2 border-b border-zinc-400 pb-1"></div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <div className="h-3.5 w-48 bg-zinc-600 rounded"></div>
                      <div className="h-3 w-24 bg-zinc-400 rounded"></div>
                    </div>
                    <div className="h-3 w-full bg-zinc-300 rounded"></div>
                    <div className="h-3 w-11/12 bg-zinc-300 rounded"></div>
                  </div>
                </div>
                <div>
                  <div className="h-4 w-40 bg-zinc-700 rounded mb-2 border-b border-zinc-400 pb-1"></div>
                  <div className="h-3 w-full bg-zinc-300 rounded mb-1"></div>
                  <div className="h-3 w-3/4 bg-zinc-300 rounded"></div>
                </div>
              </div>

              {/* Center High-Impact CTA Card */}
              <div className="absolute inset-0 flex items-center justify-center p-6 bg-gradient-to-b from-white/70 via-white/92 to-white/98 backdrop-blur-[2px]">
                <div className="max-w-md w-full bg-white border border-zinc-200/90 rounded-2xl p-6 shadow-2xl text-center space-y-4">
                  <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-inner">
                    <Sparkles size={24} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900 tracking-tight">
                      Generate Tailored Resume for this Role
                    </h3>
                    <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                      Our modular ATS engine will analyze <strong className="text-zinc-800">{job?.title || "the role"}</strong> at <strong className="text-zinc-800">{job?.company || "the company"}</strong>, select your highest-impact projects, inject quantified metrics (+40% throughput, 99.9% uptime), and compile a publication-grade LaTeX PDF.
                    </p>
                  </div>
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={handleAnalyseAndApply}
                      disabled={Boolean(isLoadingJob || isGenerating)}
                      className="w-full inline-flex items-center justify-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold text-xs py-3 px-5 rounded-xl transition shadow-md disabled:opacity-50 cursor-pointer"
                    >
                      <Sparkles size={14} className="text-indigo-400" />
                      <span>{isGenerating ? "Analyzing & Compiling Resume..." : "Analyse & Generate Tailored Resume (1-Click)"}</span>
                    </button>
                  </div>
                  <div className="flex items-center justify-center gap-4 text-[11px] text-zinc-400 pt-1">
                    <span className="flex items-center gap-1">✓ Single-Column ATS</span>
                    <span className="flex items-center gap-1">✓ pdflatex Compiled</span>
                    <span className="flex items-center gap-1">✓ Zero Keyword Stuffing</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Banner with Smooth Scroll Link */}
        <div className="px-5 py-2.5 border-t border-zinc-150 bg-white flex items-center justify-between text-xs text-zinc-500">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>Targeting: <strong>{job?.company}</strong> ({job?.location || "Remote"})</span>
            {job && (job.application_url || job.url) && (
              <>
                <span className="text-zinc-300">•</span>
                <a
                  href={job.application_url || job.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-semibold hover:underline"
                  title="Open original job posting"
                >
                  <span>Job Posting URL</span>
                  <ExternalLink size={11} />
                </a>
              </>
            )}
          </div>
          <button
            type="button"
            onClick={scrollToDetails}
            className="inline-flex items-center gap-1.5 font-semibold text-indigo-600 hover:text-indigo-800 cursor-pointer transition hover:translate-y-0.5"
          >
            <span>Scroll down for Cover Letter Studio, Company Intelligence &amp; Job Context</span>
            <ChevronDown size={14} />
          </button>
        </div>
      </section>

      {/* ======================================================== */}
      {/* LOWER SECTION: Cover Letter Studio, Research & Job Context */}
      {/* ======================================================== */}
      {/* Main Grid: Left Column (Job info + Instructions) | Right Column (Research, Cover Letter) */}
      <div id="application-details" className="grid grid-cols-1 xl:grid-cols-12 gap-6 flex-1 items-start scroll-mt-6">
        {/* Left Column (Job details, context inputs, progress) */}
        <div className="xl:col-span-5 space-y-6">
          {/* Instructions Input */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-4 space-y-3">
            <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-1.5">
              <SlidersHorizontal size={14} className="text-indigo-600" />
              Custom Tailoring Directives
            </h3>
            <textarea
              value={jobInstructions}
              onChange={(e) => setJobInstructions(e.target.value)}
              placeholder="e.g. Highlight high-throughput distributed systems experience and Redis caching."
              className="w-full text-xs p-3 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-zinc-900 resize-none h-20 text-zinc-700"
            />
          </div>

          {/* Progress Checklist */}
          {appStatus === "generating" && (
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-4 space-y-2">
              <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider mb-2">
                Parallel Pipeline Tasks
              </h3>
              {checklistItems.map((item) => {
                const status = progress[item.key] || "pending";
                let icon = <Clock size={15} className="text-zinc-300" />;
                let textClass = "text-zinc-400";
                if (status === "completed") {
                  icon = <CheckCircle2 size={15} className="text-emerald-500 fill-emerald-50" />;
                  textClass = "text-zinc-800 font-semibold";
                } else if (status === "running") {
                  icon = <Loader2 size={15} className="text-indigo-600 animate-spin" />;
                  textClass = "text-indigo-600 font-medium";
                } else if (status === "failed") {
                  icon = <AlertTriangle size={15} className="text-red-500" />;
                  textClass = "text-red-500 font-semibold";
                }
                return (
                  <div key={item.key} className="flex items-center gap-2.5 text-xs py-1 border-b border-zinc-50 last:border-0">
                    {icon}
                    <span className={textClass}>{item.label}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Job Details Card */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-4">
            {job ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                  <div>
                    <h2 className="text-base font-bold text-zinc-900">{job.title}</h2>
                    <p className="text-xs text-zinc-500 font-medium">{job.company} • {job.location || "Remote"}</p>
                  </div>
                  <button
                    onClick={handleVerifyJobStatus}
                    className="text-[11px] px-2.5 py-1 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700 font-medium transition"
                  >
                    Check Status
                  </button>
                </div>

                {job.salary_range && (
                  <div className="bg-emerald-50/50 border border-emerald-150 rounded-lg p-2.5 text-xs text-emerald-900 font-medium">
                    Compensation: {job.salary_range}
                  </div>
                )}

                <div className="space-y-2 text-xs text-zinc-650">
                  <p><strong className="text-zinc-900">Employment Type:</strong> {job.employment_type || "Full-time"}</p>
                  <p><strong className="text-zinc-900">Work Arrangement:</strong> {job.work_arrangement || "Onsite"}</p>
                  {job.last_verified_at && (
                    <p><strong className="text-zinc-900">Last Verified:</strong> {new Date(job.last_verified_at).toLocaleDateString()}</p>
                  )}
                </div>

                {/* Technologies */}
                {(job.required_skills_json?.length || job.tech_stack_json?.length) ? (
                  <div className="space-y-1.5 pt-2">
                    <p className="text-xs font-bold text-zinc-900">Required Skills &amp; Stack:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {Array.from(new Set([...(job.required_skills_json || []), ...(job.tech_stack_json || [])])).map((sk, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded bg-zinc-100 text-zinc-800 text-[11px] font-medium border border-zinc-200">
                          {sk}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {/* Job Links */}
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-zinc-100">
                  {job.url && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 text-zinc-700 text-xs font-medium transition"
                    >
                      <ExternalLink size={12} /> Original Posting
                    </a>
                  )}
                  {job.application_url && job.application_url !== job.url && (
                    <a
                      href={job.application_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 text-zinc-700 text-xs font-medium transition"
                    >
                      <ExternalLink size={12} /> Direct Portal
                    </a>
                  )}
                </div>

                {/* Full Description Accordion */}
                <div className="pt-2 border-t border-zinc-100">
                  <h4 className="font-bold text-zinc-900 mb-1 text-xs">Job Description:</h4>
                  <div className="text-xs text-zinc-650 leading-relaxed max-h-[160px] overflow-y-auto whitespace-pre-wrap p-2.5 bg-zinc-50/50 rounded-lg border border-zinc-150">
                    {job.description}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-zinc-400">Loading job details...</p>
            )}
          </div>
        </div>

        {/* Right Column (Company Research Brief, Cover Letter Studio, Tailored Resume) */}
        <div className="xl:col-span-7 space-y-6 flex flex-col">
          {/* SECTION 1: Company & Job Research Brief */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-150 pb-3">
              <div className="flex items-center gap-2">
                <Building2 size={17} className="text-indigo-600" />
                <h2 className="text-sm font-bold text-zinc-900">Company &amp; Role Research Brief</h2>
              </div>
              <div className="flex items-center gap-2">
                {researchData && (
                  <span className="text-[11px] text-zinc-400 flex items-center gap-1">
                    <Clock size={11} /> {new Date(researchData.retrieval_date || researchData.created_at).toLocaleDateString()}
                  </span>
                )}
                <button
                  onClick={handleRefreshResearch}
                  disabled={isResearchLoading}
                  className="inline-flex items-center gap-1 text-xs px-2.5 py-1 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 font-medium rounded-md transition"
                >
                  <RefreshCw size={11} className={isResearchLoading ? "animate-spin" : ""} />
                  <span>{researchData ? "Refresh Brief" : "Generate Brief"}</span>
                </button>
              </div>
            </div>

            {isResearchLoading ? (
              <div className="py-8 flex flex-col items-center justify-center text-zinc-500 gap-2">
                <Loader2 size={24} className="animate-spin text-indigo-600" />
                <p className="text-xs font-medium">Synthesizing verified company intelligence &amp; architectural challenges...</p>
              </div>
            ) : researchData ? (
              <div className="space-y-4">
                {/* Epistemic Badges */}
                <div className="flex flex-wrap items-center gap-2 text-[11px]">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium flex items-center gap-1">
                    <ShieldCheck size={11} /> Verified Facts ({researchData.verified_facts?.length || 0})
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-medium flex items-center gap-1">
                    <Cpu size={11} /> Engineering Inferences ({researchData.inferred_insights?.length || 0})
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium flex items-center gap-1">
                    <AlertTriangle size={11} /> Unavailable Fields ({researchData.unavailable_fields?.length || 0})
                  </span>
                  {researchData.sources?.[0]?.url && (
                    <a
                      href={researchData.sources[0].url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-auto inline-flex items-center gap-1 text-[11px] text-indigo-600 hover:underline font-medium"
                    >
                      <span>Source: {researchData.sources[0].label}</span>
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>

                {/* Sub-tabs */}
                <div className="flex items-center gap-1 border-b border-zinc-150 overflow-x-auto pb-1 text-xs">
                  {[
                    { id: "overview", label: "Overview & Products" },
                    { id: "challenges", label: "Engineering Challenges" },
                    { id: "skills", label: "Key Skills" },
                    { id: "alignment", label: "Candidate Fit" },
                    { id: "interview", label: "Interview Prep" },
                    { id: "provenance", label: "Provenance & Facts" },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setResearchTab(tab.id as any)}
                      className={`px-3 py-1.5 rounded-md font-semibold transition whitespace-nowrap ${
                        researchTab === tab.id
                          ? "bg-zinc-900 text-white"
                          : "text-zinc-600 hover:bg-zinc-100"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab Contents */}
                <div className="text-xs text-zinc-700 leading-relaxed bg-zinc-50/50 p-4 rounded-xl border border-zinc-150 min-h-[140px] max-h-[220px] overflow-y-auto">
                  {researchTab === "overview" && (
                    <div className="space-y-3">
                      <div>
                        <h4 className="font-bold text-zinc-900 mb-1">Company Overview:</h4>
                        <p>{researchData.company_overview || "Overview not available."}</p>
                      </div>
                      {researchData.products_and_services?.length > 0 && (
                        <div>
                          <h4 className="font-bold text-zinc-900 mb-1">Products &amp; Core Services:</h4>
                          <ul className="list-disc pl-4 space-y-0.5">
                            {researchData.products_and_services.map((p: string, i: number) => (
                              <li key={i}>{p}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div>
                        <h4 className="font-bold text-zinc-900 mb-1">Industry &amp; Business Model:</h4>
                        <p>{researchData.industry_and_business_model || "Software & Technology."}</p>
                      </div>
                    </div>
                  )}

                  {researchTab === "challenges" && (
                    <div className="space-y-2">
                      <h4 className="font-bold text-zinc-900 mb-1">Engineering Challenges for this Role:</h4>
                      <ul className="list-disc pl-4 space-y-1.5">
                        {researchData.engineering_challenges?.map((c: string, i: number) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {researchTab === "skills" && (
                    <div className="space-y-2">
                      <h4 className="font-bold text-zinc-900 mb-1">Prioritized Technical Skills:</h4>
                      <ul className="list-disc pl-4 space-y-1.5">
                        {researchData.key_skills_in_position?.map((s: string, i: number) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {researchTab === "alignment" && (
                    <div className="space-y-2">
                      <h4 className="font-bold text-zinc-900 mb-1">Candidate Profile Alignment:</h4>
                      <ul className="list-disc pl-4 space-y-1.5">
                        {researchData.candidate_relevant_experience?.map((a: string, i: number) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {researchTab === "interview" && (
                    <div className="space-y-2">
                      <h4 className="font-bold text-zinc-900 mb-1">Topics to Research Before Interview:</h4>
                      <ul className="list-disc pl-4 space-y-1.5">
                        {researchData.interview_topics_to_prep?.map((t: string, i: number) => (
                          <li key={i}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {researchTab === "provenance" && (
                    <div className="space-y-3">
                      <div>
                        <h4 className="font-bold text-emerald-800 mb-1 flex items-center gap-1">
                          <ShieldCheck size={12} /> Verified Facts:
                        </h4>
                        <ul className="list-disc pl-4 space-y-1 text-emerald-950">
                          {researchData.verified_facts?.map((f: any, i: number) => (
                            <li key={i}>{f.claim || f} <span className="text-[10px] text-zinc-400">({f.source || "Official"})</span></li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-bold text-blue-800 mb-1 flex items-center gap-1">
                          <Cpu size={12} /> AI Engineering Inferences:
                        </h4>
                        <ul className="list-disc pl-4 space-y-1 text-blue-950">
                          {researchData.inferred_insights?.map((inf: any, i: number) => (
                            <li key={i}>{inf.insight || inf} <span className="text-[10px] text-zinc-400">({inf.rationale || "Inference"})</span></li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-bold text-amber-800 mb-1 flex items-center gap-1">
                          <AlertTriangle size={12} /> Unavailable Fields (Confidential/Not Disclosed):
                        </h4>
                        <ul className="list-disc pl-4 space-y-1 text-amber-950">
                          {researchData.unavailable_fields?.map((u: string, i: number) => (
                            <li key={i}>{u}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-zinc-400 text-xs">
                No company research compiled yet. Click &quot;Generate Brief&quot; or start analysis to synthesize verified insights.
              </div>
            )}
          </div>

          {/* SECTION 2: Personalized Cover Letter Studio */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-150 pb-3">
              <div className="flex items-center gap-2">
                <FileText size={17} className="text-indigo-600" />
                <h2 className="text-sm font-bold text-zinc-900">Personalized Cover Letter Studio</h2>
                {clData?.version_number && (
                  <span className="px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 text-[10px] font-bold">
                    v{clData.version_number}
                  </span>
                )}
                {isClApproved && (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold flex items-center gap-1">
                    <CheckCheck size={11} /> Approved
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowClHistoryModal(true)}
                  className="inline-flex items-center gap-1 text-xs px-2.5 py-1 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 font-medium rounded-md transition"
                >
                  <History size={12} />
                  <span>Versions ({clVersions.length})</span>
                </button>
              </div>
            </div>

            {/* Controls: Style chips & Motivation input */}
            <div className="space-y-3 bg-zinc-50/60 p-3.5 rounded-xl border border-zinc-150">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-zinc-700">Writing Style:</span>
                  {[
                    { id: "concise", label: "Concise & Direct" },
                    { id: "technical", label: "Technical & Projects" },
                    { id: "startup", label: "Startup & Impact" },
                    { id: "formal", label: "Formal & Traditional" },
                  ].map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setClStyle(s.id)}
                      className={`text-[11px] px-2.5 py-1 rounded-md font-semibold transition ${
                        clStyle === s.id
                          ? "bg-zinc-900 text-white shadow-2xs"
                          : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-100"
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleGenerateCoverLetter}
                  disabled={isClGenerating}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition shadow-2xs disabled:opacity-50"
                >
                  <Sparkles size={12} className={isClGenerating ? "animate-spin" : ""} />
                  <span>{isClGenerating ? "Generating..." : clContent ? "Regenerate Letter" : "Generate Tailored Letter"}</span>
                </button>
              </div>

              {/* Candidate Motivation Angle */}
              <div>
                <label className="text-[11px] font-bold text-zinc-700 block mb-1">
                  Candidate Motivation &amp; Genuine Interest (Optional angle):
                </label>
                <input
                  type="text"
                  value={clMotivation}
                  onChange={(e) => setClMotivation(e.target.value)}
                  placeholder="e.g. Loved reading your engineering blog post on caching; excited to help scale backend APIs."
                  className="w-full text-xs p-2 bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-zinc-900 text-zinc-700"
                />
              </div>

              {/* Granular Projects to Feature */}
              {candidateProjects.length > 0 && (
                <div className="pt-1">
                  <span className="text-[11px] font-bold text-zinc-700 block mb-1">
                    Featured Verified Projects to Emphasize:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {candidateProjects.slice(0, 6).map((proj) => {
                      const isSelected = selectedProjects.includes(proj.id);
                      return (
                        <button
                          key={proj.id}
                          type="button"
                          onClick={() => toggleProjectSelection(proj.id)}
                          className={`text-[10px] px-2 py-0.5 rounded-md font-medium border transition ${
                            isSelected
                              ? "bg-indigo-50 border-indigo-300 text-indigo-700"
                              : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-100"
                          }`}
                        >
                          {isSelected ? "✓ " : "+ "}
                          {proj.title || proj.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Live Markdown Editor for Cover Letter */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-500">
                <span className="font-semibold text-zinc-700">Editable Letter Content:</span>
                <div className="flex items-center gap-3">
                  <span>{clContent.trim() ? `${clContent.trim().split(/\s+/).length} words` : "0 words"}</span>
                  <button
                    onClick={handleCopyCoverLetter}
                    className="inline-flex items-center gap-1 text-zinc-600 hover:text-zinc-900 font-medium"
                  >
                    {copiedCl ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                    <span>{copiedCl ? "Copied" : "Copy"}</span>
                  </button>
                </div>
              </div>

              <textarea
                value={clContent}
                onChange={(e) => setClContent(e.target.value)}
                placeholder="Click 'Generate Tailored Letter' above to write a personalized cover letter..."
                className="w-full text-xs p-3.5 bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-zinc-900 leading-relaxed text-zinc-800 min-h-[220px] max-h-[360px] resize-y font-sans"
              />
            </div>

            {/* Action Buttons: Save New Version, Approve, Download Dropdown */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-zinc-150">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveCoverLetterVersion}
                  disabled={isClSaving || !clContent}
                  className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold rounded-lg transition disabled:opacity-50"
                >
                  {isClSaving ? "Saving..." : "Save as New Version"}
                </button>
                <button
                  onClick={handleApproveCoverLetter}
                  disabled={!clData || isClApproved}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition border flex items-center gap-1.5 ${
                    isClApproved
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : "bg-white text-zinc-700 border-zinc-200 hover:bg-zinc-50"
                  }`}
                >
                  <CheckCheck size={13} className={isClApproved ? "text-emerald-600" : "text-zinc-400"} />
                  <span>{isClApproved ? "Approved ✓" : "Approve for Application"}</span>
                </button>
              </div>

              {clData && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleDownloadCoverLetter("pdf")}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-50 text-xs font-medium rounded-lg transition"
                  >
                    <Download size={11} /> PDF
                  </button>
                  <button
                    onClick={() => handleDownloadCoverLetter("md")}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-50 text-xs font-medium rounded-lg transition"
                  >
                    <Download size={11} /> Markdown
                  </button>
                  <button
                    onClick={() => handleDownloadCoverLetter("txt")}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-50 text-xs font-medium rounded-lg transition"
                  >
                    <Download size={11} /> TXT
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* (Tailored Resume has been elevated to the Full-Page Hero Workstation at the top) */}
        </div>
      </div>

      {/* MODAL: Version History Drawer / Modal */}
      {showClHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[85vh] flex flex-col shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-4 border-b border-zinc-150 flex items-center justify-between">
              <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
                <History size={16} className="text-indigo-600" />
                Cover Letter Version History ({clVersions.length})
              </h3>
              <button
                onClick={() => setShowClHistoryModal(false)}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              {clVersions.map((v, i) => (
                <div key={v.id} className="p-3 rounded-xl border border-zinc-200 bg-zinc-50/50 flex items-center justify-between gap-3 text-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-zinc-900">Version #{v.version_number}</span>
                      <span className="px-1.5 py-0.5 rounded bg-zinc-200 text-zinc-700 text-[10px] uppercase font-semibold">
                        {v.style}
                      </span>
                      {v.is_approved && (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-semibold">
                          Approved
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      {new Date(v.created_at).toLocaleString()} • {v.char_count} chars
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {i < clVersions.length - 1 && (
                      <button
                        onClick={() => handleCompareVersions(clVersions[i + 1].id, v.id)}
                        className="px-2 py-1 bg-white border border-zinc-200 text-zinc-700 rounded text-[11px] font-medium hover:bg-zinc-100"
                      >
                        Diff v{clVersions[i + 1].version_number}
                      </button>
                    )}
                    <button
                      onClick={() => handleRestoreVersion(v.id)}
                      className="px-2.5 py-1 bg-zinc-900 text-white rounded text-[11px] font-medium hover:bg-zinc-800"
                    >
                      Restore
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Diff View Modal */}
      {showClDiffModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-4 border-b border-zinc-150 flex items-center justify-between">
              <h3 className="text-sm font-bold text-zinc-900">Version Comparison Diff</h3>
              <button
                onClick={() => setShowClDiffModal(false)}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 leading-relaxed text-xs">
              <div className="flex flex-wrap gap-1 p-3 bg-zinc-50 rounded-xl border border-zinc-150 whitespace-pre-wrap">
                {diffTokens.map((token, i) => {
                  if (token.type === "added") {
                    return (
                      <span key={i} className="bg-emerald-100 text-emerald-800 font-medium px-1 rounded">
                        {token.text}
                      </span>
                    );
                  }
                  if (token.type === "removed") {
                    return (
                      <span key={i} className="bg-red-100 text-red-800 line-through px-1 rounded">
                        {token.text}
                      </span>
                    );
                  }
                  return <span key={i} className="text-zinc-700">{token.text} </span>;
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
