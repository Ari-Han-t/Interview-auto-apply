"use client";

import { useState, useEffect } from "react";
import { UploadCloud, FileText, Trash2, Download, Sparkles, GitBranch, Award, BookOpen, Plus, RefreshCw, CheckCircle2 } from "lucide-react";
import { toast } from "react-hot-toast";
import { apiFetch, API_BASE } from "@/lib/api";

type AutofillResult = {
  message: string;
  counts: {
    profile_fields: number;
    experiences: number;
    projects: number;
    skills: number;
    achievements: number;
    courses: number;
  };
};

function GithubIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

export default function ResumeManager() {
  const [isDragging, setIsDragging] = useState(false);
  const [resumes, setResumes] = useState<any[]>([]);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [githubUsername, setGithubUsername] = useState("");
  const [isSyncingGithub, setIsSyncingGithub] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [autofillSummary, setAutofillSummary] = useState("");

  // New Achievement Form State
  const [newAch, setNewAch] = useState({ title: "", category: "hackathon", issuer_or_event: "", year_or_date: "", description: "" });
  const [showAddAch, setShowAddAch] = useState(false);

  // New Course Form State
  const [newCourse, setNewCourse] = useState({ name: "", issuer: "", issue_date: "", credential_url: "", skills_covered: "" });
  const [showAddCourse, setShowAddCourse] = useState(false);

  useEffect(() => {
    fetchProfileData();
    fetchResumes();
  }, []);

  const fetchProfileData = async () => {
    try {
      const data = await apiFetch("/api/v1/profile/");
      if (data.profile?.github) {
        const gh = data.profile.github.replace("https://github.com/", "").replace("/", "");
        setGithubUsername(gh);
      }
      setAchievements(data.achievements || []);
      setCourses(data.courses || []);
      return true;
    } catch (e: any) {
      console.error("Failed to load profile knowledge base:", e);
      return false;
    }
  };

  const fetchResumes = async () => {
    try {
      const data = await apiFetch("/api/v1/resume/versions");
      const mapped = data.map((r: any) => ({
        id: r.id,
        name: r.name,
        type: r.file_type,
        date: new Date(r.created_at).toLocaleDateString(),
        size: "Uploaded",
        tags: ["Master"],
      }));
      setResumes(mapped);
    } catch (e: any) {
      if (e.message !== "Unauthorized") {
        toast.error("Failed to load resumes");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleAutofill = async () => {
    if (isAutofilling || isUploading || isLoading || isSyncingGithub) return;
    if (!window.confirm("Autofill from your latest uploaded resume? Saved profile data will be refreshed, replacing any unsaved GitHub username edit. Review all imported facts afterward.")) return;

    setIsAutofilling(true);
    setAutofillSummary("");
    const toastId = toast.loading("Autofilling from your latest resume...");
    try {
      const result = await apiFetch<AutofillResult>("/api/v1/resume/autofill", { method: "POST" });
      const { counts } = result;
      const summary = `${result.message} Added: ${counts.profile_fields} profile fields, ${counts.experiences} experiences, ${counts.projects} projects, ${counts.skills} skills, ${counts.achievements} achievements, ${counts.courses} courses. Review the imported facts in Settings and below.`;
      setAutofillSummary(summary);
      toast.success(summary, { id: toastId, duration: 10000 });
      const [refreshed] = await Promise.all([fetchProfileData(), fetchResumes()]);
      if (!refreshed) toast.error("Autofill completed, but profile data could not be refreshed. Reload this page before editing.");
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Resume autofill failed. Please try again.", { id: toastId });
    } finally {
      setIsAutofilling(false);
    }
  };

  const handleSyncGithub = async () => {
    if (!githubUsername.trim()) {
      toast.error("Please enter a valid GitHub username");
      return;
    }

    setIsSyncingGithub(true);
    const toastId = toast.loading("Syncing GitHub repositories & achievements...");

    try {
      const res = await apiFetch("/api/v1/github/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_username: githubUsername.trim() }),
      });

      toast.success(
        `Synced! Discovered ${res.synced_projects} projects, ${res.discovered_skills_count} skills, and ${res.discovered_achievements_count} achievements.`,
        { id: toastId, duration: 5000 }
      );
      fetchProfileData();
    } catch (e: any) {
      toast.error(e.message || "Failed to sync GitHub profile", { id: toastId });
    } finally {
      setIsSyncingGithub(false);
    }
  };

  const handleAddAchievement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAch.title.trim()) return;

    try {
      const added = await apiFetch("/api/v1/profile/achievements", {
        method: "POST",
        body: JSON.stringify(newAch),
      });
      setAchievements([...achievements, added]);
      setNewAch({ title: "", category: "hackathon", issuer_or_event: "", year_or_date: "", description: "" });
      setShowAddAch(false);
      toast.success("Achievement added to knowledge base");
    } catch (e: any) {
      toast.error(e.message || "Failed to add achievement");
    }
  };

  const handleDeleteAchievement = async (id: number) => {
    try {
      await apiFetch(`/api/v1/profile/achievements/${id}`, { method: "DELETE" });
      setAchievements(achievements.filter((a) => a.id !== id));
      toast.success("Achievement removed");
    } catch (e: any) {
      toast.error("Failed to delete achievement");
    }
  };

  const handleAddCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCourse.name.trim()) return;

    const payload = {
      ...newCourse,
      skills_covered: newCourse.skills_covered.split(",").map((s) => s.trim()).filter(Boolean),
    };

    try {
      const added = await apiFetch("/api/v1/profile/courses", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setCourses([...courses, added]);
      setNewCourse({ name: "", issuer: "", issue_date: "", credential_url: "", skills_covered: "" });
      setShowAddCourse(false);
      toast.success("Course / Certification added to knowledge base");
    } catch (e: any) {
      toast.error(e.message || "Failed to add course");
    }
  };

  const handleDeleteCourse = async (id: number) => {
    try {
      await apiFetch(`/api/v1/profile/courses/${id}`, { method: "DELETE" });
      setCourses(courses.filter((c) => c.id !== id));
      toast.success("Course / Certification removed");
    } catch (e: any) {
      toast.error("Failed to delete course");
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file || isUploading || isAutofilling) return;

    if (!file.name.endsWith(".tex") && !file.name.endsWith(".pdf") && !file.name.endsWith(".docx") && !file.name.endsWith(".txt") && !file.name.endsWith(".md")) {
      toast.error("Unsupported file type. Use .tex, .pdf, .docx, .txt, or .md");
      return;
    }

    setIsUploading(true);
    setAutofillSummary("");
    const toastId = toast.loading("Uploading resume...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/resume/upload`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (res.ok) {
        toast.success("Resume uploaded. Click Autofill from resume to import its facts into your profile.", { id: toastId, duration: 6000 });
        await fetchResumes();
      } else if (res.status === 401) {
        window.location.href = "/login";
      } else {
        toast.error("Failed to upload.", { id: toastId });
      }
    } catch (e) {
      toast.error("Network error.", { id: toastId });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiFetch(`/api/v1/resume/${id}`, { method: "DELETE" });
      setResumes(resumes.filter((r) => r.id !== id));
      toast.success("Resume deleted.");
    } catch (e: any) {
      toast.error(e.message || "Failed to delete resume");
    }
  };

  const handleDownload = (id: number) => {
    window.open(`${API_BASE}/api/v1/resume/download/${id}`, "_blank");
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  };

  return (
    <fieldset disabled={isAutofilling} aria-busy={isAutofilling} className="min-w-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto pb-12">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Master Knowledge Base & Resumes</h1>
          <p className="text-sm text-zinc-500 mt-1">Connect GitHub, achievements, certifications, and master resumes for AI tailoring.</p>
        </div>
      </div>

      {/* GitHub Sync Section */}
      <div className="bg-gradient-to-r from-zinc-900 via-zinc-800 to-zinc-900 text-white rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-white shrink-0">
            <GithubIcon size={24} />
          </div>
          <div>
            <h3 className="text-base font-semibold">GitHub Integration</h3>
            <p className="text-xs text-zinc-400 mt-0.5">Auto-import repos, stars, tech stacks, and hackathon wins into your candidate database.</p>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="text"
            placeholder="GitHub username (e.g. Ari-Han-t)"
            value={githubUsername}
            onChange={(e) => setGithubUsername(e.target.value)}
            className="px-3 py-2 bg-zinc-800 border border-zinc-700 text-white text-sm rounded-lg focus:outline-none focus:border-indigo-500 w-full md:w-56"
          />
          <button
            onClick={handleSyncGithub}
            disabled={isSyncingGithub}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg flex items-center gap-2 transition-colors shrink-0 shadow-sm"
          >
            <RefreshCw size={16} className={isSyncingGithub ? "animate-spin" : ""} />
            {isSyncingGithub ? "Syncing..." : "Sync GitHub"}
          </button>
        </div>
      </div>

      {/* Upload Dropzone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center transition-colors ${
          isDragging ? "border-indigo-500 bg-indigo-50/50" : "border-zinc-200 bg-zinc-50/50 hover:bg-zinc-50"
        }`}
      >
        <div className="w-12 h-12 bg-white border border-zinc-200 rounded-full flex items-center justify-center shadow-sm mb-4 text-zinc-600">
          <UploadCloud size={20} />
        </div>
        <h3 className="text-sm font-medium text-zinc-900">Upload Master Resume</h3>
        <p className="text-xs text-zinc-500 mt-1 mb-4">Drag and drop LaTeX (.tex), PDF, DOCX, or Text resume</p>

        <input
          type="file"
          id="resume-upload"
          className="hidden"
          accept=".pdf,.docx,.tex,.txt,.md"
          disabled={isUploading || isAutofilling}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void handleFileUpload(file);
          }}
        />
        <label
          htmlFor="resume-upload"
          className="cursor-pointer px-4 py-2 bg-white border border-zinc-200 rounded-md text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 transition-colors"
        >
          {isUploading ? "Uploading..." : "Select File"}
        </label>
      </div>

      <section aria-labelledby="resume-autofill-heading" className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-5 space-y-3">
        <h2 id="resume-autofill-heading" className="text-sm font-semibold text-zinc-900">Autofill from resume</h2>
        <p className="text-sm text-zinc-600">Uses your latest uploaded resume with Gemini as the primary extractor and Groq as fallback. Preserves existing entries and fills only facts from your resume. Review all imported details; visa, work authorization, and preferences are never guessed.</p>
        <p className="text-xs text-zinc-500">Upload your resume above, then explicitly click Autofill from resume. Uploading alone does not parse it. Review your profile, experiences, projects, and skills in Settings, and achievements and courses below.</p>
        <button
          type="button"
          onClick={handleAutofill}
          disabled={isAutofilling || isUploading || isLoading || isSyncingGithub || resumes.length === 0}
          aria-busy={isAutofilling}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg inline-flex items-center gap-2 transition-colors"
        >
          <Sparkles size={16} />
          {isAutofilling ? "Autofilling..." : "Autofill from resume"}
        </button>
        {!isLoading && resumes.length === 0 && <p className="text-xs text-zinc-500">Upload a resume to enable autofill.</p>}
        {autofillSummary && <p role="status" className="text-sm text-emerald-700">{autofillSummary}</p>}
      </section>

      {/* Achievements, Hackathons & Prizes */}
      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
          <div className="flex items-center gap-2">
            <Award size={18} className="text-amber-500" />
            <h3 className="text-sm font-semibold text-zinc-900">Achievements, Hackathon Wins & Prizes</h3>
          </div>
          <button
            onClick={() => setShowAddAch(!showAddAch)}
            className="text-xs font-medium px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-md border border-indigo-100 hover:bg-indigo-100 flex items-center gap-1"
          >
            <Plus size={14} /> Add Achievement
          </button>
        </div>

        {showAddAch && (
          <form onSubmit={handleAddAchievement} className="p-4 bg-zinc-50 border-b border-zinc-200 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Title (e.g. 1st Place -- DEVSOC 2026 Hackathon)"
                value={newAch.title}
                onChange={(e) => setNewAch({ ...newAch, title: e.target.value })}
                required
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
              <input
                type="text"
                placeholder="Issuer / Event (e.g. DEVSOC 2026)"
                value={newAch.issuer_or_event}
                onChange={(e) => setNewAch({ ...newAch, issuer_or_event: e.target.value })}
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <select
                value={newAch.category}
                onChange={(e) => setNewAch({ ...newAch, category: e.target.value })}
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              >
                <option value="hackathon">Hackathon / Competition Win</option>
                <option value="award">Award / Honor</option>
                <option value="prize">Prize / Grant</option>
                <option value="publication">Research Publication</option>
                <option value="other">Other Achievement</option>
              </select>
              <input
                type="text"
                placeholder="Year (e.g. 2026)"
                value={newAch.year_or_date}
                onChange={(e) => setNewAch({ ...newAch, year_or_date: e.target.value })}
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
            </div>
            <textarea
              placeholder="Description & Impact Details..."
              value={newAch.description}
              onChange={(e) => setNewAch({ ...newAch, description: e.target.value })}
              rows={2}
              className="w-full px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAddAch(false)}
                className="px-3 py-1 text-xs text-zinc-600 hover:bg-zinc-200 rounded-md"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-3 py-1 text-xs bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-500"
              >
                Save Achievement
              </button>
            </div>
          </form>
        )}

        <div className="divide-y divide-zinc-100">
          {achievements.map((ach) => (
            <div key={ach.id} className="p-4 flex items-start justify-between hover:bg-zinc-50 transition-colors">
              <div>
                <h4 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                  {ach.title}
                  {ach.year_or_date && <span className="text-xs text-zinc-400 font-normal">[{ach.year_or_date}]</span>}
                </h4>
                {ach.issuer_or_event && <p className="text-xs text-indigo-600 font-medium mt-0.5">{ach.issuer_or_event}</p>}
                {ach.description && <p className="text-xs text-zinc-600 mt-1">{ach.description}</p>}
              </div>
              <button
                onClick={() => handleDeleteAchievement(ach.id)}
                className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {achievements.length === 0 && (
            <div className="p-6 text-center text-xs text-zinc-400">
              No achievements added yet. Sync GitHub or click 'Add Achievement' above.
            </div>
          )}
        </div>
      </div>

      {/* Courses & Certifications */}
      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
          <div className="flex items-center gap-2">
            <BookOpen size={18} className="text-indigo-600" />
            <h3 className="text-sm font-semibold text-zinc-900">Courses & Industry Certifications</h3>
          </div>
          <button
            onClick={() => setShowAddCourse(!showAddCourse)}
            className="text-xs font-medium px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-md border border-indigo-100 hover:bg-indigo-100 flex items-center gap-1"
          >
            <Plus size={14} /> Add Course / Certification
          </button>
        </div>

        {showAddCourse && (
          <form onSubmit={handleAddCourse} className="p-4 bg-zinc-50 border-b border-zinc-200 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Course / Certification Title"
                value={newCourse.name}
                onChange={(e) => setNewCourse({ ...newCourse, name: e.target.value })}
                required
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
              <input
                type="text"
                placeholder="Issuer (e.g. Coursera, DeepLearning.AI, AWS)"
                value={newCourse.issuer}
                onChange={(e) => setNewCourse({ ...newCourse, issuer: e.target.value })}
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Skills Covered (comma separated, e.g. PyTorch, CNNs)"
                value={newCourse.skills_covered}
                onChange={(e) => setNewCourse({ ...newCourse, skills_covered: e.target.value })}
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
              <input
                type="text"
                placeholder="Issue Date (e.g. 2025)"
                value={newCourse.issue_date}
                onChange={(e) => setNewCourse({ ...newCourse, issue_date: e.target.value })}
                className="px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
              />
            </div>
            <input
              type="text"
              placeholder="Credential URL (optional)"
              value={newCourse.credential_url}
              onChange={(e) => setNewCourse({ ...newCourse, credential_url: e.target.value })}
              className="w-full px-3 py-1.5 bg-white border border-zinc-200 rounded-md text-sm"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAddCourse(false)}
                className="px-3 py-1 text-xs text-zinc-600 hover:bg-zinc-200 rounded-md"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-3 py-1 text-xs bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-500"
              >
                Save Course
              </button>
            </div>
          </form>
        )}

        <div className="divide-y divide-zinc-100">
          {courses.map((crs) => (
            <div key={crs.id} className="p-4 flex items-start justify-between hover:bg-zinc-50 transition-colors">
              <div>
                <h4 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                  {crs.name}
                  {crs.issuer && <span className="text-xs text-zinc-500 font-normal">by {crs.issuer}</span>}
                </h4>
                {crs.skills_covered && crs.skills_covered.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {crs.skills_covered.map((s: string, idx: number) => (
                      <span key={idx} className="text-[10px] bg-zinc-100 text-zinc-600 px-1.5 py-0.5 rounded">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => handleDeleteCourse(crs.id)}
                className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {courses.length === 0 && (
            <div className="p-6 text-center text-xs text-zinc-400">
              No courses or certifications added yet. Click 'Add Course / Certification' above.
            </div>
          )}
        </div>
      </div>

      {/* Resume List */}
      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
          <h3 className="text-sm font-semibold text-zinc-900">Your Resumes</h3>
          <span className="text-xs font-medium px-2 py-1 bg-zinc-100 text-zinc-600 rounded-md">
            {resumes.length} versions
          </span>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-zinc-400">Loading resumes...</div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {resumes.map((resume) => (
              <div key={resume.id} className="p-4 flex items-center justify-between hover:bg-zinc-50 transition-colors group">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-zinc-900 flex items-center gap-2">
                      {resume.name}
                      {resume.type === "tex" && (
                        <span className="text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 uppercase">
                          LaTeX
                        </span>
                      )}
                    </h4>
                    <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
                      <span>{resume.date}</span>
                      <span>&bull;</span>
                      <span>{resume.size}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleDownload(resume.id)}
                    className="p-1.5 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded-md transition-colors"
                    title="Download"
                  >
                    <Download size={16} />
                  </button>
                  <button
                    onClick={() => handleDelete(resume.id)}
                    className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
            {resumes.length === 0 && !isLoading && (
              <div className="p-8 text-center text-zinc-400">
                No resumes uploaded yet. Upload your master resume to get started.
              </div>
            )}
          </div>
        )}
      </div>
    </fieldset>
  );
}

