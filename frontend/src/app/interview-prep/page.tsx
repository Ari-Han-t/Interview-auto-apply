"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch, apiPost, API_BASE } from "@/lib/api";
import { toast } from "react-hot-toast";
import {
  GraduationCap,
  Sparkles,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  ArrowRight,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Award,
  Clock,
  Briefcase,
  History,
  Target,
  ExternalLink,
  HelpCircle,
  Lightbulb,
  Check,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";

interface JobOption {
  id: number;
  title: string;
  company: string;
  location?: string;
}

interface StarBreakdown {
  situation?: string;
  task?: string;
  action?: string;
  result?: string;
}

interface InterviewQuestionData {
  id: number;
  job_id: number;
  category: string;
  question: string;
  difficulty: string;
  is_verified_company_question: boolean;
  source_provenance?: string | null;
  why_it_matters?: string | null;
  what_good_answer_demonstrates?: string | null;
  suggested_answer?: string | null;
  star_breakdown?: StarBreakdown | null;
  likely_follow_ups?: string[] | null;
  common_mistakes?: string[] | null;
  practice_resources?: { title: string; url?: string; description?: string }[] | null;
}

interface CategoryInfo {
  id: string;
  label?: string;
  name?: string;
  icon?: string;
  description?: string;
}

const DEFAULT_CATEGORIES: CategoryInfo[] = [
  { id: "resume_walkthrough", label: "Resume & Projects", name: "Resume & Projects" },
  { id: "programming_fundamentals", label: "Programming Fundamentals", name: "Programming Fundamentals" },
  { id: "dsa", label: "Data Structures & Algorithms", name: "Data Structures & Algorithms" },
  { id: "languages_frameworks", label: "Languages & Frameworks", name: "Languages & Frameworks" },
  { id: "role_specific", label: "Role-Specific Topics", name: "Role-Specific Topics" },
  { id: "software_practices", label: "Software Engineering Practices", name: "Software Engineering Practices" },
  { id: "system_design", label: "System Design", name: "System Design" },
  { id: "behavioral", label: "Behavioral & STAR", name: "Behavioral & STAR" },
  { id: "company_product", label: "Company & Product", name: "Company & Product" },
];

interface MockSessionListItem {
  id: number;
  job_id: number;
  company: string;
  role: string;
  title: string;
  category: string;
  difficulty: string;
  status: string;
  total_questions: number;
  answered_count: number;
  overall_score?: number | null;
  created_at: string;
}

interface MockSessionDetail {
  id: number;
  job_id: number;
  company: string;
  role: string;
  title: string;
  category: string;
  difficulty: string;
  status: string;
  questions: any[];
  current_question_index: number;
  answers: Record<string, { answer_text: string; evaluation?: any; eval_result?: any; score?: number; feedback?: string; strengths?: string[]; improvements?: string[]; model_answer?: string; retry_count?: number }>;
  overall_score?: number | null;
  overall_feedback?: string | null;
  created_at: string;
}

function InterviewPrepContent() {
  const searchParams = useSearchParams();
  const initialJobId = searchParams.get("jobId");

  // Global State
  const [jobs, setJobs] = useState<JobOption[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(
    initialJobId ? parseInt(initialJobId, 10) : null
  );
  const [categories, setCategories] = useState<CategoryInfo[]>(DEFAULT_CATEGORIES);
  const [activeTab, setActiveTab] = useState<"study" | "mock">("study");

  // Study Mode State
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [questions, setQuestions] = useState<InterviewQuestionData[]>([]);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [isRefreshingQuestions, setIsRefreshingQuestions] = useState(false);
  const [expandedQuestionId, setExpandedQuestionId] = useState<number | null>(null);

  // Mock Session Setup State
  const [mockCategory, setMockCategory] = useState<string>("all");
  const [mockDifficulty, setMockDifficulty] = useState<string>("medium");
  const [mockQuestionCount, setMockQuestionCount] = useState<number>(5);
  const [isStartingSession, setIsStartingSession] = useState(false);

  // Active Mock Session State
  const [activeSession, setActiveSession] = useState<MockSessionDetail | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [candidateAnswer, setCandidateAnswer] = useState<string>("");
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState<boolean>(false);
  const [lastEvaluation, setLastEvaluation] = useState<any | null>(null);

  // Past Sessions History
  const [historySessions, setHistorySessions] = useState<MockSessionListItem[]>([]);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);

  // 1. Initial Load: Jobs and Categories
  useEffect(() => {
    fetchJobs();
    fetchCategories();
  }, []);

  // 2. Load Questions when Job changes
  useEffect(() => {
    if (selectedJobId) {
      fetchQuestions(selectedJobId, selectedCategory);
      fetchSessionHistory(selectedJobId);
    }
  }, [selectedJobId, selectedCategory]);

  const fetchJobs = async () => {
    try {
      const data = await apiFetch<any[]>("/api/v1/jobs/");
      const mapped = data.map((j) => ({
        id: j.id,
        title: j.title,
        company: j.company,
        location: j.location,
      }));
      setJobs(mapped);
      if (!selectedJobId && mapped.length > 0) {
        setSelectedJobId(mapped[0].id);
      }
    } catch {
      // ignore or toast
    }
  };

  const fetchCategories = async () => {
    try {
      const data = await apiFetch<CategoryInfo[]>("/api/v1/interview-prep/categories");
      if (Array.isArray(data) && data.length > 0) {
        setCategories(data);
      } else {
        setCategories(DEFAULT_CATEGORIES);
      }
    } catch {
      setCategories(DEFAULT_CATEGORIES);
    }
  };

  const fetchQuestions = async (jobId: number, category: string) => {
    setIsLoadingQuestions(true);
    try {
      const catParam = category && category !== "all" ? `?category=${category}` : "";
      const data = await apiFetch<InterviewQuestionData[]>(
        `/api/v1/interview-prep/job/${jobId}/questions${catParam}`
      );
      setQuestions(data);
    } catch (err: any) {
      toast.error("Failed to load interview questions");
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  const handleRefreshQuestions = async () => {
    if (!selectedJobId) return;
    setIsRefreshingQuestions(true);
    try {
      const data = await apiPost<InterviewQuestionData[]>(
        `/api/v1/interview-prep/job/${selectedJobId}/generate`,
        { force_refresh: true }
      );
      setQuestions(data);
      toast.success("Interview questions refreshed and calibrated for this job!");
    } catch (err: any) {
      toast.error(err.message || "Failed to refresh questions");
    } finally {
      setIsRefreshingQuestions(false);
    }
  };

  const fetchSessionHistory = async (jobId?: number) => {
    try {
      const q = jobId ? `?job_id=${jobId}` : "";
      const data = await apiFetch<MockSessionListItem[]>(`/api/v1/interview-prep/sessions${q}`);
      setHistorySessions(data);
    } catch {
      // ignore
    }
  };

  const handleStartMockSession = async () => {
    if (!selectedJobId) {
      toast.error("Please select a target job first");
      return;
    }
    setIsStartingSession(true);
    try {
      const session = await apiPost<any>("/api/v1/interview-prep/sessions", {
        job_id: selectedJobId,
        category: mockCategory,
        difficulty: mockDifficulty,
        question_count: mockQuestionCount,
      });

      // Fetch full session details
      const detail = await apiFetch<MockSessionDetail>(
        `/api/v1/interview-prep/sessions/${session.id}`
      );
      setActiveSession(detail);
      setCurrentQuestionIndex(0);
      setCandidateAnswer("");
      setLastEvaluation(null);
      setActiveTab("mock");
      toast.success("Mock interview session started!");
    } catch (err: any) {
      toast.error(err.message || "Failed to start mock session");
    } finally {
      setIsStartingSession(false);
    }
  };

  const handleResumeSession = async (sessionId: number) => {
    try {
      const detail = await apiFetch<MockSessionDetail>(
        `/api/v1/interview-prep/sessions/${sessionId}`
      );
      setActiveSession(detail);
      const currIdx = detail.current_question_index || 0;
      setCurrentQuestionIndex(currIdx);
      const ansObj = detail.answers?.[String(currIdx)];
      setCandidateAnswer(ansObj?.answer_text || "");
      setLastEvaluation(ansObj ? (ansObj.eval_result || ansObj.evaluation || ansObj) : null);
      setActiveTab("mock");
      setShowHistoryDrawer(false);
    } catch (err: any) {
      toast.error(err.message || "Failed to resume session");
    }
  };

  const handleSubmitAnswer = async () => {
    if (!activeSession) return;
    if (!candidateAnswer.trim() || candidateAnswer.trim().length < 20) {
      toast.error("Please provide a thorough answer (at least 20 characters)");
      return;
    }

    setIsSubmittingAnswer(true);
    try {
      const evalData = await apiPost<any>(
        `/api/v1/interview-prep/sessions/${activeSession.id}/answer`,
        {
          question_index: currentQuestionIndex,
          answer_text: candidateAnswer.trim(),
        }
      );
      const resObj = evalData.eval_result || evalData;
      setLastEvaluation(resObj);
      toast.success(`Answer scored: ${resObj.score}/100!`);

      // Refresh session state to get updated overall score and completion status
      const updatedDetail = await apiFetch<MockSessionDetail>(
        `/api/v1/interview-prep/sessions/${activeSession.id}`
      );
      setActiveSession(updatedDetail);
      fetchSessionHistory(selectedJobId || undefined);
    } catch (err: any) {
      toast.error(err.message || "Failed to evaluate answer");
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleNextQuestion = () => {
    if (!activeSession) return;
    const nextIdx = currentQuestionIndex + 1;
    if (nextIdx < activeSession.questions.length) {
      setCurrentQuestionIndex(nextIdx);
      const ansObj = activeSession.answers?.[String(nextIdx)];
      setCandidateAnswer(ansObj?.answer_text || "");
      setLastEvaluation(ansObj ? (ansObj.eval_result || ansObj.evaluation || ansObj) : null);
    }
  };

  const handlePrevQuestion = () => {
    if (!activeSession) return;
    const prevIdx = currentQuestionIndex - 1;
    if (prevIdx >= 0) {
      setCurrentQuestionIndex(prevIdx);
      const ansObj = activeSession.answers?.[String(prevIdx)];
      setCandidateAnswer(ansObj?.answer_text || "");
      setLastEvaluation(ansObj ? (ansObj.eval_result || ansObj.evaluation || ansObj) : null);
    }
  };

  const handleRetryQuestion = () => {
    setLastEvaluation(null);
    toast("Refine your response and resubmit for constructive feedback", { icon: "✍️" });
  };

  const currentJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
              Interview Preparation Workspace
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              Role & Seniority Calibrated
            </span>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            Master verified questions across 9 technical & behavioral dimensions with grounded candidate STAR answers and interactive mock interviews.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Target Job Selector */}
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 border border-zinc-300 rounded-lg shadow-xs">
            <Briefcase size={14} className="text-zinc-500" />
            <select
              value={selectedJobId || ""}
              onChange={(e) => setSelectedJobId(Number(e.target.value))}
              className="text-xs font-semibold text-zinc-800 bg-transparent focus:outline-none cursor-pointer max-w-xs truncate"
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.company} - {j.title}
                </option>
              ))}
            </select>
          </div>

          {/* Past Sessions History Toggle */}
          <button
            onClick={() => setShowHistoryDrawer(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-zinc-700 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 shadow-xs transition-colors"
          >
            <History size={14} className="text-zinc-500" />
            Session History ({historySessions.length})
          </button>
        </div>
      </div>

      {/* Main Mode Navigation: Study Question Bank vs Interactive Mock Session */}
      <div className="flex items-center gap-2 border-b border-zinc-200">
        <button
          onClick={() => setActiveTab("study")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "study"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          <BookOpen size={15} />
          Curated Question Bank & Guides ({questions.length})
        </button>
        <button
          onClick={() => setActiveTab("mock")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "mock"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-zinc-600 hover:text-zinc-900"
          }`}
        >
          <GraduationCap size={15} />
          Interactive Mock Interview Session
          {activeSession && activeSession.status === "in_progress" && (
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          )}
        </button>
      </div>

      {/* ================= MODE 1: STUDY QUESTION BANK ================= */}
      {activeTab === "study" && (
        <div className="space-y-6">
          {/* Category Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-zinc-100">
            <button
              onClick={() => setSelectedCategory("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === "all"
                  ? "bg-zinc-900 text-white shadow-xs"
                  : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50"
              }`}
            >
              All Categories
            </button>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  selectedCategory === cat.id
                    ? "bg-zinc-900 text-white shadow-xs"
                    : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50"
                }`}
              >
                {cat.label || cat.name || cat.id}
              </button>
            ))}
          </div>

          {/* Action Bar: Question Count & Refresh */}
          <div className="flex items-center justify-between">
            <div className="text-xs text-zinc-500">
              Showing <span className="font-semibold text-zinc-800">{questions.length}</span> calibrated questions for{" "}
              <strong className="text-zinc-800">{currentJob?.company || "selected role"}</strong>.
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={isRefreshingQuestions}
                onClick={handleRefreshQuestions}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-700 bg-white border border-zinc-200 rounded-lg hover:bg-zinc-50 shadow-xs transition-colors disabled:opacity-50"
              >
                <RefreshCw size={13} className={isRefreshingQuestions ? "animate-spin" : ""} />
                {isRefreshingQuestions ? "Calibrating..." : "Regenerate Questions"}
              </button>
              <button
                onClick={() => {
                  setMockCategory(selectedCategory);
                  setActiveTab("mock");
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors"
              >
                <Play size={13} />
                Practice In Mock Interview
              </button>
            </div>
          </div>

          {/* Question List */}
          {isLoadingQuestions ? (
            <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center text-zinc-400">
              Loading calibrated questions and model answers...
            </div>
          ) : questions.length === 0 ? (
            <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center">
              <HelpCircle size={36} className="mx-auto text-zinc-300 mb-3" />
              <h3 className="text-sm font-semibold text-zinc-900">No questions found</h3>
              <p className="text-xs text-zinc-500 mt-1">
                Click &ldquo;Regenerate Questions&rdquo; to build calibrated questions for this role.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {questions.map((q, idx) => {
                const isExpanded = expandedQuestionId === q.id;

                return (
                  <div
                    key={q.id}
                    className="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-xs hover:border-zinc-300 transition-all"
                  >
                    {/* Question Header */}
                    <div
                      onClick={() => setExpandedQuestionId(isExpanded ? null : q.id)}
                      className="p-4 flex items-start justify-between gap-4 cursor-pointer hover:bg-zinc-50/50 transition-colors"
                    >
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700">
                            Q{idx + 1}
                          </span>
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 capitalize">
                            {q.category.replace(/_/g, " ")}
                          </span>
                          <span
                            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full capitalize ${
                              q.difficulty === "easy"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                                : q.difficulty === "hard"
                                ? "bg-rose-50 text-rose-700 border border-rose-100"
                                : "bg-amber-50 text-amber-700 border border-amber-100"
                            }`}
                          >
                            {q.difficulty}
                          </span>

                          {/* Epistemic Honesty Badge */}
                          {q.is_verified_company_question ? (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                              ✓ Verified Company Question
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-zinc-50 text-zinc-500 border border-zinc-200">
                              Anticipated Role Question
                            </span>
                          )}
                        </div>

                        <h3 className="text-sm font-bold text-zinc-900 tracking-tight leading-snug">
                          {q.question}
                        </h3>
                      </div>

                      <button className="text-zinc-400 hover:text-zinc-600 p-1">
                        {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </button>
                    </div>

                    {/* Expanded Detail Panel */}
                    {isExpanded && (
                      <div className="px-5 pb-5 pt-2 border-t border-zinc-100 space-y-4 text-xs bg-zinc-50/30">
                        {/* Why it matters & What good answer demonstrates */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {q.why_it_matters && (
                            <div className="p-3 bg-white rounded-lg border border-zinc-200">
                              <div className="font-bold text-zinc-800 flex items-center gap-1.5 mb-1">
                                <Target size={13} className="text-indigo-600" />
                                Why It Matters
                              </div>
                              <p className="text-zinc-600 leading-relaxed text-[11px]">
                                {q.why_it_matters}
                              </p>
                            </div>
                          )}

                          {q.what_good_answer_demonstrates && (
                            <div className="p-3 bg-white rounded-lg border border-zinc-200">
                              <div className="font-bold text-zinc-800 flex items-center gap-1.5 mb-1">
                                <Sparkles size={13} className="text-emerald-600" />
                                What a Good Answer Demonstrates
                              </div>
                              <p className="text-zinc-600 leading-relaxed text-[11px]">
                                {q.what_good_answer_demonstrates}
                              </p>
                            </div>
                          )}
                        </div>

                        {/* STAR Breakdown for Behavioral Questions */}
                        {(q.star_breakdown || (q as any).star_framework) && (() => {
                          const star = q.star_breakdown || (q as any).star_framework;
                          return (
                            <div className="p-3.5 bg-indigo-50/60 rounded-xl border border-indigo-100 space-y-2">
                              <div className="font-bold text-indigo-950 flex items-center gap-1.5 text-xs">
                                <Award size={14} className="text-indigo-600" />
                                STAR Method Formulation
                              </div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                                {star.situation && (
                                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                                    <span className="font-bold text-indigo-900 block mb-0.5">Situation</span>
                                    <span className="text-zinc-600">{star.situation}</span>
                                  </div>
                                )}
                                {star.task && (
                                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                                    <span className="font-bold text-indigo-900 block mb-0.5">Task</span>
                                    <span className="text-zinc-600">{star.task}</span>
                                  </div>
                                )}
                                {star.action && (
                                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                                    <span className="font-bold text-indigo-900 block mb-0.5">Action</span>
                                    <span className="text-zinc-600">{star.action}</span>
                                  </div>
                                )}
                                {star.result && (
                                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100">
                                    <span className="font-bold text-indigo-900 block mb-0.5">Result</span>
                                    <span className="text-zinc-600">{star.result}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Suggested Candidate Answer */}
                        {q.suggested_answer && (
                          <div className="p-3.5 bg-white rounded-xl border border-zinc-200 space-y-1.5">
                            <div className="font-bold text-zinc-900 flex items-center gap-1.5 text-xs">
                              <CheckCircle2 size={14} className="text-teal-600" />
                              Suggested Answer (Grounded in Candidate Experience)
                            </div>
                            <p className="text-zinc-700 leading-relaxed text-xs whitespace-pre-line">
                              {q.suggested_answer}
                            </p>
                          </div>
                        )}

                        {/* Common Mistakes & Likely Follow-ups */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {q.common_mistakes && q.common_mistakes.length > 0 && (
                            <div className="p-3 bg-rose-50/50 rounded-lg border border-rose-100">
                              <div className="font-bold text-rose-950 flex items-center gap-1.5 mb-1.5">
                                <AlertTriangle size={13} className="text-rose-600" />
                                Common Pitfalls to Avoid
                              </div>
                              <ul className="space-y-1 text-[11px] text-rose-900 list-disc list-inside">
                                {q.common_mistakes.map((m, mIdx) => (
                                  <li key={mIdx}>{m}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {q.likely_follow_ups && q.likely_follow_ups.length > 0 && (
                            <div className="p-3 bg-amber-50/50 rounded-lg border border-amber-100">
                              <div className="font-bold text-amber-950 flex items-center gap-1.5 mb-1.5">
                                <Lightbulb size={13} className="text-amber-600" />
                                Likely Follow-up Questions
                              </div>
                              <ul className="space-y-1 text-[11px] text-amber-900 list-disc list-inside">
                                {q.likely_follow_ups.map((f, fIdx) => (
                                  <li key={fIdx}>{f}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>

                        {/* Curated Practice & Reference Resources */}
                        {q.practice_resources && q.practice_resources.length > 0 && (
                          <div className="p-3 bg-white rounded-xl border border-zinc-200 space-y-2">
                            <div className="font-bold text-zinc-900 flex items-center gap-1.5 text-xs">
                              <BookOpen size={13} className="text-indigo-600" />
                              Useful Practice & Reference Resources
                            </div>
                            <div className="flex flex-wrap gap-2 pt-0.5">
                              {q.practice_resources.map((res: any, rIdx: number) => (
                                <a
                                  key={rIdx}
                                  href={res.url || "#"}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-indigo-700 bg-indigo-50/70 hover:bg-indigo-100 rounded-lg border border-indigo-200 transition-colors"
                                >
                                  <span>{res.title || "Study Guide"}</span>
                                  <ExternalLink size={11} className="text-indigo-500" />
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ================= MODE 2: INTERACTIVE MOCK INTERVIEW SIMULATOR ================= */}
      {activeTab === "mock" && (
        <div className="space-y-6">
          {/* Active Session vs Setup Form */}
          {!activeSession ? (
            <div className="max-w-xl mx-auto bg-white p-6 rounded-2xl border border-zinc-200 shadow-sm space-y-5">
              <div className="text-center space-y-1">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-2">
                  <GraduationCap size={22} />
                </div>
                <h2 className="text-lg font-bold text-zinc-900 tracking-tight">
                  Configure Mock Interview Session
                </h2>
                <p className="text-xs text-zinc-500">
                  Simulate real technical or behavioral interviews one question at a time with instant AI scoring.
                </p>
              </div>

              <div className="space-y-3.5 text-xs">
                {/* Job Info Card */}
                <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-zinc-900">{currentJob?.company || "Target Company"}</div>
                    <div className="text-zinc-500 text-[11px]">{currentJob?.title || "Role"}</div>
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-zinc-200 text-zinc-700">
                    Active Job
                  </span>
                </div>

                {/* Category Selection */}
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">Question Category</label>
                  <select
                    value={mockCategory}
                    onChange={(e) => setMockCategory(e.target.value)}
                    className="w-full px-3 py-2 border border-zinc-200 rounded-lg bg-white"
                  >
                    <option value="all">Mixed / Comprehensive (All 9 Categories)</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label || c.name || c.id}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Difficulty */}
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">Target Difficulty</label>
                  <div className="grid grid-cols-3 gap-2">
                    {["easy", "medium", "hard"].map((diff) => (
                      <button
                        key={diff}
                        type="button"
                        onClick={() => setMockDifficulty(diff)}
                        className={`py-2 rounded-lg text-xs font-semibold capitalize border transition-all ${
                          mockDifficulty === diff
                            ? "bg-zinc-900 text-white border-zinc-900 shadow-xs"
                            : "bg-white text-zinc-600 border-zinc-200 hover:bg-zinc-50"
                        }`}
                      >
                        {diff}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Question Count */}
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">Number of Questions</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[3, 5, 10].map((num) => (
                      <button
                        key={num}
                        type="button"
                        onClick={() => setMockQuestionCount(num)}
                        className={`py-2 rounded-lg text-xs font-semibold border transition-all ${
                          mockQuestionCount === num
                            ? "bg-zinc-900 text-white border-zinc-900 shadow-xs"
                            : "bg-white text-zinc-600 border-zinc-200 hover:bg-zinc-50"
                        }`}
                      >
                        {num} Questions
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <button
                disabled={isStartingSession}
                onClick={handleStartMockSession}
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-sm transition-colors disabled:opacity-50"
              >
                <Play size={14} />
                {isStartingSession ? "Generating Session..." : "Start Mock Interview"}
              </button>
            </div>
          ) : (
            /* ACTIVE RUNNING MOCK SESSION */
            <div className="space-y-5">
              {/* Session Status & Navigation Bar */}
              <div className="bg-white p-4 rounded-xl border border-zinc-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-zinc-900">
                      Mock Session #{activeSession.id}
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {activeSession.difficulty}
                    </span>
                    {activeSession.overall_score !== null && activeSession.overall_score !== undefined && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Score: {activeSession.overall_score}/100
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-0.5">
                    {activeSession.company} • {activeSession.role}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveSession(null)}
                    className="px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors"
                  >
                    Exit Session
                  </button>
                </div>
              </div>

              {/* Question Progress Indicator */}
              <div className="bg-white p-3 rounded-xl border border-zinc-200 flex items-center justify-between text-xs font-medium text-zinc-600 shadow-xs">
                <button
                  disabled={currentQuestionIndex === 0}
                  onClick={handlePrevQuestion}
                  className="flex items-center gap-1 text-zinc-500 hover:text-zinc-900 disabled:opacity-30 disabled:hover:text-zinc-500 transition-colors"
                >
                  <ArrowLeft size={14} />
                  Prev
                </button>

                <div className="flex items-center gap-1.5">
                  {activeSession.questions.map((_, qIdx) => {
                    const isAnswered = Boolean(activeSession.answers?.[String(qIdx)]);
                    const isCurrent = qIdx === currentQuestionIndex;

                    return (
                      <button
                        key={qIdx}
                        onClick={() => {
                          setCurrentQuestionIndex(qIdx);
                          const ansObj = activeSession.answers?.[String(qIdx)];
                          setCandidateAnswer(ansObj?.answer_text || "");
                          setLastEvaluation(ansObj ? (ansObj.eval_result || ansObj.evaluation || ansObj) : null);
                        }}
                        className={`w-7 h-7 rounded-lg text-xs font-bold flex items-center justify-center transition-all ${
                          isCurrent
                            ? "bg-indigo-600 text-white shadow-xs"
                            : isAnswered
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                            : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                        }`}
                      >
                        {qIdx + 1}
                      </button>
                    );
                  })}
                </div>

                <button
                  disabled={currentQuestionIndex === activeSession.questions.length - 1}
                  onClick={handleNextQuestion}
                  className="flex items-center gap-1 text-zinc-500 hover:text-zinc-900 disabled:opacity-30 disabled:hover:text-zinc-500 transition-colors"
                >
                  Next
                  <ArrowRight size={14} />
                </button>
              </div>

              {/* Current Question Workspace */}
              {activeSession.questions[currentQuestionIndex] && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {/* Left: Question Card & Evaluation Insights */}
                  <div className="space-y-4">
                    <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600">
                          Question {currentQuestionIndex + 1} of {activeSession.questions.length}
                        </span>
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-zinc-100 text-zinc-700 capitalize">
                          {activeSession.questions[currentQuestionIndex].category?.replace(/_/g, " ")}
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-zinc-900 tracking-tight leading-snug">
                        {activeSession.questions[currentQuestionIndex].question}
                      </h3>

                      {activeSession.questions[currentQuestionIndex].why_it_matters && (
                        <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200 text-xs text-zinc-600">
                          <span className="font-bold text-zinc-800 block mb-0.5">Evaluation Focus:</span>
                          {activeSession.questions[currentQuestionIndex].why_it_matters}
                        </div>
                      )}
                    </div>

                    {/* AI Feedback & Score Card (if evaluated) */}
                    {lastEvaluation && (
                      <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-4 animate-in fade-in duration-150">
                        <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
                          <div className="font-bold text-zinc-900 text-sm flex items-center gap-1.5">
                            <Sparkles size={16} className="text-indigo-600" />
                            AI Constructive Evaluation
                          </div>
                          <div
                            className={`px-3 py-1 rounded-full text-xs font-bold border ${
                              lastEvaluation.score >= 80
                                ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                                : lastEvaluation.score >= 65
                                ? "bg-amber-50 text-amber-800 border-amber-300"
                                : "bg-rose-50 text-rose-800 border-rose-300"
                            }`}
                          >
                            Score: {lastEvaluation.score} / 100
                          </div>
                        </div>

                        {/* Interviewer Constructive Feedback */}
                        {lastEvaluation.feedback && (
                          <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 text-xs text-indigo-950 leading-relaxed">
                            <span className="font-bold text-indigo-900 block mb-0.5">Interviewer Constructive Feedback:</span>
                            {lastEvaluation.feedback}
                          </div>
                        )}

                        {/* Strengths */}
                        {lastEvaluation.strengths && lastEvaluation.strengths.length > 0 && (
                          <div className="space-y-1.5">
                            <span className="text-xs font-bold text-emerald-800 flex items-center gap-1">
                              <CheckCircle2 size={13} className="text-emerald-600" />
                              Key Strengths Demonstrated
                            </span>
                            <ul className="space-y-1 text-xs text-zinc-600 list-disc list-inside bg-emerald-50/50 p-2.5 rounded-lg border border-emerald-100">
                              {lastEvaluation.strengths.map((str: string, sIdx: number) => (
                                <li key={sIdx}>{str}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Improvements */}
                        {lastEvaluation.improvements && lastEvaluation.improvements.length > 0 && (
                          <div className="space-y-1.5">
                            <span className="text-xs font-bold text-amber-800 flex items-center gap-1">
                              <AlertTriangle size={13} className="text-amber-600" />
                              Actionable Improvement Points
                            </span>
                            <ul className="space-y-1 text-xs text-zinc-600 list-disc list-inside bg-amber-50/50 p-2.5 rounded-lg border border-amber-100">
                              {lastEvaluation.improvements.map((imp: string, iIdx: number) => (
                                <li key={iIdx}>{imp}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Model Answer Reference */}
                        {lastEvaluation.model_answer && (
                          <div className="space-y-1">
                            <span className="text-xs font-bold text-zinc-800">
                              Model Answer (Grounded in Verified Experience):
                            </span>
                            <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg text-xs text-zinc-700 leading-relaxed whitespace-pre-line max-h-48 overflow-y-auto">
                              {lastEvaluation.model_answer}
                            </div>
                          </div>
                        )}

                        {/* Action buttons after evaluation */}
                        <div className="flex items-center justify-between pt-2">
                          <button
                            onClick={handleRetryQuestion}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-zinc-600 hover:text-zinc-900 transition-colors"
                          >
                            <RotateCcw size={13} />
                            Retry Question
                          </button>

                          {currentQuestionIndex < activeSession.questions.length - 1 ? (
                            <button
                              onClick={handleNextQuestion}
                              className="inline-flex items-center gap-1 px-4 py-2 rounded-lg bg-indigo-600 text-white font-semibold text-xs hover:bg-indigo-700 shadow-sm transition-colors"
                            >
                              Next Question
                              <ArrowRight size={13} />
                            </button>
                          ) : (
                            <span className="text-xs font-bold text-emerald-700">
                              ✓ All Questions Completed!
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right: Answer Input Textarea */}
                  <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs flex flex-col space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="font-bold text-zinc-900 text-sm">Your Response</label>
                      <span className="text-[11px] text-zinc-400">
                        {candidateAnswer.split(/\s+/).filter(Boolean).length} words
                      </span>
                    </div>

                    <p className="text-[11px] text-zinc-500">
                      Answer as you would in a live interview. Structure your technical explanation or use the STAR method for behavioral queries.
                    </p>

                    <textarea
                      rows={12}
                      value={candidateAnswer}
                      onChange={(e) => setCandidateAnswer(e.target.value)}
                      placeholder="Type your response here... For behavioral questions, clearly outline your Situation, Task, Action, and Result."
                      className="w-full flex-1 p-3.5 border border-zinc-200 rounded-xl text-xs text-zinc-800 leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white"
                    />

                    <div className="flex items-center justify-between pt-2">
                      <div className="text-[11px] text-zinc-400">
                        {lastEvaluation ? "Answer submitted and evaluated" : "Ready to evaluate"}
                      </div>

                      <button
                        disabled={isSubmittingAnswer || !candidateAnswer.trim()}
                        onClick={handleSubmitAnswer}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white font-semibold text-xs shadow-sm transition-colors disabled:opacity-50"
                      >
                        <Sparkles size={14} className="text-indigo-400" />
                        {isSubmittingAnswer
                          ? "Analyzing Response..."
                          : lastEvaluation
                          ? "Re-evaluate Answer"
                          : "Submit Answer for Feedback"}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================= PAST SESSIONS HISTORY DRAWER ================= */}
      {showHistoryDrawer && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex justify-end">
          <div className="bg-white w-full max-w-md h-full shadow-2xl flex flex-col border-l border-zinc-200 animate-in slide-in-from-right duration-200">
            <div className="p-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50">
              <h3 className="font-bold text-zinc-900 text-sm flex items-center gap-1.5">
                <History size={16} className="text-zinc-600" />
                Mock Interview History
              </h3>
              <button
                onClick={() => setShowHistoryDrawer(false)}
                className="text-zinc-400 hover:text-zinc-600 p-1"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 p-4 overflow-y-auto space-y-3">
              {historySessions.length === 0 ? (
                <div className="p-8 text-center text-zinc-400 text-xs">
                  No mock sessions recorded yet.
                </div>
              ) : (
                historySessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => handleResumeSession(s.id)}
                    className="p-3.5 bg-white rounded-xl border border-zinc-200 hover:border-indigo-300 hover:shadow-sm transition-all cursor-pointer space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-zinc-900">{s.company}</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          s.overall_score && s.overall_score >= 80
                            ? "bg-emerald-50 text-emerald-700"
                            : s.overall_score
                            ? "bg-amber-50 text-amber-700"
                            : "bg-zinc-100 text-zinc-600"
                        }`}
                      >
                        {s.overall_score ? `${s.overall_score}/100` : s.status}
                      </span>
                    </div>

                    <div className="text-[11px] text-zinc-500 font-medium">{s.role}</div>

                    <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-zinc-100">
                      <span>
                        {s.answered_count} / {s.total_questions} answered
                      </span>
                      <span>{new Date(s.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function InterviewPrepPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-zinc-400">Loading Interview Prep...</div>}>
      <InterviewPrepContent />
    </Suspense>
  );
}
