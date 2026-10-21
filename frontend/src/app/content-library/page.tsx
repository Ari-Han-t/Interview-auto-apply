"use client";

import { useState, useEffect } from "react";
import {
  Database, Search, Plus, Filter, Copy, Archive, Trash2, Edit3, CheckCircle2,
  ExternalLink, Sparkles, BookOpen, Briefcase, GraduationCap, Award, Code2,
  FileCheck2, Users, BookMarked, ScrollText, Layers, ChevronRight, X, AlertCircle,
  Tag, Check, ArrowRight
} from "lucide-react";
import { apiFetch, apiPost, apiPut, apiDelete } from "@/lib/api";

type ModuleType =
  | "general-info"
  | "educations"
  | "experiences"
  | "projects"
  | "skills"
  | "achievements"
  | "certifications"
  | "leadership"
  | "coursework"
  | "publications"
  | "custom-sections";

interface BulletItem {
  id?: string;
  text: string;
  is_selected?: boolean;
  metric?: string;
}

export default function ContentLibraryPage() {
  const [activeModule, setActiveModule] = useState<ModuleType>("projects");
  const [overview, setOverview] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [generalInfo, setGeneralInfo] = useState<any>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);
  const [verificationFilter, setVerificationFilter] = useState<string>("all");

  // Modals
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [isReadmeModalOpen, setIsReadmeModalOpen] = useState<boolean>(false);
  const [readmeText, setReadmeText] = useState<string>("");
  const [readmeGithub, setReadmeGithub] = useState<string>("");
  const [analyzedProject, setAnalyzedProject] = useState<any>(null);
  const [selectedSuggestedTechs, setSelectedSuggestedTechs] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

  // Load overview stats
  const fetchOverview = async () => {
    try {
      const data = await apiFetch("/api/v1/content-library/overview");
      setOverview(data);
    } catch (e) {
      console.error("Failed to load library overview", e);
    }
  };

  // Load items for active module
  const fetchModuleItems = async () => {
    setLoading(true);
    try {
      if (activeModule === "general-info") {
        const data = await apiFetch("/api/v1/content-library/general-info");
        setGeneralInfo(data || {});
        setItems([]);
      } else {
        const url = `/api/v1/content-library/${activeModule}?include_archived=${includeArchived}`;
        const data = await apiFetch<any[]>(url);
        setItems(data || []);
      }
    } catch (e) {
      console.error(`Failed to fetch items for ${activeModule}`, e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  useEffect(() => {
    fetchModuleItems();
  }, [activeModule, includeArchived]);

  // Actions
  const handleDuplicate = async (id: number) => {
    try {
      await apiPost(`/api/v1/content-library/${activeModule}/${id}/duplicate`);
      await fetchModuleItems();
      await fetchOverview();
    } catch (e: any) {
      alert(`Duplication failed: ${e.message}`);
    }
  };

  const handleToggleArchive = async (id: number, currentStatus: boolean) => {
    try {
      await apiPut(`/api/v1/content-library/${activeModule}/${id}/archive`, {
        is_archived: !currentStatus
      });
      await fetchModuleItems();
      await fetchOverview();
    } catch (e: any) {
      alert(`Archive toggle failed: ${e.message}`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this record from the Content Library?")) return;
    try {
      await apiDelete(`/api/v1/content-library/${activeModule}/${id}`);
      await fetchModuleItems();
      await fetchOverview();
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  const handleSaveItem = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (activeModule === "general-info") {
        await apiPut("/api/v1/content-library/general-info", generalInfo);
      } else if (editingItem.id) {
        await apiPut(`/api/v1/content-library/${activeModule}/${editingItem.id}`, editingItem);
      } else {
        await apiPost(`/api/v1/content-library/${activeModule}`, editingItem);
      }
      setIsEditModalOpen(false);
      setEditingItem(null);
      await fetchModuleItems();
      await fetchOverview();
    } catch (e: any) {
      alert(`Save failed: ${e.message}`);
    }
  };

  const handleAnalyzeReadme = async () => {
    if (!readmeText.trim()) return;
    setIsAnalyzing(true);
    try {
      const result = await apiPost("/api/v1/content-library/projects/analyze-import", {
        text: readmeText,
        github_url: readmeGithub.trim() || undefined
      });
      setAnalyzedProject(result);
      setSelectedSuggestedTechs(result.flat_technologies || []);
    } catch (e: any) {
      alert(`Analysis failed: ${e.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSaveImportedProject = async () => {
    if (!analyzedProject) return;
    try {
      const payload = {
        name: analyzedProject.name,
        problem: analyzedProject.problem,
        description: analyzedProject.description,
        personal_contribution: analyzedProject.personal_contribution,
        implementation: analyzedProject.implementation,
        technologies: selectedSuggestedTechs,
        github: analyzedProject.github,
        live_link: analyzedProject.live_link,
        supporting_evidence: analyzedProject.supporting_evidence,
        bullets: analyzedProject.bullets,
        verification_status: "project_backed"
      };
      await apiPost("/api/v1/content-library/projects", payload);
      setIsReadmeModalOpen(false);
      setReadmeText("");
      setAnalyzedProject(null);
      setActiveModule("projects");
      await fetchModuleItems();
      await fetchOverview();
    } catch (e: any) {
      alert(`Failed to save imported project: ${e.message}`);
    }
  };

  // Filter items
  const filteredItems = items.filter((item) => {
    if (verificationFilter !== "all" && item.verification_status !== verificationFilter) {
      return false;
    }
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const strVals = Object.values(item).map((v) => (typeof v === "string" ? v.toLowerCase() : ""));
    return strVals.some((val) => val.includes(q));
  });

  const modulesList: { id: ModuleType; label: string; icon: any }[] = [
    { id: "projects", label: "Projects Portfolio", icon: Code2 },
    { id: "experiences", label: "Work & Experience", icon: Briefcase },
    { id: "educations", label: "Education & Degrees", icon: GraduationCap },
    { id: "skills", label: "Skills Inventory", icon: Layers },
    { id: "achievements", label: "Achievements & Awards", icon: Award },
    { id: "certifications", label: "Certifications & Training", icon: FileCheck2 },
    { id: "leadership", label: "Leadership & Activities", icon: Users },
    { id: "coursework", label: "Relevant Coursework", icon: BookMarked },
    { id: "publications", label: "Publications & Open Source", icon: ScrollText },
    { id: "custom-sections", label: "Custom Sections", icon: BookOpen },
    { id: "general-info", label: "General Information", icon: Database },
  ];

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-zinc-50">
      {/* Header */}
      <header className="h-16 border-b border-zinc-200 bg-white px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-600">
            <Database size={20} />
          </div>
          <div>
            <h1 className="text-base font-semibold text-zinc-900 tracking-tight">
              Candidate Content Library
            </h1>
            <p className="text-xs text-zinc-500">
              Canonical repository of your professional facts. Edits here preserve historical resume snapshots.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsReadmeModalOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-md transition-colors"
          >
            <Sparkles size={14} />
            Import from README
          </button>
          {activeModule !== "general-info" && (
            <button
              onClick={() => {
                setEditingItem({
                  is_visible: true,
                  is_archived: false,
                  verification_status: "self_attested",
                  bullets: []
                });
                setIsEditModalOpen(true);
              }}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-zinc-900 hover:bg-zinc-800 rounded-md shadow-sm transition-colors"
            >
              <Plus size={14} />
              Add Record
            </button>
          )}
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Module Selector Sidebar */}
        <div className="w-64 border-r border-zinc-200 bg-white p-3 flex flex-col gap-1 overflow-y-auto shrink-0">
          <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-3 py-2">
            Independent Modules
          </div>
          {modulesList.map((m) => {
            const Icon = m.icon;
            const isActive = activeModule === m.id;
            const count = overview?.modules?.[m.id.replace("-", "_")]?.active ?? 0;

            return (
              <button
                key={m.id}
                onClick={() => setActiveModule(m.id)}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors text-left ${
                  isActive
                    ? "bg-zinc-900 text-white shadow-sm"
                    : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon size={15} className={isActive ? "text-white" : "text-zinc-400"} />
                  <span className="truncate">{m.label}</span>
                </div>
                {m.id !== "general-info" && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      isActive ? "bg-zinc-800 text-zinc-300" : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Content Panel */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Subheader / Search & Filters */}
          <div className="h-14 border-b border-zinc-200 bg-white/80 backdrop-blur px-6 flex items-center justify-between gap-4 shrink-0">
            <div className="flex items-center gap-3 flex-1 max-w-md">
              <div className="relative w-full">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
                <input
                  type="text"
                  placeholder={`Search ${activeModule}...`}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-zinc-50 border border-zinc-200 rounded-md focus:bg-white focus:outline-none focus:ring-1 focus:ring-zinc-900"
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              {activeModule !== "general-info" && (
                <>
                  <select
                    value={verificationFilter}
                    onChange={(e) => setVerificationFilter(e.target.value)}
                    className="text-xs bg-zinc-50 border border-zinc-200 rounded-md px-2.5 py-1.5 focus:outline-none"
                  >
                    <option value="all">All Verification</option>
                    <option value="verified">Verified</option>
                    <option value="project_backed">Project-Backed</option>
                    <option value="certified">Certified</option>
                    <option value="self_attested">Self-Attested</option>
                  </select>

                  <label className="flex items-center gap-2 text-xs text-zinc-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeArchived}
                      onChange={(e) => setIncludeArchived(e.target.checked)}
                      className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                    />
                    <span>Show Archived</span>
                  </label>
                </>
              )}
            </div>
          </div>

          {/* Records View */}
          <div className="flex-1 p-6 overflow-y-auto">
            {loading ? (
              <div className="h-64 flex items-center justify-center text-xs text-zinc-400">
                Loading module records...
              </div>
            ) : activeModule === "general-info" ? (
              /* General Info Form */
              <div className="max-w-3xl bg-white border border-zinc-200 rounded-xl p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-zinc-900 mb-4 pb-2 border-b border-zinc-100">
                  Candidate General Information
                </h2>
                <form onSubmit={handleSaveItem} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Full Name</label>
                      <input
                        type="text"
                        value={generalInfo.full_name || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, full_name: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Preferred Name</label>
                      <input
                        type="text"
                        value={generalInfo.preferred_name || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, preferred_name: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Email Address</label>
                      <input
                        type="email"
                        value={generalInfo.email || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, email: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Phone</label>
                      <input
                        type="text"
                        value={generalInfo.phone || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, phone: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs font-medium text-zinc-700">GitHub Profile</label>
                      <input
                        type="text"
                        value={generalInfo.github || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, github: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-700">LinkedIn Profile</label>
                      <input
                        type="text"
                        value={generalInfo.linkedin || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, linkedin: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Personal Website</label>
                      <input
                        type="text"
                        value={generalInfo.website || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, website: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-zinc-700">Bio / Professional Summary</label>
                    <textarea
                      rows={3}
                      value={generalInfo.bio || ""}
                      onChange={(e) => setGeneralInfo({ ...generalInfo, bio: e.target.value })}
                      className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Availability / Notice Period</label>
                      <input
                        type="text"
                        value={generalInfo.availability || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, availability: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                        placeholder="e.g. Immediate, 2 weeks notice"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Current Location</label>
                      <input
                        type="text"
                        value={generalInfo.current_location || ""}
                        onChange={(e) => setGeneralInfo({ ...generalInfo, current_location: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                  </div>

                  <div className="pt-4 flex justify-end">
                    <button
                      type="submit"
                      className="px-4 py-2 text-xs font-medium text-white bg-zinc-900 rounded-md hover:bg-zinc-800 transition-colors"
                    >
                      Save General Info
                    </button>
                  </div>
                </form>
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="h-64 border-2 border-dashed border-zinc-200 rounded-xl flex flex-col items-center justify-center p-6 text-center">
                <Database size={32} className="text-zinc-300 mb-2" />
                <h3 className="text-xs font-semibold text-zinc-700">No records found</h3>
                <p className="text-[11px] text-zinc-400 max-w-sm mt-1">
                  Add entries to your {activeModule} module to build your single source of truth.
                </p>
                <button
                  onClick={() => {
                    setEditingItem({
                      is_visible: true,
                      is_archived: false,
                      verification_status: "self_attested",
                      bullets: []
                    });
                    setIsEditModalOpen(true);
                  }}
                  className="mt-3 text-xs text-indigo-600 font-medium hover:underline flex items-center gap-1"
                >
                  <Plus size={12} /> Add your first entry
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {filteredItems.map((item) => (
                  <div
                    key={item.id}
                    className={`bg-white border rounded-xl p-5 shadow-sm transition-all hover:shadow-md ${
                      item.is_archived
                        ? "border-zinc-200 opacity-60 bg-zinc-50/50"
                        : "border-zinc-200"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          {/* Stable ID Badge */}
                          <span className="text-[10px] font-mono px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded border border-zinc-200">
                            #{activeModule.slice(0, 4).toUpperCase()}-{item.id}
                          </span>

                          <h3 className="text-sm font-semibold text-zinc-900">
                            {item.name || item.title || item.institution || item.organization || item.course_name}
                          </h3>

                          {/* Verification Indicator */}
                          <span
                            className={`text-[10px] font-medium px-2 py-0.5 rounded-full flex items-center gap-1 ${
                              item.verification_status === "verified"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : item.verification_status === "certified"
                                ? "bg-blue-50 text-blue-700 border border-blue-200"
                                : item.verification_status === "project_backed"
                                ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                                : "bg-zinc-100 text-zinc-600"
                            }`}
                          >
                            <CheckCircle2 size={11} />
                            {item.verification_status || "Self-Attested"}
                          </span>

                          {item.is_archived && (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                              Archived
                            </span>
                          )}
                        </div>

                        {/* Subtitle / Metadata */}
                        <div className="text-xs text-zinc-500 flex items-center gap-3 flex-wrap">
                          {item.company && <span>{item.company}</span>}
                          {item.degree && <span>{item.degree}</span>}
                          {item.role && <span>{item.role}</span>}
                          {item.start_date && (
                            <span>
                              {item.start_date} — {item.end_date || (item.currently_working ? "Present" : "")}
                            </span>
                          )}
                          {item.graduation_year && <span>Class of {item.graduation_year}</span>}
                          {item.cgpa && (
                            <span className="font-mono bg-zinc-50 px-1.5 py-0.5 rounded border border-zinc-100">
                              GPA: {item.cgpa}
                            </span>
                          )}
                        </div>

                        {/* Description / Problem */}
                        {item.problem && (
                          <div className="mt-2 text-xs text-zinc-600">
                            <span className="font-semibold text-zinc-700">Problem: </span>
                            {item.problem}
                          </div>
                        )}
                        {item.description && (
                          <p className="mt-1.5 text-xs text-zinc-600 line-clamp-2">
                            {item.description}
                          </p>
                        )}

                        {/* Technologies Tags */}
                        {item.technologies && item.technologies.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {item.technologies.slice(0, 8).map((t: string) => (
                              <span
                                key={t}
                                className="text-[10px] px-2 py-0.5 bg-zinc-100 text-zinc-700 rounded-md border border-zinc-200/60 font-mono"
                              >
                                {t}
                              </span>
                            ))}
                            {item.technologies.length > 8 && (
                              <span className="text-[10px] text-zinc-400">
                                +{item.technologies.length - 8} more
                              </span>
                            )}
                          </div>
                        )}

                        {/* Selectable Bullets with Stable IDs */}
                        {item.bullets && item.bullets.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-zinc-100 space-y-1.5">
                            <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                              Accomplishment Bullets ({item.bullets.length})
                            </div>
                            {item.bullets.map((b: BulletItem) => (
                              <div
                                key={b.id || b.text}
                                className="flex items-start gap-2 text-xs text-zinc-600 bg-zinc-50/70 p-1.5 rounded border border-zinc-100"
                              >
                                <span className="text-[9px] font-mono text-zinc-400 shrink-0 mt-0.5">
                                  {b.id}
                                </span>
                                <span className="flex-1">{b.text}</span>
                                {b.metric && (
                                  <span className="text-[10px] font-medium px-1.5 py-0.2 bg-emerald-50 text-emerald-700 rounded border border-emerald-200 shrink-0">
                                    {b.metric}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Card Action Buttons */}
                      <div className="flex items-center gap-1 shrink-0">
                        {item.evidence_url && (
                          <a
                            href={item.evidence_url}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 text-zinc-400 hover:text-indigo-600 rounded hover:bg-zinc-100 transition-colors"
                            title="View Supporting Evidence"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                        <button
                          onClick={() => {
                            setEditingItem({ ...item });
                            setIsEditModalOpen(true);
                          }}
                          className="p-1.5 text-zinc-400 hover:text-zinc-800 rounded hover:bg-zinc-100 transition-colors"
                          title="Edit Record"
                        >
                          <Edit3 size={14} />
                        </button>
                        <button
                          onClick={() => handleDuplicate(item.id)}
                          className="p-1.5 text-zinc-400 hover:text-zinc-800 rounded hover:bg-zinc-100 transition-colors"
                          title="Duplicate Record"
                        >
                          <Copy size={14} />
                        </button>
                        <button
                          onClick={() => handleToggleArchive(item.id, item.is_archived)}
                          className={`p-1.5 rounded transition-colors ${
                            item.is_archived
                              ? "text-amber-600 hover:bg-amber-50"
                              : "text-zinc-400 hover:text-zinc-800 hover:bg-zinc-100"
                          }`}
                          title={item.is_archived ? "Unarchive Record" : "Archive Record"}
                        >
                          <Archive size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="p-1.5 text-zinc-400 hover:text-red-600 rounded hover:bg-red-50 transition-colors"
                          title="Delete Record"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Edit Record Modal */}
      {isEditModalOpen && editingItem && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-zinc-200 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-zinc-900">
                {editingItem.id ? "Edit Record" : "Add Record"} — {activeModule}
              </h3>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-700"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveItem} className="p-6 overflow-y-auto space-y-4 flex-1">
              <div>
                <label className="text-xs font-medium text-zinc-700">
                  {activeModule === "projects"
                    ? "Project Name"
                    : activeModule === "experiences"
                    ? "Company Name"
                    : activeModule === "educations"
                    ? "Institution Name"
                    : activeModule === "skills"
                    ? "Skill Name"
                    : "Title / Name"}
                </label>
                <input
                  type="text"
                  required
                  value={editingItem.name || editingItem.title || editingItem.company || editingItem.institution || ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    setEditingItem({
                      ...editingItem,
                      name: val,
                      title: val,
                      company: val,
                      institution: val
                    });
                  }}
                  className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                />
              </div>

              {activeModule === "projects" && (
                <>
                  <div>
                    <label className="text-xs font-medium text-zinc-700">Problem Statement</label>
                    <textarea
                      rows={2}
                      value={editingItem.problem || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, problem: e.target.value })}
                      className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      placeholder="What problem does this project solve?"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-zinc-700">Implementation Details</label>
                    <textarea
                      rows={2}
                      value={editingItem.implementation || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, implementation: e.target.value })}
                      className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      placeholder="Architecture, microservices, pipeline structure..."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-zinc-700">GitHub URL</label>
                      <input
                        type="text"
                        value={editingItem.github || ""}
                        onChange={(e) => setEditingItem({ ...editingItem, github: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Live Demo URL</label>
                      <input
                        type="text"
                        value={editingItem.live_link || ""}
                        onChange={(e) => setEditingItem({ ...editingItem, live_link: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                  </div>
                </>
              )}

              {activeModule === "experiences" && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-zinc-700">Role / Title</label>
                    <input
                      type="text"
                      value={editingItem.title || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, title: e.target.value })}
                      className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-zinc-700">Experience Type</label>
                    <select
                      value={editingItem.experience_type || "employment"}
                      onChange={(e) => setEditingItem({ ...editingItem, experience_type: e.target.value })}
                      className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                    >
                      <option value="employment">Employment (Full-time)</option>
                      <option value="internship">Internship</option>
                      <option value="freelance">Freelance / Contractor</option>
                      <option value="research">Academic / Research</option>
                      <option value="leadership">Leadership / Advisory</option>
                    </select>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-zinc-700">Verification Status</label>
                  <select
                    value={editingItem.verification_status || "self_attested"}
                    onChange={(e) => setEditingItem({ ...editingItem, verification_status: e.target.value })}
                    className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                  >
                    <option value="self_attested">Self-Attested</option>
                    <option value="project_backed">Project-Backed (Code Repository)</option>
                    <option value="certified">Certified (Issued Credential)</option>
                    <option value="verified">Verified (Third-Party / Published)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-zinc-700">Supporting Evidence URL</label>
                  <input
                    type="text"
                    value={editingItem.evidence_url || ""}
                    onChange={(e) => setEditingItem({ ...editingItem, evidence_url: e.target.value })}
                    className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                    placeholder="https://..."
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-700">Description / Details</label>
                <textarea
                  rows={3}
                  value={editingItem.description || ""}
                  onChange={(e) => setEditingItem({ ...editingItem, description: e.target.value })}
                  className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                />
              </div>

              <div className="pt-4 border-t border-zinc-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-zinc-600 hover:bg-zinc-100 rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-medium text-white bg-zinc-900 rounded-md hover:bg-zinc-800 transition-colors"
                >
                  Save Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* README / Documentation Importer Modal */}
      {isReadmeModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-zinc-200 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
            <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-indigo-600" />
                <h3 className="text-sm font-semibold text-zinc-900">
                  Project Importer & Technology Suggestions
                </h3>
              </div>
              <button
                onClick={() => setIsReadmeModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-700"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {!analyzedProject ? (
                <>
                  <p className="text-xs text-zinc-500">
                    Paste your project documentation, README markdown, or repository notes. The analyzer will extract the problem, implementation, outcome bullets, and suggest categorized technologies for candidate review.
                  </p>

                  <div>
                    <label className="text-xs font-medium text-zinc-700">GitHub Repository URL (Optional)</label>
                    <input
                      type="text"
                      placeholder="https://github.com/username/project"
                      value={readmeGithub}
                      onChange={(e) => setReadmeGithub(e.target.value)}
                      className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-zinc-700">README / Project Documentation Text</label>
                    <textarea
                      rows={10}
                      placeholder="# Project Name&#10;&#10;## Problem&#10;...&#10;&#10;## Implementation&#10;Built with FastAPI, Redis..."
                      value={readmeText}
                      onChange={(e) => setReadmeText(e.target.value)}
                      className="mt-1 w-full text-xs font-mono px-3 py-2 border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-900"
                    />
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      disabled={isAnalyzing || !readmeText.trim()}
                      onClick={handleAnalyzeReadme}
                      className="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-md transition-colors flex items-center gap-2"
                    >
                      {isAnalyzing ? "Analyzing Text..." : "Analyze & Suggest Technologies"}
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </>
              ) : (
                /* Review Extracted Project */
                <div className="space-y-4">
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs flex items-center gap-2">
                    <CheckCircle2 size={16} />
                    Analysis complete! Review the suggested technologies below and toggle genuine proficiencies.
                  </div>

                  <div>
                    <label className="text-xs font-medium text-zinc-700">Extracted Project Name</label>
                    <input
                      type="text"
                      value={analyzedProject.name || ""}
                      onChange={(e) => setAnalyzedProject({ ...analyzedProject, name: e.target.value })}
                      className="mt-1 w-full text-xs font-semibold px-3 py-2 border border-zinc-200 rounded-md"
                    />
                  </div>

                  {analyzedProject.problem && (
                    <div>
                      <label className="text-xs font-medium text-zinc-700">Problem Statement</label>
                      <textarea
                        rows={2}
                        value={analyzedProject.problem || ""}
                        onChange={(e) => setAnalyzedProject({ ...analyzedProject, problem: e.target.value })}
                        className="mt-1 w-full text-xs px-3 py-2 border border-zinc-200 rounded-md"
                      />
                    </div>
                  )}

                  {/* Suggested Technologies Review Box */}
                  <div>
                    <label className="text-xs font-semibold text-zinc-800 flex items-center gap-1.5 mb-2">
                      <Tag size={13} className="text-indigo-600" />
                      Suggested Technologies for Candidate Review
                    </label>
                    <p className="text-[11px] text-zinc-500 mb-2">
                      Dependencies were scanned automatically. Select only those you have genuine proficiency in:
                    </p>

                    <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto p-3 bg-zinc-50 border border-zinc-200 rounded-lg">
                      {analyzedProject.flat_technologies?.map((tech: string) => {
                        const isSelected = selectedSuggestedTechs.includes(tech);
                        return (
                          <button
                            key={tech}
                            type="button"
                            onClick={() => {
                              if (isSelected) {
                                setSelectedSuggestedTechs(selectedSuggestedTechs.filter((t) => t !== tech));
                              } else {
                                setSelectedSuggestedTechs([...selectedSuggestedTechs, tech]);
                              }
                            }}
                            className={`px-2.5 py-1 text-xs rounded-md font-mono border transition-all flex items-center gap-1.5 ${
                              isSelected
                                ? "bg-indigo-600 text-white border-indigo-700"
                                : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"
                            }`}
                          >
                            {isSelected && <Check size={12} />}
                            {tech}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Bullets Preview */}
                  {analyzedProject.bullets?.length > 0 && (
                    <div>
                      <label className="text-xs font-semibold text-zinc-800 mb-1 block">
                        Extracted Accomplishment Bullets ({analyzedProject.bullets.length})
                      </label>
                      <div className="space-y-1.5">
                        {analyzedProject.bullets.map((b: BulletItem, idx: number) => (
                          <div key={idx} className="p-2 bg-zinc-50 border border-zinc-200 rounded text-xs text-zinc-700 flex items-start gap-2">
                            <span className="text-indigo-600 mt-0.5">•</span>
                            <span className="flex-1">{b.text}</span>
                            {b.metric && (
                              <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded border border-emerald-200">
                                {b.metric}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-4 border-t border-zinc-200 flex justify-between">
                    <button
                      type="button"
                      onClick={() => setAnalyzedProject(null)}
                      className="px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 rounded-md"
                    >
                      ← Back to Raw Text
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveImportedProject}
                      className="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md shadow-sm transition-colors"
                    >
                      Save to Project Portfolio
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
