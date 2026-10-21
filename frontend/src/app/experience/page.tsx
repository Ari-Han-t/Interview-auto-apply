"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Code2,
  Briefcase,
  Plus,
  Search,
  ExternalLink,
  GitBranch,
  CheckCircle2,
  Eye,
  EyeOff,
  Edit3,
  Trash2,
  Sparkles,
  Calendar,
  MapPin,
  Tag,
  ArrowRight,
  Database
} from "lucide-react";
import { toast } from "react-hot-toast";
import { apiFetch, apiPost, apiPut, apiDelete } from "@/lib/api";

export default function ProjectsAndExperiencePage() {
  const [activeTab, setActiveTab] = useState<"experiences" | "projects">("experiences");
  const [experiences, setExperiences] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // Modals
  const [isExpModalOpen, setIsExpModalOpen] = useState(false);
  const [editingExp, setEditingExp] = useState<any>(null);
  const [isProjModalOpen, setIsProjModalOpen] = useState(false);
  const [editingProj, setEditingProj] = useState<any>(null);

  const fetchRecords = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<any>("/api/v1/profile/");
      setExperiences(data.experiences || []);
      setProjects(data.projects || []);
    } catch (e: any) {
      toast.error(e.message || "Failed to load experiences and projects");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const handleToggleExpVisibility = async (expId: number, currentVisible: boolean) => {
    try {
      await apiPut(`/api/v1/profile/experiences/${expId}/visibility`, { is_visible: !currentVisible });
      setExperiences(experiences.map((e) => (e.id === expId ? { ...e, is_visible: !currentVisible } : e)));
      toast.success(!currentVisible ? "Experience visible in resumes" : "Experience hidden from resumes");
    } catch (e) {
      toast.error("Failed to update visibility");
    }
  };

  const handleToggleProjVisibility = async (projId: number, currentVisible: boolean) => {
    try {
      await apiPut(`/api/v1/profile/projects/${projId}/visibility`, { is_visible: !currentVisible });
      setProjects(projects.map((p) => (p.id === projId ? { ...p, is_visible: !currentVisible } : p)));
      toast.success(!currentVisible ? "Project visible in resumes" : "Project hidden from resumes");
    } catch (e) {
      toast.error("Failed to update visibility");
    }
  };

  const filteredExperiences = experiences.filter((e) => {
    const q = searchQuery.toLowerCase();
    return (
      e.company?.toLowerCase().includes(q) ||
      e.title?.toLowerCase().includes(q) ||
      (e.technologies || []).some((t: string) => t.toLowerCase().includes(q))
    );
  });

  const filteredProjects = projects.filter((p) => {
    const q = searchQuery.toLowerCase();
    return (
      p.name?.toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q) ||
      (p.technologies || []).some((t: string) => t.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Projects and Experience</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Verified work history, technical projects, impact metrics, and resume inclusion controls.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/content-library"
            className="px-3.5 py-2 bg-white border border-zinc-200 hover:bg-zinc-50 text-zinc-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <Database size={13} />
            Content Library
          </Link>
          <button
            onClick={() => {
              if (activeTab === "experiences") {
                setEditingExp({
                  company: "",
                  title: "",
                  internship_or_fulltime: "fulltime",
                  location: "",
                  start_date: "",
                  end_date: "",
                  currently_working: false,
                  description: "",
                  technologies: [],
                });
                setIsExpModalOpen(true);
              } else {
                setEditingProj({
                  name: "",
                  role: "",
                  description: "",
                  github: "",
                  live_link: "",
                  technologies: [],
                });
                setIsProjModalOpen(true);
              }
            }}
            className="px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <Plus size={14} />
            {activeTab === "experiences" ? "Add Experience" : "Add Project"}
          </button>
        </div>
      </div>

      {/* Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-200 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("experiences")}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
              activeTab === "experiences"
                ? "bg-zinc-900 text-white shadow-sm"
                : "text-zinc-600 hover:bg-zinc-100"
            }`}
          >
            <Briefcase size={14} />
            Work Experiences ({experiences.length})
          </button>
          <button
            onClick={() => setActiveTab("projects")}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
              activeTab === "projects"
                ? "bg-zinc-900 text-white shadow-sm"
                : "text-zinc-600 hover:bg-zinc-100"
            }`}
          >
            <Code2 size={14} />
            Technical Projects ({projects.length})
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-2.5 text-zinc-400" />
          <input
            type="text"
            placeholder="Search by role, company, or tech..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-900"
          />
        </div>
      </div>

      {/* Main Content List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm animate-pulse h-32" />
          ))}
        </div>
      ) : activeTab === "experiences" ? (
        <div className="space-y-4">
          {filteredExperiences.map((exp) => (
            <div
              key={exp.id}
              className={`bg-white rounded-xl border p-5 transition-all shadow-sm ${
                exp.is_visible ? "border-zinc-200" : "border-zinc-200/60 opacity-60 bg-zinc-50/40"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-sm text-zinc-900">{exp.title}</h3>
                    <span className="text-zinc-400">·</span>
                    <span className="font-semibold text-xs text-zinc-700">{exp.company}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 ml-1">
                      {exp.internship_or_fulltime || "Full-time"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                    <span className="flex items-center gap-1">
                      <Calendar size={13} />
                      {exp.start_date || "Start"} – {exp.currently_working ? "Present" : exp.end_date || "End"}
                    </span>
                    {exp.location && (
                      <span className="flex items-center gap-1">
                        <MapPin size={13} />
                        {exp.location}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 self-end sm:self-auto">
                  <button
                    onClick={() => handleToggleExpVisibility(exp.id, exp.is_visible)}
                    title={exp.is_visible ? "Include in resume builds" : "Excluded from resume builds"}
                    className="p-1.5 text-zinc-500 hover:text-zinc-800 rounded hover:bg-zinc-100"
                  >
                    {exp.is_visible ? <Eye size={16} className="text-emerald-600" /> : <EyeOff size={16} />}
                  </button>
                  <button
                    onClick={() => {
                      setEditingExp(exp);
                      setIsExpModalOpen(true);
                    }}
                    className="p-1.5 text-zinc-500 hover:text-zinc-800 rounded hover:bg-zinc-100"
                    title="Edit experience"
                  >
                    <Edit3 size={15} />
                  </button>
                </div>
              </div>

              {exp.description && (
                <p className="text-xs text-zinc-600 mt-3 whitespace-pre-line leading-relaxed">
                  {exp.description}
                </p>
              )}

              {exp.technologies && exp.technologies.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-zinc-100">
                  {exp.technologies.map((t: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-zinc-100 text-zinc-700 rounded text-[11px] font-mono"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}

          {filteredExperiences.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border border-dashed border-zinc-200 p-8">
              <Briefcase size={28} className="text-zinc-300 mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-zinc-800">No work experiences found</h3>
              <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
                Add internships, full-time positions, or research roles to establish verified experience for your resumes.
              </p>
              <button
                onClick={() => {
                  setEditingExp({
                    company: "",
                    title: "",
                    internship_or_fulltime: "fulltime",
                    location: "",
                    start_date: "",
                    end_date: "",
                    currently_working: false,
                    description: "",
                    technologies: [],
                  });
                  setIsExpModalOpen(true);
                }}
                className="mt-4 px-3.5 py-1.5 bg-zinc-900 text-white text-xs font-semibold rounded-lg hover:bg-zinc-800"
              >
                Add First Experience
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredProjects.map((proj) => (
            <div
              key={proj.id}
              className={`bg-white rounded-xl border p-5 transition-all shadow-sm ${
                proj.is_visible ? "border-zinc-200" : "border-zinc-200/60 opacity-60 bg-zinc-50/40"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-sm text-zinc-900">{proj.name}</h3>
                    {proj.role && (
                      <>
                        <span className="text-zinc-400">·</span>
                        <span className="text-xs text-zinc-600">{proj.role}</span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                    {proj.github && (
                      <a
                        href={proj.github}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                      >
                        <GitBranch size={13} /> Repository
                      </a>
                    )}
                    {proj.live_link && (
                      <a
                        href={proj.live_link}
                        target="_blank"
                        rel="noreferrer"
                        className="text-emerald-600 hover:text-emerald-800 flex items-center gap-1"
                      >
                        <ExternalLink size={13} /> Live Deployment
                      </a>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 self-end sm:self-auto">
                  <button
                    onClick={() => handleToggleProjVisibility(proj.id, proj.is_visible)}
                    title={proj.is_visible ? "Included in resume builds" : "Excluded from resume builds"}
                    className="p-1.5 text-zinc-500 hover:text-zinc-800 rounded hover:bg-zinc-100"
                  >
                    {proj.is_visible ? <Eye size={16} className="text-emerald-600" /> : <EyeOff size={16} />}
                  </button>
                  <button
                    onClick={() => {
                      setEditingProj(proj);
                      setIsProjModalOpen(true);
                    }}
                    className="p-1.5 text-zinc-500 hover:text-zinc-800 rounded hover:bg-zinc-100"
                    title="Edit project"
                  >
                    <Edit3 size={15} />
                  </button>
                </div>
              </div>

              {proj.description && (
                <p className="text-xs text-zinc-600 mt-3 whitespace-pre-line leading-relaxed">
                  {proj.description}
                </p>
              )}

              {proj.technologies && proj.technologies.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-zinc-100">
                  {proj.technologies.map((t: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-zinc-100 text-zinc-700 rounded text-[11px] font-mono"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}

          {filteredProjects.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border border-dashed border-zinc-200 p-8">
              <Code2 size={28} className="text-zinc-300 mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-zinc-800">No technical projects found</h3>
              <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
                Add repositories, open-source work, and key systems to showcase hands-on architectural competence.
              </p>
              <button
                onClick={() => {
                  setEditingProj({
                    name: "",
                    role: "",
                    description: "",
                    github: "",
                    live_link: "",
                    technologies: [],
                  });
                  setIsProjModalOpen(true);
                }}
                className="mt-4 px-3.5 py-1.5 bg-zinc-900 text-white text-xs font-semibold rounded-lg hover:bg-zinc-800"
              >
                Add First Project
              </button>
            </div>
          )}
        </div>
      )}

      {/* Experience Edit Modal */}
      {isExpModalOpen && editingExp && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-zinc-200 max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-zinc-900">
              {editingExp.id ? "Edit Work Experience" : "Add Work Experience"}
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Company / Organization *</label>
                <input
                  type="text"
                  required
                  value={editingExp.company || ""}
                  onChange={(e) => setEditingExp({ ...editingExp, company: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. Stripe, Google, Startup"
                />
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Position / Job Title *</label>
                <input
                  type="text"
                  required
                  value={editingExp.title || ""}
                  onChange={(e) => setEditingExp({ ...editingExp, title: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. Software Engineer Intern"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">Start Date</label>
                  <input
                    type="text"
                    value={editingExp.start_date || ""}
                    onChange={(e) => setEditingExp({ ...editingExp, start_date: e.target.value })}
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                    placeholder="e.g. May 2024"
                  />
                </div>
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">End Date</label>
                  <input
                    type="text"
                    disabled={editingExp.currently_working}
                    value={editingExp.end_date || ""}
                    onChange={(e) => setEditingExp({ ...editingExp, end_date: e.target.value })}
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900 disabled:bg-zinc-100"
                    placeholder="e.g. Aug 2024"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="curr_work"
                  checked={editingExp.currently_working || false}
                  onChange={(e) => setEditingExp({ ...editingExp, currently_working: e.target.checked })}
                  className="rounded text-zinc-900 focus:ring-zinc-900"
                />
                <label htmlFor="curr_work" className="font-medium text-zinc-700">Currently working here</label>
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Location</label>
                <input
                  type="text"
                  value={editingExp.location || ""}
                  onChange={(e) => setEditingExp({ ...editingExp, location: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. San Francisco, CA / Remote"
                />
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Technologies (comma separated)</label>
                <input
                  type="text"
                  value={Array.isArray(editingExp.technologies) ? editingExp.technologies.join(", ") : ""}
                  onChange={(e) =>
                    setEditingExp({
                      ...editingExp,
                      technologies: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. Python, FastApi, PostgreSQL, Redis"
                />
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Bullet Points & Impact Description</label>
                <textarea
                  rows={4}
                  value={editingExp.description || ""}
                  onChange={(e) => setEditingExp({ ...editingExp, description: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900 leading-relaxed"
                  placeholder="Designed and deployed microservices reducing API latency by 45%..."
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
              <button
                type="button"
                onClick={() => setIsExpModalOpen(false)}
                className="px-4 py-2 border border-zinc-200 hover:bg-zinc-50 rounded-lg text-xs font-semibold text-zinc-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    if (editingExp.id) {
                      await apiPut(`/api/v1/profile/experiences/${editingExp.id}`, editingExp);
                      toast.success("Experience updated!");
                    } else {
                      await apiPost("/api/v1/profile/experiences", editingExp);
                      toast.success("Experience added!");
                    }
                    setIsExpModalOpen(false);
                    fetchRecords();
                  } catch (e: any) {
                    toast.error(e.message || "Failed to save experience");
                  }
                }}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg text-xs font-semibold"
              >
                Save Experience
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Project Edit Modal */}
      {isProjModalOpen && editingProj && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-zinc-200 max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-zinc-900">
              {editingProj.id ? "Edit Technical Project" : "Add Technical Project"}
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Project Name *</label>
                <input
                  type="text"
                  required
                  value={editingProj.name || ""}
                  onChange={(e) => setEditingProj({ ...editingProj, name: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. Distributed Consensus Engine"
                />
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Role / Subtitle</label>
                <input
                  type="text"
                  value={editingProj.role || ""}
                  onChange={(e) => setEditingProj({ ...editingProj, role: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. Lead Developer / Core Contributor"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">GitHub URL</label>
                  <input
                    type="url"
                    value={editingProj.github || ""}
                    onChange={(e) => setEditingProj({ ...editingProj, github: e.target.value })}
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                    placeholder="https://github.com/user/project"
                  />
                </div>
                <div>
                  <label className="font-semibold text-zinc-700 block mb-1">Live Demo / URL</label>
                  <input
                    type="url"
                    value={editingProj.live_link || ""}
                    onChange={(e) => setEditingProj({ ...editingProj, live_link: e.target.value })}
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                    placeholder="https://project.domain.com"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Technologies (comma separated)</label>
                <input
                  type="text"
                  value={Array.isArray(editingProj.technologies) ? editingProj.technologies.join(", ") : ""}
                  onChange={(e) =>
                    setEditingProj({
                      ...editingProj,
                      technologies: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900"
                  placeholder="e.g. Rust, Tokio, Raft, Docker"
                />
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Project Description & Architecture</label>
                <textarea
                  rows={4}
                  value={editingProj.description || ""}
                  onChange={(e) => setEditingProj({ ...editingProj, description: e.target.value })}
                  className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900 leading-relaxed"
                  placeholder="Implemented Raft consensus algorithm in Rust with log replication and cluster heartbeat monitors..."
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
              <button
                type="button"
                onClick={() => setIsProjModalOpen(false)}
                className="px-4 py-2 border border-zinc-200 hover:bg-zinc-50 rounded-lg text-xs font-semibold text-zinc-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    if (editingProj.id) {
                      await apiPut(`/api/v1/profile/projects/${editingProj.id}`, editingProj);
                      toast.success("Project updated!");
                    } else {
                      await apiPost("/api/v1/profile/projects", editingProj);
                      toast.success("Project added!");
                    }
                    setIsProjModalOpen(false);
                    fetchRecords();
                  } catch (e: any) {
                    toast.error(e.message || "Failed to save project");
                  }
                }}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg text-xs font-semibold"
              >
                Save Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
