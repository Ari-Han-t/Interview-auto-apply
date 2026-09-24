"use client";

import { useState, useEffect, use } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "react-hot-toast";
import { apiFetch, apiPost, API_BASE } from "@/lib/api";
import { Download, ArrowLeft, GitBranch, Sparkles, CheckCircle2, Clock, AlertTriangle, Loader2, BookOpen, HelpCircle, FileText, ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";

interface Job {
  id: number;
  title: string;
  company: string;
  url: string | null;
  location: string | null;
  description: string | null;
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
  const [clPreview, setClPreview] = useState("");
  
  const [job, setJob] = useState<Job | null>(null);
  const [isLoadingJob, setIsLoadingJob] = useState(true);

  // Background analysis state
  const [appId, setAppId] = useState<number | null>(null);
  const [appStatus, setAppStatus] = useState<string>("");
  const [progress, setProgress] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, any>>({});
  const [expandedQa, setExpandedQa] = useState<Record<number, boolean>>({});

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
      setAppId(parseInt(searchAppId));
    }
  }, [searchAppId]);

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
            setAppStatus(appData.status);
            if (appData.user_instructions) setJobInstructions(appData.user_instructions);
            if (appData.status === "generated") {
              setGenerated(true);
            }
          } else if (forceAnalyze) {
            // Auto initialize
            handleStartAnalysis();
          }
        } catch (err) {
          if (forceAnalyze) {
            handleStartAnalysis();
          }
        }
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

  // Polling hook
  useEffect(() => {
    if (!appId) return;

    // Helper to load final/latest data
    const fetchProgress = async () => {
      try {
        const res = await apiFetch<any>(`/api/v1/applications/${appId}/progress`);
        setProgress(res.progress || {});
        setResults(res.results || {});
        setAppStatus(res.status);

        if (res.results?.tailoring_resume?.path) {
          setResumePreview(res.results.tailoring_resume.path);
        }
        if (res.results?.cover_letter?.preview) {
          setClPreview(res.results.cover_letter.preview);
        }

        if (res.status === "generated") {
          setGenerated(true);
          setApplicationId(appId);
          setIsGenerating(false);
          setStatusText("");
        }
      } catch (err) {
        console.error("Progress polling error:", err);
      }
    };

    // If already complete, just fetch once and don't poll
    if (appStatus === "generated" || appStatus === "applied" || appStatus === "applying") {
      fetchProgress();
      return;
    }

    setIsGenerating(true);
    setStatusText("Running background analyses concurrently...");

    fetchProgress(); // immediate call
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
      toast.error(`Cannot generate materials: ${job.rejection_reason}`);
      return;
    }
    
    // Start the analysis pipeline
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

  const renderChecklistItem = (item: { key: string; label: string }) => {
    const status = progress[item.key] || "pending";
    const errorMsg = progress[item.key + "_error"];

    let icon = <Clock size={16} className="text-zinc-300" />;
    let textClass = "text-zinc-400";

    if (status === "completed") {
      icon = <CheckCircle2 size={16} className="text-emerald-500 fill-emerald-50" />;
      textClass = "text-zinc-700 font-semibold";
    } else if (status === "running") {
      icon = <Loader2 size={16} className="text-indigo-600 animate-spin" />;
      textClass = "text-indigo-600 font-medium animate-pulse";
    } else if (status === "failed") {
      icon = <AlertTriangle size={16} className="text-red-500" />;
      textClass = "text-red-500 font-semibold";
    }

    return (
      <div key={item.key} className="flex items-center gap-3 text-xs py-1.5 border-b border-zinc-50 last:border-0">
        {icon}
        <span className={textClass}>{item.label}</span>
        {errorMsg && (
          <span className="text-[10px] text-red-400 ml-auto max-w-[200px] truncate" title={errorMsg}>
            {errorMsg}
          </span>
        )}
      </div>
    );
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
            <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Tailoring Room</h1>
            <p className="text-sm text-zinc-500">
              {job ? `${job.title} at ${job.company}` : `Job #${id}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
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
              disabled={Boolean(isLoadingJob || (job && job.eligible === false))}
              className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 disabled:opacity-50 transition-colors shadow-md"
            >
              <Sparkles size={14} />
              Analyse & Apply (Concurrent)
            </button>
          )}
        </div>
      </div>

      {/* Context inputs: GitHub + per-job instructions */}
      {!generated && appStatus !== "generating" && (
        <div className="bg-white border border-zinc-200 shadow-sm p-4 rounded-xl grid grid-cols-1 md:grid-cols-[220px_1fr] gap-4">
          <div className="grid gap-1.5">
            <label className="text-xs font-bold text-zinc-700 flex items-center gap-1.5">
              <GitBranch size={13} className="text-indigo-600" /> GitHub username
            </label>
            <input
              type="text"
              value={githubUsername}
              onChange={(e) => setGithubUsername(e.target.value)}
              placeholder="your-handle"
              className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full"
            />
            <p className="text-[10px] text-zinc-400">Used to refresh projects before tailoring (if stale).</p>
          </div>
          <div className="grid gap-1.5">
            <label className="text-xs font-bold text-zinc-700">Instructions for this job</label>
            <textarea
              value={jobInstructions}
              onChange={(e) => setJobInstructions(e.target.value)}
              rows={3}
              placeholder="Anything the AI should know for THIS role — tone, projects to highlight, sections to emphasize, companies to reference… (overrides your global instructions)"
              className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full resize-y"
            />
            <p className="text-[10px] text-zinc-400">Draft is saved locally. Global instructions live in Settings.</p>
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 flex-1">
        {/* Left Column (Job Details + Checklist) */}
        <div className="xl:col-span-5 space-y-6 flex flex-col">
          {/* Progress Checklist Tracker */}
          {appId && (
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-4">
              <h2 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
                <Loader2 size={16} className={`text-indigo-600 ${appStatus === "generating" ? "animate-spin" : ""}`} />
                Analysis Pipeline Progress
              </h2>
              <div className="bg-zinc-50 border border-zinc-150 rounded-lg p-3 space-y-1">
                {checklistItems.map(renderChecklistItem)}
              </div>
            </div>
          )}

          {/* Job Details Card */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 flex-1 flex flex-col overflow-hidden">
            <h2 className="text-sm font-bold text-zinc-900 border-b border-zinc-100 pb-3 mb-4">
              Job Description
            </h2>
            {isLoadingJob ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              </div>
            ) : job ? (
              <div className="text-sm text-zinc-705 space-y-4 flex-1 overflow-y-auto pr-2">
                {job.eligible === false && (
                  <div className="bg-red-50 border border-red-200/60 rounded-xl p-4 space-y-2 text-red-700">
                    <h3 className="text-xs font-bold uppercase tracking-wider">Ineligible</h3>
                    <p className="text-xs leading-relaxed">{job.rejection_reason}</p>
                  </div>
                )}

                {/* Match percentage / Skill gap */}
                {results.matching_resume ? (
                  <div className="bg-indigo-50/50 border border-indigo-100/80 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">Match Overview</h3>
                      <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-lg">
                        {results.matching_resume.match_percentage || 0}% Match Score
                      </span>
                    </div>
                    {results.matching_resume.missing_skills && results.matching_resume.missing_skills.length > 0 && (
                      <div className="space-y-1.5">
                        <p className="text-xs font-semibold text-zinc-700">Skill Gap identified:</p>
                        <div className="flex flex-wrap gap-1">
                          {results.matching_resume.missing_skills.map((s: string, idx: number) => (
                            <span key={idx} className="bg-amber-50 border border-amber-200/50 text-amber-800 text-[10px] px-2 py-0.5 rounded-md font-medium">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {results.matching_resume.strengths && results.matching_resume.strengths.length > 0 && (
                      <div className="text-xs space-y-1">
                        <p className="font-semibold text-zinc-700">Key Match Strengths:</p>
                        <ul className="list-disc pl-4 text-zinc-600 space-y-0.5">
                          {results.matching_resume.strengths.slice(0, 3).map((s: string, idx: number) => (
                            <li key={idx}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : appStatus === "generating" ? (
                  <div className="animate-pulse bg-zinc-50 border border-zinc-150 rounded-xl p-4 space-y-3">
                    <div className="h-4 bg-zinc-200 rounded w-1/3"></div>
                    <div className="h-3 bg-zinc-200 rounded w-5/6"></div>
                    <div className="h-3 bg-zinc-200 rounded w-3/4"></div>
                  </div>
                ) : null}

                {/* Salary Info (from parsing_job) */}
                {results.parsing_job && results.parsing_job.salary_range && (
                  <div className="bg-emerald-50/50 border border-emerald-150 rounded-xl p-3 text-xs text-emerald-900 font-medium">
                    Estimated Salary: {results.parsing_job.salary_range}
                  </div>
                )}

                <div className="space-y-1.5 pt-2">
                  <p><strong className="text-zinc-950 font-bold">Role:</strong> {job.title}</p>
                  <p><strong className="text-zinc-950 font-bold">Company:</strong> {job.company}</p>
                  {job.location && <p><strong className="text-zinc-950 font-bold">Location:</strong> {job.location}</p>}
                </div>
                <div className="mt-4 whitespace-pre-wrap leading-relaxed text-zinc-600 border-t border-zinc-100 pt-4">
                  {job.description}
                </div>
              </div>
            ) : (
              <p className="text-red-500">Job not found.</p>
            )}
          </div>
        </div>

        {/* Right Column (Tailored Outputs, Research, Interview Prep) */}
        <div className="xl:col-span-7 space-y-6 flex flex-col overflow-hidden">
          {/* progressive results: Company Research */}
          {results.company_research ? (
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-3">
              <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-1.5">
                <BookOpen size={16} className="text-indigo-600" />
                Company Mission & Culture Research
              </h3>
              <div className="text-xs text-zinc-650 leading-relaxed whitespace-pre-wrap max-h-[180px] overflow-y-auto border border-zinc-100 rounded-lg p-3 bg-zinc-50/50">
                {results.company_research}
              </div>
            </div>
          ) : appStatus === "generating" ? (
            <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-3 animate-pulse">
              <div className="h-4 bg-zinc-200 rounded w-1/4"></div>
              <div className="h-3 bg-zinc-200 rounded w-full"></div>
              <div className="h-3 bg-zinc-200 rounded w-5/6"></div>
            </div>
          ) : null}

          {/* progressive results: Interview Questions Prep */}
          {results.interview_prep ? (
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5 space-y-3">
              <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-1.5">
                <HelpCircle size={16} className="text-indigo-600" />
                Tailored Interview Questions Prep
              </h3>
              <div className="space-y-2 max-h-[220px] overflow-y-auto pr-2">
                {results.interview_prep.map((item: { question: string; answer: string }, idx: number) => {
                  const isExpanded = expandedQa[idx];
                  return (
                    <div key={idx} className="border border-zinc-150 rounded-lg overflow-hidden bg-zinc-50/30 text-xs">
                      <button
                        onClick={() => toggleQa(idx)}
                        className="w-full flex items-center justify-between p-3 font-semibold text-zinc-800 text-left bg-zinc-50 border-b border-zinc-100 hover:bg-zinc-100/80 transition-colors"
                      >
                        <span>Q{idx+1}: {item.question}</span>
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      {isExpanded && (
                        <div className="p-3 bg-white text-zinc-600 leading-relaxed whitespace-pre-wrap">
                          <strong>A:</strong> {item.answer}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : appStatus === "generating" ? (
            <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-3 animate-pulse">
              <div className="h-4 bg-zinc-200 rounded w-1/4"></div>
              <div className="h-3 bg-zinc-200 rounded w-3/4"></div>
            </div>
          ) : null}

          {/* Generated Tailored Materials Panel */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 flex flex-col min-h-[420px] flex-1 overflow-hidden">
            <h2 className="text-sm font-bold text-zinc-900 border-b border-zinc-100 pb-3 mb-4 flex items-center gap-2">
              <FileText size={16} className="text-indigo-600" />
              Generated Materials (Tailored LaTeX)
            </h2>

            {!generated && !isGenerating ? (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 space-y-3 px-8 text-center">
                <Sparkles size={32} className="text-zinc-300 animate-pulse" />
                <p className="text-sm font-medium">Ready to generate materials</p>
                <p className="text-xs text-zinc-400">
                  Click &quot;Analyse & Apply (Concurrent)&quot; to trigger the parallel pipeline execution and generate tailored resume, cover letter, company insights, and Q&A.
                </p>
              </div>
            ) : isGenerating && !generated ? (
              <div className="flex-1 flex flex-col items-center justify-center text-indigo-500 space-y-4">
                <Loader2 size={36} className="animate-spin text-indigo-600" />
                <p className="font-semibold text-zinc-700 animate-pulse text-xs">{statusText}</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                {/* Resume section */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider">Tailored Resume (PDF &amp; LaTeX)</h3>
                    {applicationId && (
                      <div className="flex items-center gap-3">
                        <a
                          href={`${API_BASE}/api/v1/applications/${applicationId}/resume.tex`}
                          download={`resume_${job?.company || "tailored"}.tex`}
                          className="inline-flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-900 font-semibold"
                        >
                          <Download size={12} /> Source (.tex)
                        </a>
                        <a
                          href={`${API_BASE}/api/v1/applications/${applicationId}/resume.pdf`}
                          download={`resume_${job?.company || "tailored"}.pdf`}
                          target="_blank"
                          className="inline-flex items-center gap-1 text-xs text-indigo-650 hover:text-indigo-800 font-bold"
                        >
                          <Download size={12} /> Download PDF
                        </a>
                      </div>
                    )}
                  </div>
                  <div className="bg-zinc-50 rounded-lg border border-zinc-200 h-[280px] w-full overflow-hidden">
                    {applicationId ? (
                      <iframe 
                        src={`${API_BASE}/api/v1/applications/${applicationId}/resume.pdf`} 
                        className="w-full h-full"
                        title="Resume PDF Preview"
                      />
                    ) : (
                      <pre className="p-4 text-[10px] overflow-x-auto whitespace-pre-wrap h-full overflow-y-auto text-zinc-600 font-mono">
                        {resumePreview || "No resume text generated."}
                      </pre>
                    )}
                  </div>
                </div>

                {/* Cover letter section */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider">Cover Letter</h3>
                    <button
                      onClick={() => handleDownload(clPreview, `cover_letter_${job?.company || "tailored"}.md`)}
                      className="inline-flex items-center gap-1 text-xs text-indigo-650 hover:text-indigo-800 font-bold"
                    >
                      <Download size={12} /> Download CL
                    </button>
                  </div>
                  <pre className="bg-zinc-50 p-4 rounded-lg text-xs overflow-x-auto border border-zinc-200 whitespace-pre-wrap max-h-[180px] overflow-y-auto text-zinc-650">
                    {clPreview || "Cover letter generating..."}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
