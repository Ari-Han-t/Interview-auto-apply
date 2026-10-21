"use client";

import { useState, useEffect, use, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { toast } from "react-hot-toast";
import Link from "next/link";
import {
  Sparkles,
  Layers,
  FileText,
  Lock,
  Unlock,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Download,
  RotateCcw,
  Sliders,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  MoveUp,
  MoveDown,
  Edit3,
  Copy,
  ExternalLink,
  History,
  Archive,
  RefreshCw,
  Plus,
  Trash2,
  Check,
  X,
  FileCode,
  ArrowRight,
  GitBranch,
  ShieldCheck,
  Search,
  BookOpen,
  Briefcase,
  GraduationCap,
  Award,
  Code2,
  Users,
  BookMarked,
  ScrollText,
} from "lucide-react";
import { apiFetch, apiPost, API_BASE } from "@/lib/api";

interface Job {
  id: number;
  title: string;
  company: string;
  description?: string;
  tech_stack_json?: string[] | null;
  required_skills_json?: string[] | null;
}

interface TemplateInfo {
  id: string;
  name: string;
  description: string;
}

interface DiffToken {
  word: string;
  type: "unchanged" | "added" | "removed";
}

interface RefinementItem {
  original: string;
  refined: string;
  reason: string;
  job_requirement: string;
  status: "proposed" | "accepted" | "rejected";
  diff?: DiffToken[];
}

interface SectionConfig {
  included: boolean;
  locked?: boolean;
  reason?: string;
  matching_requirements?: string[];
  contact_fields?: string[];
  selected_item_ids?: number[];
  selected_bullets?: Record<string, string[]>;
  selected_categories?: string[];
}

interface AssemblyPlan {
  job_id: number;
  job_title: string;
  job_company: string;
  role_category: string;
  candidate_level: string;
  recommended_template: string;
  template_name: string;
  template_options: {
    font_size: string;
    margins: string;
    spacing: string;
    page_target: number;
  };
  section_order: string[];
  sections: Record<string, SectionConfig>;
  refinements: Record<string, RefinementItem>;
  summary?: string;
}

const SECTION_ICONS: Record<string, any> = {
  general_info: Users,
  education: GraduationCap,
  experience: Briefcase,
  projects: Code2,
  skills: Sparkles,
  achievements: Award,
  certifications: ShieldCheck,
  leadership: Users,
  coursework: BookOpen,
  publications: BookMarked,
  custom_sections: ScrollText,
};

function ModularResumeStudioContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const urlJobId = searchParams.get("job_id");
  const urlAppId = searchParams.get("app_id");

  // Jobs and candidate modules
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(urlJobId ? parseInt(urlJobId) : null);
  const [candidateLibrary, setCandidateLibrary] = useState<any>(null);
  const [moduleDisplayNames, setModuleDisplayNames] = useState<Record<string, string>>({});
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);

  // Studio tabs: "plan" | "refinements" | "template" | "preview" | "history"
  const [activeTab, setActiveTab] = useState<"plan" | "refinements" | "template" | "preview" | "history">("plan");

  // Plan state
  const [plan, setPlan] = useState<AssemblyPlan | null>(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [customInstructions, setCustomInstructions] = useState("");

  // Granular Accordions
  const [expandedSection, setExpandedSection] = useState<string | null>("projects");

  // LaTeX & Compilation state
  const [latexSource, setLatexSource] = useState<string>("");
  const [isCompiling, setIsCompiling] = useState(false);
  const [previewPdfPath, setPreviewPdfPath] = useState<string>("");
  const [readabilityReport, setReadabilityReport] = useState<any>(null);

  // Versioning state
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [isSavingVersion, setIsSavingVersion] = useState(false);
  const [versionNotes, setVersionNotes] = useState("");

  // Compare versions modal
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [compareV1, setCompareV1] = useState<number | null>(null);
  const [compareV2, setCompareV2] = useState<number | null>(null);
  const [diffData, setDiffData] = useState<any>(null);

  // Manual bullet editor
  const [editingBulletId, setEditingBulletId] = useState<string | null>(null);
  const [editingBulletText, setEditingBulletText] = useState("");

  // 1. Load Initial Jobs, Templates, and Candidate Modules
  useEffect(() => {
    const initializeStudio = async () => {
      try {
        const [jobsData, modulesData, templatesData] = await Promise.all([
          apiFetch<Job[]>("/api/v1/jobs/"),
          apiFetch<any>("/api/v1/modular-resume/candidate-modules"),
          apiFetch<TemplateInfo[]>("/api/v1/modular-resume/templates"),
        ]);

        setJobs(jobsData || []);
        if (modulesData) {
          setCandidateLibrary(modulesData.candidate_data);
          setModuleDisplayNames(modulesData.module_display_names || {});
        }
        setTemplates(templatesData || []);

        // If no job selected yet, pick first available
        if (!selectedJobId && jobsData && jobsData.length > 0) {
          setSelectedJobId(jobsData[0].id);
        }
      } catch (err: any) {
        toast.error("Failed to load initial studio data");
      }
    };
    initializeStudio();
  }, []);

  // 2. When selectedJobId changes, load or generate plan & versions
  useEffect(() => {
    if (!selectedJobId) return;
    loadVersions(selectedJobId);
    generateInitialPlan(selectedJobId);
  }, [selectedJobId]);

  const loadVersions = async (jobId: number) => {
    try {
      const vList = await apiFetch<any[]>(`/api/v1/modular-resume/versions/${jobId}`);
      setVersions(vList || []);
    } catch {
      setVersions([]);
    }
  };

  const generateInitialPlan = async (jobId: number, locks?: any) => {
    setIsPlanning(true);
    try {
      const body: any = {
        target_page_length: 1,
      };
      if (locks) body.user_locks = locks;
      if (customInstructions.trim()) body.custom_instructions = customInstructions.trim();

      const planData = await apiPost<AssemblyPlan>(`/api/v1/modular-resume/plan/${jobId}`, body);
      setPlan(planData);

      // Auto render and compile initial preview
      await handleRenderAndCompile(planData);
    } catch (err: any) {
      toast.error(err.message || "Failed to generate resume assembly plan");
    } finally {
      setIsPlanning(false);
    }
  };

  const handleRenderAndCompile = async (currentPlan: AssemblyPlan) => {
    setIsCompiling(true);
    try {
      // 1. Render LaTeX
      const renderRes = await apiPost<{ latex_source: string }>(
        "/api/v1/modular-resume/render",
        {
          assembly_plan: currentPlan,
          template_name: currentPlan.template_name,
          template_options: currentPlan.template_options,
        }
      );
      setLatexSource(renderRes.latex_source);

      // 2. Compile to PDF with validation
      const compileRes = await apiPost<any>("/api/v1/modular-resume/compile", {
        latex_source: renderRes.latex_source,
        job_id: currentPlan.job_id,
      });

      setPreviewPdfPath(compileRes.preview_url || `/api/v1/modular-resume/temp-preview/pdf?t=${Date.now()}`);
      setReadabilityReport(compileRes.readability_report);
    } catch (err: any) {
      toast.error("Compilation error: " + (err.message || "Unknown error"));
    } finally {
      setIsCompiling(false);
    }
  };

  // Re-order modules
  const moveSection = (index: number, direction: "up" | "down") => {
    if (!plan) return;
    const newOrder = [...plan.section_order];
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= newOrder.length) return;

    const temp = newOrder[index];
    newOrder[index] = newOrder[targetIdx];
    newOrder[targetIdx] = temp;

    const updatedPlan = { ...plan, section_order: newOrder };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
    toast.success(`Reordered: ${moduleDisplayNames[temp] || temp}`);
  };

  // Toggle module included
  const toggleSectionIncluded = (sectionKey: string) => {
    if (!plan) return;
    const sec = plan.sections[sectionKey] || { included: false };
    const updatedSec = { ...sec, included: !sec.included };
    const updatedPlan = {
      ...plan,
      sections: { ...plan.sections, [sectionKey]: updatedSec },
    };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
  };

  // Toggle module locked
  const toggleSectionLocked = (sectionKey: string) => {
    if (!plan) return;
    const sec = plan.sections[sectionKey] || { included: true };
    const updatedSec = { ...sec, locked: !sec.locked };
    const updatedPlan = {
      ...plan,
      sections: { ...plan.sections, [sectionKey]: updatedSec },
    };
    setPlan(updatedPlan);
    toast.success(
      updatedSec.locked
        ? `Locked ${moduleDisplayNames[sectionKey] || sectionKey}`
        : `Unlocked ${moduleDisplayNames[sectionKey] || sectionKey}`
    );
  };

  // Granular item selection toggle (e.g. project, experience, skill)
  const toggleItemSelection = (sectionKey: string, itemId: number) => {
    if (!plan) return;
    const sec = plan.sections[sectionKey] || { included: true, selected_item_ids: [] };
    const currentIds = sec.selected_item_ids || [];
    const newIds = currentIds.includes(itemId)
      ? currentIds.filter((id) => id !== itemId)
      : [...currentIds, itemId];

    const updatedPlan = {
      ...plan,
      sections: {
        ...plan.sections,
        [sectionKey]: { ...sec, selected_item_ids: newIds },
      },
    };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
  };

  // Granular bullet selection toggle
  const toggleBulletSelection = (sectionKey: string, parentId: string, bulletId: string) => {
    if (!plan) return;
    const sec = plan.sections[sectionKey] || { included: true, selected_bullets: {} };
    const currentBullets = sec.selected_bullets || {};
    const parentList = currentBullets[parentId] || [];

    const newList = parentList.includes(bulletId)
      ? parentList.filter((b) => b !== bulletId)
      : [...parentList, bulletId];

    const updatedPlan = {
      ...plan,
      sections: {
        ...plan.sections,
        [sectionKey]: {
          ...sec,
          selected_bullets: { ...currentBullets, [parentId]: newList },
        },
      },
    };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
  };

  // Refinement controls: Accept / Reject / Edit
  const handleSetRefinementStatus = (bulletId: string, status: "accepted" | "rejected") => {
    if (!plan) return;
    const ref = plan.refinements[bulletId];
    if (!ref) return;

    const updatedRef = { ...ref, status };
    const updatedPlan = {
      ...plan,
      refinements: { ...plan.refinements, [bulletId]: updatedRef },
    };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
    toast.success(status === "accepted" ? "Refinement applied" : "Restored original wording");
  };

  const handleSaveEditedBullet = (bulletId: string) => {
    if (!plan) return;
    const ref = plan.refinements[bulletId] || {
      original: editingBulletText,
      job_requirement: "Manual Candidate Edit",
      reason: "Direct candidate refinement",
    };

    const updatedRef: RefinementItem = {
      ...ref,
      refined: editingBulletText,
      status: "accepted",
    };

    const updatedPlan = {
      ...plan,
      refinements: { ...plan.refinements, [bulletId]: updatedRef },
    };
    setPlan(updatedPlan);
    setEditingBulletId(null);
    handleRenderAndCompile(updatedPlan);
    toast.success("Bullet updated");
  };

  // Template switch
  const handleSelectTemplate = (templateId: string) => {
    if (!plan) return;
    const updatedPlan = { ...plan, template_name: templateId };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
    toast.success(`Template changed to ${templateId.replace("_", " ").toUpperCase()}`);
  };

  // Template options change (margins, font size, spacing)
  const handleUpdateTemplateOptions = (key: string, value: any) => {
    if (!plan) return;
    const updatedOptions = { ...plan.template_options, [key]: value };
    const updatedPlan = { ...plan, template_options: updatedOptions };
    setPlan(updatedPlan);
    handleRenderAndCompile(updatedPlan);
  };

  // Save Immutable Version
  const handleSaveVersion = async () => {
    if (!plan) return;
    setIsSavingVersion(true);
    try {
      const selectedJob = jobs.find((j) => j.id === selectedJobId);
      const res = await apiPost<any>("/api/v1/modular-resume/save-version", {
        job_id: selectedJobId,
        application_id: urlAppId ? parseInt(urlAppId) : null,
        name: `${selectedJob?.company || "Custom"} - ${plan.template_name}`,
        latex_source: latexSource,
        assembly_plan: plan,
        template_name: plan.template_name,
        template_options: plan.template_options,
        notes: versionNotes || `Tailored for ${selectedJob?.title} at ${selectedJob?.company}`,
      });

      toast.success(`Saved immutable Version #${res.version_number}!`);
      setVersionNotes("");
      if (selectedJobId) loadVersions(selectedJobId);
    } catch (err: any) {
      toast.error(err.message || "Failed to save version");
    } finally {
      setIsSavingVersion(false);
    }
  };

  // Restore a Version
  const handleRestoreVersion = async (vId: number) => {
    try {
      const details = await apiFetch<any>(`/api/v1/modular-resume/version/${vId}`);
      if (details && details.assembly_plan) {
        setPlan(details.assembly_plan);
        setLatexSource(details.latex_source);
        await apiPost(`/api/v1/modular-resume/version/${vId}/restore`);
        await handleRenderAndCompile(details.assembly_plan);
        toast.success(`Restored Version #${details.version_number}`);
        setActiveTab("plan");
      }
    } catch (err: any) {
      toast.error("Failed to restore version");
    }
  };

  // Compare two versions
  const handleCompareVersions = async () => {
    if (!compareV1 || !compareV2) {
      toast.error("Select two versions to compare");
      return;
    }
    try {
      const diff = await apiFetch<any>(
        `/api/v1/modular-resume/version/${compareV1}/compare/${compareV2}`
      );
      setDiffData(diff);
      setIsCompareOpen(true);
    } catch (err: any) {
      toast.error("Version comparison failed");
    }
  };

  // Direct download helpers
  const handleDownloadFile = (type: "pdf" | "tex" | "zip") => {
    if (versions.length > 0) {
      const latestVersion = versions[0];
      window.open(`${API_BASE}/api/v1/modular-resume/download/${latestVersion.id}/${type}`, "_blank");
    } else if (type === "pdf") {
      window.open(`${API_BASE}/api/v1/modular-resume/temp-preview/pdf`, "_blank");
    } else if (type === "tex") {
      const blob = new Blob([latexSource], { type: "text/x-tex" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.tex";
      a.click();
      URL.revokeObjectURL(url);
    } else {
      toast.error("Please save an immutable version first to export the full source package (.zip)");
    }
  };

  const selectedJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div className="space-y-5 pb-16 min-h-screen">
      {/* 1. STUDIO HEADER */}
      <div className="bg-white border border-zinc-200 shadow-sm p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-zinc-900 text-white flex items-center justify-center shadow-sm">
            <Layers size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
                Modular Resume Studio
              </h1>
              <span className="bg-indigo-50 text-indigo-700 text-[11px] font-semibold px-2 py-0.5 rounded-full border border-indigo-100">
                Truth-Preserving Compiler
              </span>
            </div>
            <p className="text-xs text-zinc-500">
              Controlled module selection, role-ranked reordering, and ATS-compliant LaTeX generation.
            </p>
          </div>
        </div>

        {/* Job Selector & Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1.5 bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5">
            <Briefcase size={14} className="text-zinc-500" />
            <select
              value={selectedJobId || ""}
              onChange={(e) => setSelectedJobId(parseInt(e.target.value))}
              className="bg-transparent text-xs font-semibold text-zinc-800 focus:outline-none cursor-pointer"
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.company}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => selectedJobId && generateInitialPlan(selectedJobId)}
            disabled={isPlanning}
            className="inline-flex items-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-semibold px-3 py-2 rounded-lg transition-colors"
          >
            <Sparkles size={13} className={isPlanning ? "animate-spin" : ""} />
            {isPlanning ? "Analyzing..." : "Re-Plan for Role"}
          </button>

          <button
            onClick={handleSaveVersion}
            disabled={isSavingVersion || !plan}
            className="inline-flex items-center gap-1.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-sm"
          >
            <Check size={14} />
            {isSavingVersion ? "Saving..." : "Save Immutable Version"}
          </button>
        </div>
      </div>

      {/* 2. ROLE ALIGNMENT SUMMARY BAR */}
      {plan && selectedJob && (
        <div className="bg-gradient-to-r from-zinc-50 via-indigo-50/30 to-zinc-50 border border-zinc-200/80 p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-zinc-800">Target Role Fit:</span>
            <span className="bg-white border border-zinc-200 font-medium text-zinc-700 px-2 py-0.5 rounded shadow-2xs">
              {plan.role_category.toUpperCase()}
            </span>
            <span className="bg-white border border-zinc-200 font-medium text-zinc-700 px-2 py-0.5 rounded shadow-2xs">
              {plan.candidate_level === "early_career" ? "Early Career / Student" : "Experienced Professional"}
            </span>
            <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold px-2 py-0.5 rounded">
              Template: {plan.template_name.replace("_", " ").toUpperCase()}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-zinc-500">Readability Audit:</span>
            {readabilityReport?.is_readable ? (
              <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded font-semibold text-[11px]">
                <ShieldCheck size={12} /> ATS Readable ({readabilityReport.word_count} words)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-amber-700 bg-amber-100 px-2 py-0.5 rounded font-medium text-[11px]">
                <AlertTriangle size={12} /> Readability Validated
              </span>
            )}
          </div>
        </div>
      )}

      {/* 3. STUDIO NAVIGATION TABS */}
      <div className="flex items-center gap-1 border-b border-zinc-200 px-1">
        <button
          onClick={() => setActiveTab("plan")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "plan"
              ? "border-zinc-900 text-zinc-900"
              : "border-transparent text-zinc-500 hover:text-zinc-800"
          }`}
        >
          <Layers size={14} />
          1. Assembly Plan & Modules
        </button>

        <button
          onClick={() => setActiveTab("refinements")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "refinements"
              ? "border-zinc-900 text-zinc-900"
              : "border-transparent text-zinc-500 hover:text-zinc-800"
          }`}
        >
          <Edit3 size={14} />
          2. Truth-Preserving Refinements ({Object.keys(plan?.refinements || {}).length})
        </button>

        <button
          onClick={() => setActiveTab("template")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "template"
              ? "border-zinc-900 text-zinc-900"
              : "border-transparent text-zinc-500 hover:text-zinc-800"
          }`}
        >
          <Sliders size={14} />
          3. ATS Template & Formatting
        </button>

        <button
          onClick={() => setActiveTab("preview")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "preview"
              ? "border-zinc-900 text-zinc-900"
              : "border-transparent text-zinc-500 hover:text-zinc-800"
          }`}
        >
          <Eye size={14} />
          4. Live Preview & LaTeX Source
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "history"
              ? "border-zinc-900 text-zinc-900"
              : "border-transparent text-zinc-500 hover:text-zinc-800"
          }`}
        >
          <History size={14} />
          5. Version History & Diffs ({versions.length})
        </button>
      </div>

      {/* 4. TAB CONTENT */}
      {/* ---------------- TAB 1: ASSEMBLY PLAN & MODULES ---------------- */}
      {activeTab === "plan" && plan && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* LEFT: Section Ordering & Lock Controls */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-zinc-900">Module Order & Toggles</h3>
                <span className="text-[11px] text-zinc-400">Drag or use arrows</span>
              </div>
              <p className="text-xs text-zinc-500 mb-4">
                Enable or lock sections. Locked sections are preserved during AI re-planning.
              </p>

              <div className="space-y-2">
                {plan.section_order.map((secKey, idx) => {
                  const secCfg = plan.sections[secKey] || { included: false };
                  const displayName = moduleDisplayNames[secKey] || secKey;
                  const Icon = SECTION_ICONS[secKey] || FileText;
                  const isSelectedForInspect = expandedSection === secKey;

                  return (
                    <div
                      key={secKey}
                      onClick={() => setExpandedSection(secKey)}
                      className={`flex items-center justify-between p-2.5 rounded-lg border text-xs transition-all cursor-pointer ${
                        isSelectedForInspect
                          ? "border-indigo-500 bg-indigo-50/30"
                          : secCfg.included
                          ? "border-zinc-200 bg-white hover:border-zinc-300"
                          : "border-zinc-100 bg-zinc-50 opacity-60"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-[10px] font-bold text-zinc-400 w-4 text-center">
                          {idx + 1}
                        </span>
                        <Icon size={14} className={secCfg.included ? "text-indigo-600" : "text-zinc-400"} />
                        <span className={`font-semibold ${secCfg.included ? "text-zinc-900" : "text-zinc-400"}`}>
                          {displayName}
                        </span>
                      </div>

                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        {/* Lock toggle */}
                        <button
                          onClick={() => toggleSectionLocked(secKey)}
                          title={secCfg.locked ? "Unlock section" : "Lock section against AI re-order"}
                          className={`p-1 rounded ${
                            secCfg.locked ? "text-amber-600 bg-amber-50" : "text-zinc-400 hover:text-zinc-600"
                          }`}
                        >
                          {secCfg.locked ? <Lock size={12} /> : <Unlock size={12} />}
                        </button>

                        {/* Move Up */}
                        <button
                          onClick={() => moveSection(idx, "up")}
                          disabled={idx === 0}
                          className="p-1 text-zinc-400 hover:text-zinc-700 disabled:opacity-20"
                        >
                          <MoveUp size={12} />
                        </button>

                        {/* Move Down */}
                        <button
                          onClick={() => moveSection(idx, "down")}
                          disabled={idx === plan.section_order.length - 1}
                          className="p-1 text-zinc-400 hover:text-zinc-700 disabled:opacity-20"
                        >
                          <MoveDown size={12} />
                        </button>

                        {/* Include toggle */}
                        <input
                          type="checkbox"
                          checked={secCfg.included}
                          onChange={() => toggleSectionIncluded(secKey)}
                          className="ml-1 w-3.5 h-3.5 text-zinc-900 rounded focus:ring-0 cursor-pointer"
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Candidate instructions box */}
            <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-sm space-y-2">
              <label className="text-xs font-bold text-zinc-800 flex items-center gap-1.5">
                <Edit3 size={13} className="text-indigo-600" /> Tailoring Instructions / Tone
              </label>
              <textarea
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                placeholder="E.g. Prioritize high-concurrency systems, emphasize Kafka and PostgreSQL over frontend..."
                rows={3}
                className="w-full text-xs p-2.5 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-zinc-800"
              />
              <button
                onClick={() => selectedJobId && generateInitialPlan(selectedJobId)}
                className="w-full bg-zinc-100 hover:bg-zinc-200 text-zinc-800 text-xs font-semibold py-1.5 rounded transition-colors"
              >
                Apply Instructions & Re-Score
              </button>
            </div>
          </div>

          {/* RIGHT: Granular Record & Bullet Inspector */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
                <div>
                  <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
                    <span>Selected Module Inspector:</span>
                    <span className="text-indigo-600">
                      {moduleDisplayNames[expandedSection || "projects"] || expandedSection}
                    </span>
                  </h3>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    Select individual records and bullet points to include in the compiled document.
                  </p>
                </div>

                <div className="text-xs text-zinc-400">
                  {plan.sections[expandedSection || ""]?.reason && (
                    <span className="bg-zinc-50 border border-zinc-200 px-2.5 py-1 rounded text-zinc-600 font-medium">
                      {plan.sections[expandedSection || ""]?.reason}
                    </span>
                  )}
                </div>
              </div>

              {/* INSPECTOR CONTENT FOR EXPANDED MODULE */}
              <div className="mt-4 space-y-4">
                {/* 1. PROJECTS INSPECTOR */}
                {expandedSection === "projects" && candidateLibrary?.projects && (
                  <div className="space-y-4">
                    {candidateLibrary.projects.map((proj: any) => {
                      const secCfg = plan.sections["projects"] || {};
                      const isProjSelected = (secCfg.selected_item_ids || []).includes(proj.id);
                      const selectedBulletsForProj = (secCfg.selected_bullets || {})[String(proj.id)] || [];

                      return (
                        <div
                          key={proj.id}
                          className={`border rounded-lg p-3.5 transition-colors ${
                            isProjSelected ? "border-zinc-300 bg-white" : "border-zinc-200 bg-zinc-50/50 opacity-60"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <label className="flex items-center gap-2.5 cursor-pointer font-bold text-xs text-zinc-900">
                              <input
                                type="checkbox"
                                checked={isProjSelected}
                                onChange={() => toggleItemSelection("projects", proj.id)}
                                className="w-4 h-4 text-zinc-900 rounded cursor-pointer"
                              />
                              <span>{proj.name}</span>
                              <span className="text-[11px] font-normal text-zinc-400">
                                ({proj.technologies?.join(", ")})
                              </span>
                            </label>
                            {proj.github && (
                              <a
                                href={proj.github}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[11px] text-indigo-600 hover:underline flex items-center gap-1"
                              >
                                Repo <ExternalLink size={10} />
                              </a>
                            )}
                          </div>

                          {/* Project Bullets Checklist */}
                          {isProjSelected && proj.bullets?.length > 0 && (
                            <div className="mt-3 pl-6 space-y-2 border-t border-zinc-100 pt-2.5">
                              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                                Selectable Accomplishment Bullets
                              </span>
                              {proj.bullets.map((b: any) => {
                                const isBulletSelected = selectedBulletsForProj.includes(b.id);
                                const refinement = plan.refinements[b.id];

                                return (
                                  <div key={b.id} className="flex items-start gap-2 text-xs">
                                    <input
                                      type="checkbox"
                                      checked={isBulletSelected}
                                      onChange={() =>
                                        toggleBulletSelection("projects", String(proj.id), b.id)
                                      }
                                      className="mt-0.5 w-3.5 h-3.5 text-zinc-900 rounded cursor-pointer"
                                    />
                                    <div className="flex-1">
                                      <p className="text-zinc-700 leading-relaxed">
                                        {refinement?.status === "accepted" ? (
                                          <span className="text-indigo-950 font-medium">
                                            {refinement.refined}{" "}
                                            <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-100">
                                              Refined ✓
                                            </span>
                                          </span>
                                        ) : (
                                          b.text
                                        )}
                                      </p>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 2. EXPERIENCE INSPECTOR */}
                {expandedSection === "experience" && candidateLibrary?.experience && (
                  <div className="space-y-4">
                    {candidateLibrary.experience.map((exp: any) => {
                      const secCfg = plan.sections["experience"] || {};
                      const isExpSelected = (secCfg.selected_item_ids || []).includes(exp.id);
                      const selectedBulletsForExp = (secCfg.selected_bullets || {})[String(exp.id)] || [];

                      return (
                        <div
                          key={exp.id}
                          className={`border rounded-lg p-3.5 transition-colors ${
                            isExpSelected ? "border-zinc-300 bg-white" : "border-zinc-200 bg-zinc-50/50 opacity-60"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <label className="flex items-center gap-2.5 cursor-pointer font-bold text-xs text-zinc-900">
                              <input
                                type="checkbox"
                                checked={isExpSelected}
                                onChange={() => toggleItemSelection("experience", exp.id)}
                                className="w-4 h-4 text-zinc-900 rounded cursor-pointer"
                              />
                              <span>
                                {exp.title} — {exp.company}
                              </span>
                              <span className="text-[11px] font-normal text-zinc-400">({exp.dates})</span>
                            </label>
                          </div>

                          {isExpSelected && exp.bullets?.length > 0 && (
                            <div className="mt-3 pl-6 space-y-2 border-t border-zinc-100 pt-2.5">
                              {exp.bullets.map((b: any) => {
                                const isBulletSelected = selectedBulletsForExp.includes(b.id);
                                const refinement = plan.refinements[b.id];

                                return (
                                  <div key={b.id} className="flex items-start gap-2 text-xs">
                                    <input
                                      type="checkbox"
                                      checked={isBulletSelected}
                                      onChange={() =>
                                        toggleBulletSelection("experience", String(exp.id), b.id)
                                      }
                                      className="mt-0.5 w-3.5 h-3.5 text-zinc-900 rounded cursor-pointer"
                                    />
                                    <p className="text-zinc-700 leading-relaxed flex-1">
                                      {refinement?.status === "accepted" ? (
                                        <span className="text-indigo-950 font-medium">
                                          {refinement.refined}{" "}
                                          <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-100">
                                            Refined ✓
                                          </span>
                                        </span>
                                      ) : (
                                        b.text
                                      )}
                                    </p>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 3. SKILLS INSPECTOR */}
                {expandedSection === "skills" && candidateLibrary?.skills && (
                  <div className="space-y-4">
                    <p className="text-xs text-zinc-500">
                      Toggle skills to include in the technical skills matrix:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {candidateLibrary.skills.map((s: any) => {
                        const secCfg = plan.sections["skills"] || {};
                        const isSelected = (secCfg.selected_item_ids || []).includes(s.id);

                        return (
                          <button
                            key={s.id}
                            onClick={() => toggleItemSelection("skills", s.id)}
                            className={`px-2.5 py-1 rounded-md text-xs font-semibold border transition-all ${
                              isSelected
                                ? "bg-zinc-900 text-white border-zinc-900 shadow-2xs"
                                : "bg-white text-zinc-600 border-zinc-200 hover:bg-zinc-50"
                            }`}
                          >
                            {isSelected ? "✓ " : "+ "}
                            {s.name}
                            <span className="text-[10px] opacity-70 ml-1">({s.category})</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 4. EDUCATION INSPECTOR */}
                {expandedSection === "education" && candidateLibrary?.education && (
                  <div className="space-y-3">
                    {candidateLibrary.education.map((edu: any) => {
                      const isSelected = (plan.sections["education"]?.selected_item_ids || []).includes(edu.id);
                      return (
                        <div key={edu.id} className="border p-3 rounded-lg flex items-center justify-between text-xs">
                          <label className="flex items-center gap-2 cursor-pointer font-bold text-zinc-900">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleItemSelection("education", edu.id)}
                              className="w-4 h-4 text-zinc-900 rounded"
                            />
                            <span>
                              {edu.institution} — {edu.degree} in {edu.specialization}
                            </span>
                          </label>
                          <span className="text-zinc-400">{edu.dates}</span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 5. ACHIEVEMENTS INSPECTOR */}
                {expandedSection === "achievements" && candidateLibrary?.achievements && (
                  <div className="space-y-3">
                    {candidateLibrary.achievements.map((ach: any) => {
                      const isSelected = (plan.sections["achievements"]?.selected_item_ids || []).includes(ach.id);
                      return (
                        <div key={ach.id} className="border p-3 rounded-lg flex items-center justify-between text-xs">
                          <label className="flex items-center gap-2 cursor-pointer font-bold text-zinc-900">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleItemSelection("achievements", ach.id)}
                              className="w-4 h-4 text-zinc-900 rounded"
                            />
                            <span>
                              {ach.title} ({ach.issuer_or_event})
                            </span>
                          </label>
                          <span className="text-zinc-400">{ach.year_or_date}</span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 6. GENERAL INFO / CONTACT FIELDS */}
                {expandedSection === "general_info" && candidateLibrary?.general_info && (
                  <div className="space-y-3">
                    <span className="text-xs font-bold text-zinc-800">Selectable Contact Header Fields:</span>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5 text-xs">
                      {["email", "phone", "location", "linkedin", "github", "portfolio"].map((field) => {
                        const contactList = plan.sections["general_info"]?.contact_fields || [];
                        const isIncluded = contactList.includes(field);

                        return (
                          <label
                            key={field}
                            className={`p-2.5 border rounded-lg flex items-center gap-2 cursor-pointer ${
                              isIncluded ? "border-indigo-300 bg-indigo-50/30 text-indigo-950 font-semibold" : "border-zinc-200 text-zinc-500"
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isIncluded}
                              onChange={() => {
                                const newFields = isIncluded
                                  ? contactList.filter((f) => f !== field)
                                  : [...contactList, field];
                                const updatedPlan = {
                                  ...plan,
                                  sections: {
                                    ...plan.sections,
                                    general_info: {
                                      ...plan.sections.general_info,
                                      contact_fields: newFields,
                                    },
                                  },
                                };
                                setPlan(updatedPlan);
                                handleRenderAndCompile(updatedPlan);
                              }}
                              className="w-4 h-4 text-indigo-600 rounded"
                            />
                            <span className="capitalize">{field}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 7. CERTIFICATIONS INSPECTOR */}
                {expandedSection === "certifications" && candidateLibrary?.certifications && (
                  <div className="space-y-3">
                    {candidateLibrary.certifications.length === 0 ? (
                      <p className="text-xs text-zinc-400 italic">No certifications in library.</p>
                    ) : (
                      candidateLibrary.certifications.map((cert: any) => {
                        const isSelected = (plan.sections["certifications"]?.selected_item_ids || []).includes(cert.id);
                        return (
                          <div key={cert.id} className="border p-3 rounded-lg flex items-center justify-between text-xs">
                            <label className="flex items-center gap-2 cursor-pointer font-bold text-zinc-900">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleItemSelection("certifications", cert.id)}
                                className="w-4 h-4 text-zinc-900 rounded"
                              />
                              <span>
                                {cert.name} {cert.issuer && `— ${cert.issuer}`}
                              </span>
                            </label>
                            <span className="text-zinc-400">{cert.issue_date}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

                {/* 8. LEADERSHIP INSPECTOR */}
                {expandedSection === "leadership" && candidateLibrary?.leadership && (
                  <div className="space-y-3">
                    {candidateLibrary.leadership.length === 0 ? (
                      <p className="text-xs text-zinc-400 italic">No leadership records in library.</p>
                    ) : (
                      candidateLibrary.leadership.map((lead: any) => {
                        const secCfg = plan.sections["leadership"] || {};
                        const isSelected = (secCfg.selected_item_ids || []).includes(lead.id);
                        const selectedBulletsForLead = (secCfg.selected_bullets || {})[String(lead.id)] || [];

                        return (
                          <div
                            key={lead.id}
                            className={`border rounded-lg p-3.5 transition-colors ${
                              isSelected ? "border-zinc-300 bg-white" : "border-zinc-200 bg-zinc-50/50 opacity-60"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <label className="flex items-center gap-2 cursor-pointer font-bold text-xs text-zinc-900">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleItemSelection("leadership", lead.id)}
                                  className="w-4 h-4 text-zinc-900 rounded cursor-pointer"
                                />
                                <span>{lead.role} — {lead.organization}</span>
                              </label>
                              <span className="text-[11px] text-zinc-400">{lead.end_date || lead.start_date}</span>
                            </div>

                            {isSelected && lead.bullets?.length > 0 && (
                              <div className="mt-3 pl-6 space-y-2 border-t border-zinc-100 pt-2.5">
                                {lead.bullets.map((b: any) => {
                                  const isBulletSelected = selectedBulletsForLead.includes(b.id);
                                  return (
                                    <div key={b.id} className="flex items-start gap-2 text-xs">
                                      <input
                                        type="checkbox"
                                        checked={isBulletSelected}
                                        onChange={() => toggleBulletSelection("leadership", String(lead.id), b.id)}
                                        className="mt-0.5 w-3.5 h-3.5 text-zinc-900 rounded cursor-pointer"
                                      />
                                      <p className="text-zinc-700 leading-relaxed flex-1">{b.text}</p>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

                {/* 9. COURSEWORK INSPECTOR */}
                {expandedSection === "coursework" && candidateLibrary?.coursework && (
                  <div className="space-y-3">
                    {candidateLibrary.coursework.length === 0 ? (
                      <p className="text-xs text-zinc-400 italic">No coursework in library.</p>
                    ) : (
                      candidateLibrary.coursework.map((c: any) => {
                        const isSelected = (plan.sections["coursework"]?.selected_item_ids || []).includes(c.id);
                        return (
                          <div key={c.id} className="border p-3 rounded-lg flex items-center justify-between text-xs">
                            <label className="flex items-center gap-2 cursor-pointer font-bold text-zinc-900">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleItemSelection("coursework", c.id)}
                                className="w-4 h-4 text-zinc-900 rounded"
                              />
                              <span>
                                {c.course_name} {c.course_code && `(${c.course_code})`}
                              </span>
                            </label>
                            <span className="text-zinc-400">{c.grade || c.term_or_year}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

                {/* 10. PUBLICATIONS INSPECTOR */}
                {expandedSection === "publications" && candidateLibrary?.publications && (
                  <div className="space-y-3">
                    {candidateLibrary.publications.length === 0 ? (
                      <p className="text-xs text-zinc-400 italic">No publications in library.</p>
                    ) : (
                      candidateLibrary.publications.map((pub: any) => {
                        const isSelected = (plan.sections["publications"]?.selected_item_ids || []).includes(pub.id);
                        return (
                          <div key={pub.id} className="border p-3 rounded-lg flex items-center justify-between text-xs">
                            <label className="flex items-center gap-2 cursor-pointer font-bold text-zinc-900">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleItemSelection("publications", pub.id)}
                                className="w-4 h-4 text-zinc-900 rounded"
                              />
                              <span>
                                {pub.title} {pub.venue_or_publisher && `— ${pub.venue_or_publisher}`}
                              </span>
                            </label>
                            <span className="text-zinc-400">{pub.publication_date}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}

                {/* 11. CUSTOM SECTIONS INSPECTOR */}
                {expandedSection === "custom_sections" && candidateLibrary?.custom_sections && (
                  <div className="space-y-3">
                    {candidateLibrary.custom_sections.length === 0 ? (
                      <p className="text-xs text-zinc-400 italic">No custom sections in library.</p>
                    ) : (
                      candidateLibrary.custom_sections.map((cs: any) => {
                        const isSelected = (plan.sections["custom_sections"]?.selected_item_ids || []).includes(cs.id);
                        return (
                          <div key={cs.id} className="border p-3 rounded-lg flex items-center justify-between text-xs">
                            <label className="flex items-center gap-2 cursor-pointer font-bold text-zinc-900">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleItemSelection("custom_sections", cs.id)}
                                className="w-4 h-4 text-zinc-900 rounded"
                              />
                              <span>
                                {cs.section_title}: {cs.title}
                              </span>
                            </label>
                            <span className="text-zinc-400">{cs.dates}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- TAB 2: TRUTH-PRESERVING REFINEMENTS ---------------- */}
      {activeTab === "refinements" && plan && (
        <div className="space-y-4 max-w-4xl mx-auto">
          <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm">
            <h3 className="text-base font-bold text-zinc-900 mb-1">
              Truth-Preserving Refinement Inspector
            </h3>
            <p className="text-xs text-zinc-500 mb-4">
              Review before-and-after wording changes proposed by AI. Every statement traces strictly back to
              verified library data. Hallucinated metrics or tools are strictly prohibited.
            </p>

            <div className="space-y-4">
              {Object.entries(plan.refinements).map(([bulletId, ref]) => {
                const isEditing = editingBulletId === bulletId;

                return (
                  <div key={bulletId} className="border border-zinc-200 rounded-xl p-4 bg-zinc-50/50 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2.5 py-0.5 rounded">
                        Targeted Requirement: {ref.job_requirement}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleSetRefinementStatus(bulletId, "accepted")}
                          className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors ${
                            ref.status === "accepted"
                              ? "bg-emerald-600 text-white"
                              : "bg-white border border-zinc-200 text-zinc-700 hover:bg-emerald-50"
                          }`}
                        >
                          Accept Refined
                        </button>
                        <button
                          onClick={() => handleSetRefinementStatus(bulletId, "rejected")}
                          className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors ${
                            ref.status === "rejected"
                              ? "bg-zinc-800 text-white"
                              : "bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-100"
                          }`}
                        >
                          Keep Original
                        </button>
                      </div>
                    </div>

                    {/* BEFORE / AFTER CARDS */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {/* ORIGINAL */}
                      <div className="bg-white p-3 rounded-lg border border-zinc-200 space-y-1">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                          Original Verified Library Text
                        </span>
                        <p className="text-zinc-700 leading-relaxed">{ref.original}</p>
                      </div>

                      {/* REFINED */}
                      <div className="bg-white p-3 rounded-lg border border-indigo-200 space-y-1">
                        <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">
                          Refined ATS Action Wording
                        </span>
                        {isEditing ? (
                          <div className="space-y-2">
                            <textarea
                              value={editingBulletText}
                              onChange={(e) => setEditingBulletText(e.target.value)}
                              rows={3}
                              className="w-full text-xs p-2 border rounded"
                            />
                            <div className="flex justify-end gap-1.5">
                              <button
                                onClick={() => setEditingBulletId(null)}
                                className="px-2 py-1 text-xs border rounded"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleSaveEditedBullet(bulletId)}
                                className="px-2 py-1 text-xs bg-zinc-900 text-white rounded font-medium"
                              >
                                Save
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <p className="text-zinc-900 font-medium leading-relaxed">{ref.refined}</p>
                            <button
                              onClick={() => {
                                setEditingBulletId(bulletId);
                                setEditingBulletText(ref.refined);
                              }}
                              className="text-[11px] text-zinc-400 hover:text-zinc-700 flex items-center gap-1 mt-1"
                            >
                              <Edit3 size={11} /> Edit directly
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* REASON */}
                    <div className="text-[11px] text-zinc-500 bg-white p-2 rounded border border-zinc-150">
                      <span className="font-semibold text-zinc-700">Rationale: </span>
                      {ref.reason}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ---------------- TAB 3: ATS TEMPLATE & FORMATTING ---------------- */}
      {activeTab === "template" && plan && (
        <div className="space-y-6 max-w-4xl mx-auto">
          {/* Template Selection */}
          <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-zinc-900">Select Reusable ATS Template</h3>
            <p className="text-xs text-zinc-500">
              All templates share the same structured data model. No boilerplate rewriting or package injection.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {templates.map((tpl) => {
                const isSelected = plan.template_name === tpl.id;
                return (
                  <div
                    key={tpl.id}
                    onClick={() => handleSelectTemplate(tpl.id)}
                    className={`p-4 rounded-xl border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? "border-zinc-900 bg-zinc-900 text-white shadow-md"
                        : "border-zinc-200 bg-white hover:border-zinc-300 text-zinc-800"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm">{tpl.name}</span>
                      {isSelected && <CheckCircle2 size={16} className="text-white" />}
                    </div>
                    <p className={`leading-relaxed text-[11px] ${isSelected ? "text-zinc-300" : "text-zinc-500"}`}>
                      {tpl.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Formatting Controls */}
          <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-zinc-900">Typography & Geometry Parameters</h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              {/* Font Size */}
              <div className="space-y-1.5">
                <label className="font-semibold text-zinc-700">Font Size</label>
                <select
                  value={plan.template_options?.font_size || "10.8pt"}
                  onChange={(e) => handleUpdateTemplateOptions("font_size", e.target.value)}
                  className="w-full p-2 border border-zinc-200 rounded-lg text-xs"
                >
                  <option value="10pt">10pt (High Density)</option>
                  <option value="10.5pt">10.5pt (Balanced)</option>
                  <option value="10.8pt">10.8pt (Standard)</option>
                  <option value="11pt">11pt (Traditional)</option>
                </select>
              </div>

              {/* Margins */}
              <div className="space-y-1.5">
                <label className="font-semibold text-zinc-700">Margins</label>
                <select
                  value={plan.template_options?.margins || "0.5in"}
                  onChange={(e) => handleUpdateTemplateOptions("margins", e.target.value)}
                  className="w-full p-2 border border-zinc-200 rounded-lg text-xs"
                >
                  <option value="0.45in">0.45in (Ultra Compact)</option>
                  <option value="0.5in">0.5in (Standard Technical)</option>
                  <option value="0.6in">0.6in (Balanced)</option>
                  <option value="0.75in">0.75in (Traditional)</option>
                </select>
              </div>

              {/* Spacing */}
              <div className="space-y-1.5">
                <label className="font-semibold text-zinc-700">Line & Section Spacing</label>
                <select
                  value={plan.template_options?.spacing || "compact"}
                  onChange={(e) => handleUpdateTemplateOptions("spacing", e.target.value)}
                  className="w-full p-2 border border-zinc-200 rounded-lg text-xs"
                >
                  <option value="tight">Tight (1-Page Target)</option>
                  <option value="compact">Compact (Standard)</option>
                  <option value="normal">Normal (Generous)</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- TAB 4: LIVE PREVIEW & LATEX SOURCE ---------------- */}
      {activeTab === "preview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 h-[750px]">
          {/* LEFT: LaTeX Source Editor */}
          <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-sm flex flex-col h-full">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <span className="text-xs font-bold text-zinc-900 flex items-center gap-1.5">
                <FileCode size={14} className="text-indigo-600" />
                Compiled LaTeX Source (.tex)
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(latexSource);
                    toast.success("LaTeX source copied to clipboard!");
                  }}
                  className="p-1.5 hover:bg-zinc-100 rounded text-zinc-600 text-xs flex items-center gap-1"
                >
                  <Copy size={12} /> Copy
                </button>
                <button
                  onClick={() => handleDownloadFile("tex")}
                  className="p-1.5 hover:bg-zinc-100 rounded text-zinc-600 text-xs flex items-center gap-1"
                >
                  <Download size={12} /> .tex
                </button>
              </div>
            </div>

            <textarea
              value={latexSource}
              onChange={(e) => setLatexSource(e.target.value)}
              className="flex-1 mt-3 w-full p-3 font-mono text-[11px] leading-relaxed bg-zinc-900 text-zinc-100 rounded-lg focus:outline-none resize-none"
            />

            <div className="mt-3 flex justify-between items-center text-xs">
              <span className="text-zinc-400">Characters: {latexSource.length}</span>
              <button
                onClick={async () => {
                  setIsCompiling(true);
                  try {
                    const res = await apiPost<any>("/api/v1/modular-resume/compile", {
                      latex_source: latexSource,
                      job_id: selectedJobId,
                    });
                    setPreviewPdfPath(res.preview_path);
                    setReadabilityReport(res.readability_report);
                    toast.success("Recompiled successfully!");
                  } catch (e: any) {
                    toast.error("Compilation error");
                  } finally {
                    setIsCompiling(false);
                  }
                }}
                disabled={isCompiling}
                className="bg-zinc-900 hover:bg-zinc-800 text-white font-semibold px-3 py-1.5 rounded transition-colors text-xs flex items-center gap-1"
              >
                <RefreshCw size={12} className={isCompiling ? "animate-spin" : ""} />
                Recompile Changes
              </button>
            </div>
          </div>

          {/* RIGHT: PDF Preview & Readability Report */}
          <div className="bg-white border border-zinc-200 rounded-xl p-4 shadow-sm flex flex-col h-full">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-zinc-900">PDF Document Preview</span>
                {readabilityReport?.is_readable ? (
                  <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded border border-emerald-200">
                    ATS Passed ({readabilityReport.word_count} words)
                  </span>
                ) : (
                  <span className="text-[10px] bg-amber-50 text-amber-700 font-semibold px-2 py-0.5 rounded border border-amber-200">
                    Compiled
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownloadFile("pdf")}
                  className="bg-zinc-900 text-white font-semibold px-3 py-1.5 rounded text-xs flex items-center gap-1 hover:bg-zinc-800"
                >
                  <Download size={12} /> Download PDF
                </button>
                <button
                  onClick={() => handleDownloadFile("zip")}
                  className="bg-zinc-100 text-zinc-700 font-semibold px-2.5 py-1.5 rounded text-xs flex items-center gap-1 hover:bg-zinc-200"
                >
                  <Archive size={12} /> Source .zip
                </button>
              </div>
            </div>

            {/* Embedded PDF Viewer */}
            <div className="flex-1 mt-3 bg-zinc-100 rounded-lg overflow-hidden border border-zinc-200 relative flex items-center justify-center">
              {isCompiling ? (
                <div className="flex flex-col items-center gap-2 text-zinc-500">
                  <RefreshCw size={24} className="animate-spin text-indigo-600" />
                  <span className="text-xs font-medium">Compiling in isolated environment...</span>
                </div>
              ) : previewPdfPath ? (
                <iframe
                  src={
                    previewPdfPath.startsWith("http")
                      ? previewPdfPath
                      : previewPdfPath.startsWith("/")
                      ? `${API_BASE}${previewPdfPath}`
                      : `${API_BASE}/api/v1/modular-resume/temp-preview/pdf?t=${Date.now()}`
                  }
                  className="w-full h-full border-0"
                  title="Resume PDF Preview"
                />
              ) : (
                <span className="text-xs text-zinc-400">PDF preview ready upon compilation</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ---------------- TAB 5: VERSION HISTORY & DIFFS ---------------- */}
      {activeTab === "history" && (
        <div className="space-y-4 max-w-4xl mx-auto">
          <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-zinc-900">Immutable Version History</h3>
                <p className="text-xs text-zinc-500">
                  Every approved resume is saved as an immutable record linked to this job.
                </p>
              </div>

              {versions.length >= 2 && (
                <button
                  onClick={handleCompareVersions}
                  className="bg-indigo-50 border border-indigo-200 text-indigo-700 px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-indigo-100 transition-colors"
                >
                  Compare Selected Versions
                </button>
              )}
            </div>

            {versions.length === 0 ? (
              <p className="text-xs text-zinc-400 italic py-6 text-center">
                No versions saved yet for this job opening. Click &quot;Save Immutable Version&quot; above to create one.
              </p>
            ) : (
              <div className="divide-y divide-zinc-100">
                {versions.map((v) => (
                  <div key={v.id} className="py-3 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-bold bg-zinc-100 text-zinc-800 px-2 py-0.5 rounded">
                        v{v.version_number}
                      </span>
                      <div>
                        <p className="font-semibold text-zinc-900">{v.name}</p>
                        <p className="text-[11px] text-zinc-400">
                          Template: {v.template_name} | {v.created_at}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleRestoreVersion(v.id)}
                        className="text-zinc-600 hover:text-zinc-900 font-medium px-2.5 py-1 rounded border hover:bg-zinc-50"
                      >
                        Restore
                      </button>

                      <a
                        href={`${API_BASE}/api/v1/modular-resume/download/${v.id}/pdf`}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-zinc-900 text-white font-medium px-2.5 py-1 rounded hover:bg-zinc-800"
                      >
                        PDF
                      </a>

                      <a
                        href={`${API_BASE}/api/v1/modular-resume/download/${v.id}/tex`}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-zinc-100 text-zinc-700 font-medium px-2.5 py-1 rounded hover:bg-zinc-200"
                      >
                        .tex
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. VERSION COMPARISON MODAL */}
      {isCompareOpen && diffData && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-zinc-200 max-w-3xl w-full p-6 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <h3 className="font-bold text-sm text-zinc-900">
                Version Comparison: v{diffData.v1?.version_number} vs v{diffData.v2?.version_number}
              </h3>
              <button onClick={() => setIsCompareOpen(false)} className="text-zinc-400 hover:text-zinc-700">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-zinc-50 rounded-lg flex justify-between">
                <div>
                  <span className="font-semibold text-zinc-700">Section Order: </span>
                  {diffData.order_changed ? (
                    <span className="text-amber-600 font-bold">Modified</span>
                  ) : (
                    <span className="text-emerald-600 font-bold">Identical</span>
                  )}
                </div>
                <div>
                  <span className="font-semibold text-zinc-700">Template: </span>
                  {diffData.template_changed ? (
                    <span className="text-amber-600 font-bold">
                      {diffData.v1.template} → {diffData.v2.template}
                    </span>
                  ) : (
                    <span className="text-emerald-600 font-bold">Unchanged</span>
                  )}
                </div>
              </div>

              {/* Module changes */}
              <div className="border rounded-lg divide-y divide-zinc-100">
                {Object.entries(diffData.section_changes || {}).map(([sec, ch]: any) => (
                  <div key={sec} className="p-2.5 flex items-center justify-between">
                    <span className="font-semibold text-zinc-800 capitalize">{sec}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        ch.status === "unchanged"
                          ? "bg-zinc-100 text-zinc-600"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {ch.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ModularResumeStudio() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center flex flex-col items-center justify-center gap-2 text-zinc-500">
          <div className="w-6 h-6 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold">Loading Modular Resume Studio...</p>
        </div>
      }
    >
      <ModularResumeStudioContent />
    </Suspense>
  );
}
