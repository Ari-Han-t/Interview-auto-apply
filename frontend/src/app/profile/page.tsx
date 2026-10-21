"use client";

import { useState, useEffect } from "react";
import {
  UploadCloud,
  FileText,
  Trash2,
  Download,
  Sparkles,
  GitBranch,
  Award,
  BookOpen,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Star,
  Eye,
  EyeOff,
  Edit3,
  Layers,
  FolderArchive,
  ExternalLink,
  X,
  Check,
  ChevronRight,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { apiFetch, apiPost, apiPut, apiDelete, API_BASE } from "@/lib/api";

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

  // Review Modal State
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [reviewTab, setReviewTab] = useState("contact");
  const [reviewResumeId, setReviewResumeId] = useState<number | null>(null);
  const [reviewFileName, setReviewFileName] = useState("");
  const [reviewFileType, setReviewFileType] = useState("");
  const [reviewFlags, setReviewFlags] = useState<any[]>([]);
  const [applyToMaster, setApplyToMaster] = useState(true);
  const [setAsMaster, setSetAsMaster] = useState(false);
  const [targetRole, setTargetRole] = useState("General");
  const [versionNotes, setVersionNotes] = useState("");

  // Review Editable Facts
  const [reviewProfile, setReviewProfile] = useState<any>({
    full_name: "",
    preferred_name: "",
    email: "",
    phone: "",
    github: "",
    linkedin: "",
    portfolio: "",
    website: "",
    current_location: "",
    university: "",
    degree: "Bachelors",
    specialization: "",
    cgpa: null,
    graduation_year: null,
    coursework: [],
    bio: "",
    availability: "",
  });
  const [courseworkText, setCourseworkText] = useState("");
  const [reviewExperiences, setReviewExperiences] = useState<any[]>([]);
  const [reviewProjects, setReviewProjects] = useState<any[]>([]);
  const [reviewSkills, setReviewSkills] = useState<any[]>([]);
  const [newReviewSkill, setNewReviewSkill] = useState({ name: "", category: "Languages" });
  const [reviewAchievements, setReviewAchievements] = useState<any[]>([]);
  const [reviewCourses, setReviewCourses] = useState<any[]>([]);

  // New Version Modal State
  const [isNewVersionOpen, setIsNewVersionOpen] = useState(false);
  const [newVersionData, setNewVersionData] = useState({
    name: "",
    target_role: "Backend Engineer",
    notes: "",
    base_resume_id: null as number | null,
  });

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
      setResumes(data || []);
    } catch (e: any) {
      if (e.message !== "Unauthorized") {
        toast.error("Failed to load resumes");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file || isUploading || isAutofilling) return;

    const nameLower = file.name.toLowerCase();
    const validExts = [".tex", ".zip", ".pdf", ".docx", ".txt", ".md"];
    if (!validExts.some((ext) => nameLower.endsWith(ext))) {
      toast.error("Unsupported file type. Please upload LaTeX (.tex, .zip), PDF (.pdf), or Word (.docx)");
      return;
    }

    setIsUploading(true);
    setAutofillSummary("");
    const toastId = toast.loading(`Uploading and parsing ${file.name}...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/resume/upload`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(
          data.file_type === "zip"
            ? "LaTeX project ZIP uploaded & unpacked! Review extracted facts."
            : "Resume uploaded & parsed! Review extracted facts below.",
          { id: toastId, duration: 5000 }
        );
        await fetchResumes();
        // Automatically open the Review Screen for user inspection
        openReviewModal(data.id, data.filename, data.file_type, data.extracted_data, data.flags, data.is_master);
      } else if (res.status === 401) {
        window.location.href = "/login";
      } else {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        toast.error(err.detail || "Failed to upload.", { id: toastId });
      }
    } catch (e: any) {
      toast.error(e.message || "Network error during upload.", { id: toastId });
    } finally {
      setIsUploading(false);
    }
  };

  const openReviewModal = (
    resumeId: number,
    filename: string,
    fileType: string,
    extractedData: any,
    flags: any[] = [],
    isMaster: boolean = false
  ) => {
    setReviewResumeId(resumeId);
    setReviewFileName(filename);
    setReviewFileType(fileType);
    setReviewFlags(flags || []);
    setSetAsMaster(isMaster);
    setTargetRole("General");
    setVersionNotes(`Imported from ${filename}`);

    const prof = extractedData?.profile || {};
    setReviewProfile({
      full_name: prof.full_name || "",
      preferred_name: prof.preferred_name || "",
      email: prof.email || "",
      phone: prof.phone || "",
      github: prof.github || "",
      linkedin: prof.linkedin || "",
      portfolio: prof.portfolio || "",
      website: prof.website || "",
      current_location: prof.current_location || "",
      university: prof.university || "",
      degree: prof.degree || "Bachelors",
      specialization: prof.specialization || "",
      cgpa: prof.cgpa !== undefined ? prof.cgpa : null,
      graduation_year: prof.graduation_year !== undefined ? prof.graduation_year : null,
      coursework: prof.coursework || [],
      bio: prof.bio || "",
      availability: prof.availability || "",
    });
    setCourseworkText(Array.isArray(prof.coursework) ? prof.coursework.join(", ") : "");
    setReviewExperiences(extractedData?.experiences || extractedData?.experience || []);
    setReviewProjects(extractedData?.projects || []);
    setReviewSkills(extractedData?.skills || []);
    setReviewAchievements(extractedData?.achievements || []);
    setReviewCourses(extractedData?.courses || []);
    setReviewTab("contact");
    setIsReviewOpen(true);
  };

  const handleOpenExistingReview = async (resumeId: number) => {
    try {
      const data = await apiFetch(`/api/v1/resume/${resumeId}/preview`);
      openReviewModal(
        data.resume_id,
        data.name,
        data.file_type,
        data.extracted_data,
        data.flags,
        data.is_master
      );
    } catch (e: any) {
      toast.error(e.message || "Failed to load resume facts");
    }
  };

  const handleSaveReview = async () => {
    if (!reviewResumeId) return;

    setIsSavingReview(true);
    const toastId = toast.loading("Saving reviewed facts to candidate profile...");

    try {
      const courseworkList = courseworkText
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);

      const finalProfile = {
        ...reviewProfile,
        coursework: courseworkList,
      };

      const payload = {
        resume_id: reviewResumeId,
        apply_to_master_profile: applyToMaster,
        version_name: reviewFileName,
        target_role: targetRole,
        notes: versionNotes,
        is_master: setAsMaster,
        extracted_data: {
          profile: finalProfile,
          education: [
            {
              institution: finalProfile.university,
              degree: finalProfile.degree,
              specialization: finalProfile.specialization,
              graduation_year: finalProfile.graduation_year,
              cgpa: finalProfile.cgpa,
              coursework: courseworkList,
              location: finalProfile.current_location,
              is_visible: true,
            },
          ],
          experiences: reviewExperiences,
          projects: reviewProjects,
          skills: reviewSkills,
          achievements: reviewAchievements,
          courses: reviewCourses,
        },
      };

      const res = await apiPost("/api/v1/resume/review-and-save", payload);
      toast.success(res.message || "Profile facts successfully persisted!", { id: toastId, duration: 6000 });
      setIsReviewOpen(false);
      await Promise.all([fetchProfileData(), fetchResumes()]);
    } catch (e: any) {
      toast.error(e.message || "Failed to save profile review.", { id: toastId });
    } finally {
      setIsSavingReview(false);
    }
  };

  const handleSetMasterResume = async (resumeId: number) => {
    try {
      const res = await apiPost(`/api/v1/resume/versions/${resumeId}/set-master`, {});
      toast.success(res.message || "Master resume updated!");
      fetchResumes();
    } catch (e: any) {
      toast.error(e.message || "Failed to set master resume");
    }
  };

  const handleCreateNewVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVersionData.name.trim()) return;

    try {
      await apiPost("/api/v1/resume/versions", newVersionData);
      toast.success(`Created resume version variant: ${newVersionData.name}`);
      setIsNewVersionOpen(false);
      setNewVersionData({ name: "", target_role: "Backend Engineer", notes: "", base_resume_id: null });
      fetchResumes();
    } catch (e: any) {
      toast.error(e.message || "Failed to create resume version");
    }
  };

  const handleDeleteResume = async (id: number) => {
    if (!window.confirm("Delete this resume version?")) return;
    try {
      await apiDelete(`/api/v1/resume/${id}`);
      setResumes(resumes.filter((r) => r.id !== id));
      toast.success("Resume deleted.");
    } catch (e: any) {
      toast.error(e.message || "Failed to delete resume");
    }
  };

  const handleDownload = (id: number) => {
    window.open(`${API_BASE}/api/v1/resume/download/${id}`, "_blank");
  };

  const handleSyncGithub = async () => {
    if (!githubUsername.trim()) {
      toast.error("Please enter a valid GitHub username");
      return;
    }

    setIsSyncingGithub(true);
    const toastId = toast.loading("Syncing GitHub repositories & achievements...");

    try {
      const res = await apiPost("/api/v1/github/sync", {
        github_username: githubUsername.trim(),
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
      const added = await apiPost("/api/v1/profile/achievements", newAch);
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
      await apiDelete(`/api/v1/profile/achievements/${id}`);
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
      const added = await apiPost("/api/v1/profile/courses", payload);
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
      await apiDelete(`/api/v1/profile/courses/${id}`);
      setCourses(courses.filter((c) => c.id !== id));
      toast.success("Course / Certification removed");
    } catch (e: any) {
      toast.error("Failed to delete course");
    }
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
    <div className="min-w-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Candidate Profile & Resumes</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Single source of truth for your master profile, role-specific resume versions, and AI-tailored applications.
          </p>
        </div>
        <button
          onClick={() => setIsNewVersionOpen(true)}
          className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white text-sm font-medium rounded-lg inline-flex items-center gap-2 transition-colors shadow-sm"
        >
          <Plus size={16} /> New Resume Version
        </button>
      </div>

      {/* GitHub Integration Card */}
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

      {/* Resume Upload Dropzone */}
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
        <h3 className="text-sm font-semibold text-zinc-900">Upload Resume & Parse Facts</h3>
        <p className="text-xs text-zinc-500 mt-1 mb-4 max-w-md">
          Supports <span className="font-medium text-zinc-700">LaTeX (.tex)</span>,{" "}
          <span className="font-medium text-zinc-700">ZIP project archives</span>, PDF, and Word DOCX resumes.
          Original files are preserved untouched in private storage.
        </p>

        <input
          type="file"
          id="resume-upload"
          className="hidden"
          accept=".pdf,.docx,.tex,.zip,.txt,.md"
          disabled={isUploading || isAutofilling}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void handleFileUpload(file);
          }}
        />
        <label
          htmlFor="resume-upload"
          className="cursor-pointer px-4 py-2 bg-white border border-zinc-200 rounded-md text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 transition-colors inline-flex items-center gap-2"
        >
          {isUploading ? (
            <>
              <RefreshCw size={14} className="animate-spin" /> Uploading & Parsing...
            </>
          ) : (
            <>
              <UploadCloud size={14} /> Select File (.tex, .zip, .pdf, .docx)
            </>
          )}
        </label>
      </div>

      {/* Resume Versions Section */}
      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
          <div className="flex items-center gap-2">
            <Layers size={18} className="text-zinc-700" />
            <h3 className="text-sm font-semibold text-zinc-900">Resume Versions & Master Source</h3>
          </div>
          <span className="text-xs font-medium px-2 py-1 bg-zinc-100 text-zinc-600 rounded-md">
            {resumes.length} versions
          </span>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-zinc-400">Loading resumes...</div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {resumes.map((resume) => (
              <div key={resume.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-zinc-50/50 transition-colors">
                <div className="flex items-start gap-3.5">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                    resume.is_master ? "bg-amber-50 text-amber-600 border border-amber-200" : "bg-zinc-100 text-zinc-600"
                  }`}>
                    {resume.file_type === "zip" ? <FolderArchive size={20} /> : <FileText size={20} />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-sm font-semibold text-zinc-900">{resume.name}</h4>
                      {resume.is_master && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                          <Star size={11} className="fill-amber-600 text-amber-600" /> Master Resume
                        </span>
                      )}
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600 uppercase">
                        {resume.file_type}
                      </span>
                      {resume.target_role && (
                        <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-indigo-50 text-indigo-700">
                          Role: {resume.target_role}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
                      <span>Version v{resume.version_number || 1}</span>
                      <span>&bull;</span>
                      <span>{new Date(resume.created_at).toLocaleDateString()}</span>
                      {resume.notes && (
                        <>
                          <span>&bull;</span>
                          <span className="text-zinc-600 italic">"{resume.notes}"</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
                  <button
                    onClick={() => handleOpenExistingReview(resume.id)}
                    className="px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-md border border-indigo-100 flex items-center gap-1.5 transition-colors"
                    title="Review & Edit Extracted Facts"
                  >
                    <Edit3 size={13} /> Review Extracted Facts
                  </button>

                  {!resume.is_master && (
                    <button
                      onClick={() => handleSetMasterResume(resume.id)}
                      className="px-2.5 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 rounded-md border border-zinc-200 flex items-center gap-1 transition-colors"
                      title="Set as master resume"
                    >
                      <Star size={13} /> Set as Master
                    </button>
                  )}

                  <button
                    onClick={() => handleDownload(resume.id)}
                    className="p-1.5 text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 rounded-md border border-zinc-200 transition-colors"
                    title="Download stored file"
                  >
                    <Download size={15} />
                  </button>
                  <button
                    onClick={() => handleDeleteResume(resume.id)}
                    className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-md border border-zinc-200 transition-colors"
                    title="Delete version"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
            {resumes.length === 0 && !isLoading && (
              <div className="p-8 text-center text-zinc-400 text-sm">
                No resumes uploaded yet. Upload your LaTeX or PDF resume above to start building your candidate profile.
              </div>
            )}
          </div>
        )}
      </div>

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

      {/* ============================================================ */}
      {/* RESUME REVIEW & EDIT SCREEN MODAL                            */}
      {/* ============================================================ */}
      {isReviewOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-zinc-200 overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-zinc-900">Review Extracted Resume Facts</h2>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 uppercase">
                    {reviewFileType}
                  </span>
                </div>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Review and edit facts from <span className="font-semibold text-zinc-700">{reviewFileName}</span> before saving to your master profile.
                </p>
              </div>
              <button
                onClick={() => setIsReviewOpen(false)}
                className="p-1.5 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200/50 rounded-lg transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Parsing Flags & Warnings Banner */}
            {reviewFlags && reviewFlags.length > 0 && (
              <div className="px-6 py-3 bg-amber-50 border-b border-amber-100 flex items-start gap-2.5 text-xs text-amber-800">
                <AlertCircle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <span className="font-semibold">Parser Observations:</span>
                  <ul className="list-disc list-inside mt-0.5 space-y-0.5">
                    {reviewFlags.map((flag, idx) => (
                      <li key={idx}>{flag.message || flag}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Modal Tab Navigation */}
            <div className="px-6 border-b border-zinc-200 bg-white flex gap-1 overflow-x-auto text-xs font-medium">
              {[
                { id: "contact", label: "Contact & Education" },
                { id: "experience", label: `Experience (${reviewExperiences.length})` },
                { id: "projects", label: `Projects (${reviewProjects.length})` },
                { id: "skills", label: `Skills (${reviewSkills.length})` },
                { id: "achievements", label: `Achievements (${reviewAchievements.length})` },
                { id: "courses", label: `Courses (${reviewCourses.length})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setReviewTab(tab.id)}
                  className={`py-3 px-3 border-b-2 transition-colors whitespace-nowrap ${
                    reviewTab === tab.id
                      ? "border-indigo-600 text-indigo-600 font-semibold"
                      : "border-transparent text-zinc-500 hover:text-zinc-900"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {/* TAB 1: Contact & Education */}
              {reviewTab === "contact" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900 mb-3">Personal & Contact Details</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Full Name</label>
                        <input
                          type="text"
                          value={reviewProfile.full_name || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, full_name: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Preferred Name</label>
                        <input
                          type="text"
                          value={reviewProfile.preferred_name || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, preferred_name: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Email</label>
                        <input
                          type="email"
                          value={reviewProfile.email || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, email: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Phone</label>
                        <input
                          type="text"
                          value={reviewProfile.phone || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, phone: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">GitHub Profile</label>
                        <input
                          type="text"
                          value={reviewProfile.github || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, github: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">LinkedIn Profile</label>
                        <input
                          type="text"
                          value={reviewProfile.linkedin || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, linkedin: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Portfolio Website</label>
                        <input
                          type="text"
                          value={reviewProfile.portfolio || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, portfolio: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Current Location</label>
                        <input
                          type="text"
                          value={reviewProfile.current_location || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, current_location: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-zinc-200">
                    <h3 className="text-sm font-semibold text-zinc-900 mb-3">Education & Academic Record</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      <div>
                        <label className="text-xs font-medium text-zinc-700">University / Institution</label>
                        <input
                          type="text"
                          value={reviewProfile.university || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, university: e.target.value })}
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Degree</label>
                        <input
                          type="text"
                          value={reviewProfile.degree || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, degree: e.target.value })}
                          placeholder="B.Tech, B.S., etc."
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-zinc-700">Specialization / Major</label>
                        <input
                          type="text"
                          value={reviewProfile.specialization || ""}
                          onChange={(e) => setReviewProfile({ ...reviewProfile, specialization: e.target.value })}
                          placeholder="Computer Science & Engineering"
                          className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-xs font-medium text-zinc-700">CGPA / GPA</label>
                          <input
                            type="number"
                            step="0.01"
                            value={reviewProfile.cgpa !== null ? reviewProfile.cgpa : ""}
                            onChange={(e) => setReviewProfile({ ...reviewProfile, cgpa: e.target.value ? parseFloat(e.target.value) : null })}
                            className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                          />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-zinc-700">Graduation Year</label>
                          <input
                            type="number"
                            value={reviewProfile.graduation_year !== null ? reviewProfile.graduation_year : ""}
                            onChange={(e) => setReviewProfile({ ...reviewProfile, graduation_year: e.target.value ? parseInt(e.target.value) : null })}
                            className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                          />
                        </div>
                      </div>
                    </div>
                    <div className="mt-3">
                      <label className="text-xs font-medium text-zinc-700">Coursework (comma-separated)</label>
                      <input
                        type="text"
                        value={courseworkText}
                        onChange={(e) => setCourseworkText(e.target.value)}
                        placeholder="Data Structures, Algorithms, OS, DBMS..."
                        className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Experience */}
              {reviewTab === "experience" && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-zinc-900">Extracted Experiences & Internships</h3>
                    <button
                      type="button"
                      onClick={() =>
                        setReviewExperiences([
                          ...reviewExperiences,
                          {
                            company: "Company Name",
                            title: "Role Title",
                            internship_or_fulltime: "internship",
                            start_date: "",
                            end_date: "",
                            description: "",
                            is_visible: true,
                          },
                        ])
                      }
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                    >
                      <Plus size={14} /> Add Experience
                    </button>
                  </div>

                  {reviewExperiences.map((exp, idx) => (
                    <div key={idx} className="p-4 border border-zinc-200 rounded-xl bg-zinc-50/40 space-y-3">
                      <div className="flex justify-between items-start gap-2">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1">
                          <input
                            type="text"
                            placeholder="Company"
                            value={exp.company || ""}
                            onChange={(e) => {
                              const updated = [...reviewExperiences];
                              updated[idx].company = e.target.value;
                              setReviewExperiences(updated);
                            }}
                            className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                          />
                          <input
                            type="text"
                            placeholder="Title / Role"
                            value={exp.title || ""}
                            onChange={(e) => {
                              const updated = [...reviewExperiences];
                              updated[idx].title = e.target.value;
                              setReviewExperiences(updated);
                            }}
                            className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => setReviewExperiences(reviewExperiences.filter((_, i) => i !== idx))}
                          className="p-1 text-zinc-400 hover:text-red-600 rounded"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <select
                          value={exp.internship_or_fulltime || "fulltime"}
                          onChange={(e) => {
                            const updated = [...reviewExperiences];
                            updated[idx].internship_or_fulltime = e.target.value;
                            setReviewExperiences(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                        >
                          <option value="internship">Internship</option>
                          <option value="fulltime">Full-time</option>
                        </select>
                        <input
                          type="text"
                          placeholder="Dates (e.g. 2024 - 2025)"
                          value={exp.start_date ? `${exp.start_date} - ${exp.end_date || "Present"}` : exp.dates || ""}
                          onChange={(e) => {
                            const updated = [...reviewExperiences];
                            updated[idx].start_date = e.target.value;
                            setReviewExperiences(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                        />
                        <label className="flex items-center gap-2 text-xs text-zinc-700 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={exp.is_visible !== false}
                            onChange={(e) => {
                              const updated = [...reviewExperiences];
                              updated[idx].is_visible = e.target.checked;
                              setReviewExperiences(updated);
                            }}
                            className="rounded text-indigo-600"
                          />
                          Include in AI applications
                        </label>
                      </div>

                      <textarea
                        rows={3}
                        placeholder="Bullets / Description..."
                        value={exp.description || (exp.highlights ? exp.highlights.join("\n") : "")}
                        onChange={(e) => {
                          const updated = [...reviewExperiences];
                          updated[idx].description = e.target.value;
                          setReviewExperiences(updated);
                        }}
                        className="w-full px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                      />
                    </div>
                  ))}
                  {reviewExperiences.length === 0 && (
                    <p className="text-xs text-zinc-400 italic">No experiences parsed. Click 'Add Experience' to add one manually.</p>
                  )}
                </div>
              )}

              {/* TAB 3: Projects */}
              {reviewTab === "projects" && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-zinc-900">Extracted Projects</h3>
                    <button
                      type="button"
                      onClick={() =>
                        setReviewProjects([
                          ...reviewProjects,
                          { name: "New Project", technologies: [], github: "", live_link: "", description: "", is_visible: true },
                        ])
                      }
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                    >
                      <Plus size={14} /> Add Project
                    </button>
                  </div>

                  {reviewProjects.map((proj, idx) => (
                    <div key={idx} className="p-4 border border-zinc-200 rounded-xl bg-zinc-50/40 space-y-3">
                      <div className="flex justify-between items-start gap-2">
                        <input
                          type="text"
                          placeholder="Project Name"
                          value={proj.name || ""}
                          onChange={(e) => {
                            const updated = [...reviewProjects];
                            updated[idx].name = e.target.value;
                            setReviewProjects(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white font-semibold flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => setReviewProjects(reviewProjects.filter((_, i) => i !== idx))}
                          className="p-1 text-zinc-400 hover:text-red-600 rounded"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <input
                          type="text"
                          placeholder="Technologies (comma-separated, e.g. Python, FastAPI, Docker)"
                          value={Array.isArray(proj.technologies) ? proj.technologies.join(", ") : proj.technologies || ""}
                          onChange={(e) => {
                            const updated = [...reviewProjects];
                            updated[idx].technologies = e.target.value.split(",").map((t: string) => t.trim()).filter(Boolean);
                            setReviewProjects(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                        />
                        <input
                          type="text"
                          placeholder="GitHub URL"
                          value={proj.github || ""}
                          onChange={(e) => {
                            const updated = [...reviewProjects];
                            updated[idx].github = e.target.value;
                            setReviewProjects(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                        />
                      </div>

                      <textarea
                        rows={3}
                        placeholder="Project description & achievements..."
                        value={proj.description || (proj.highlights ? proj.highlights.join("\n") : "")}
                        onChange={(e) => {
                          const updated = [...reviewProjects];
                          updated[idx].description = e.target.value;
                          setReviewProjects(updated);
                        }}
                        className="w-full px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white"
                      />
                    </div>
                  ))}
                  {reviewProjects.length === 0 && (
                    <p className="text-xs text-zinc-400 italic">No projects parsed. Click 'Add Project' to add one manually.</p>
                  )}
                </div>
              )}

              {/* TAB 4: Skills */}
              {reviewTab === "skills" && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-zinc-900">Extracted Skills</h3>
                  </div>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add skill (e.g. FastAPI)"
                      value={newReviewSkill.name}
                      onChange={(e) => setNewReviewSkill({ ...newReviewSkill, name: e.target.value })}
                      className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm flex-1"
                    />
                    <select
                      value={newReviewSkill.category}
                      onChange={(e) => setNewReviewSkill({ ...newReviewSkill, category: e.target.value })}
                      className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm"
                    >
                      <option value="Languages">Languages</option>
                      <option value="Backend">Backend</option>
                      <option value="Databases">Databases</option>
                      <option value="Cloud & DevOps">Cloud & DevOps</option>
                      <option value="AI & ML">AI & ML</option>
                      <option value="Core CS">Core CS</option>
                      <option value="General">General</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => {
                        if (newReviewSkill.name.trim()) {
                          setReviewSkills([...reviewSkills, { name: newReviewSkill.name.trim(), category: newReviewSkill.category, confidence: 5 }]);
                          setNewReviewSkill({ name: "", category: "Languages" });
                        }
                      }}
                      className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm font-medium"
                    >
                      Add
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-2">
                    {reviewSkills.map((sk, idx) => {
                      const name = typeof sk === "string" ? sk : sk.name;
                      const cat = typeof sk === "object" ? sk.category : "General";
                      return (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-zinc-100 hover:bg-zinc-200 text-zinc-800 rounded-lg text-xs font-medium transition-colors"
                        >
                          <span>{name}</span>
                          {cat && <span className="text-[10px] text-zinc-400">({cat})</span>}
                          <button
                            type="button"
                            onClick={() => setReviewSkills(reviewSkills.filter((_, i) => i !== idx))}
                            className="text-zinc-400 hover:text-red-600"
                          >
                            <X size={12} />
                          </button>
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* TAB 5: Achievements */}
              {reviewTab === "achievements" && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-zinc-900">Extracted Achievements & Honors</h3>
                    <button
                      type="button"
                      onClick={() =>
                        setReviewAchievements([
                          ...reviewAchievements,
                          { title: "New Achievement", category: "hackathon", year_or_date: "", description: "" },
                        ])
                      }
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                    >
                      <Plus size={14} /> Add Achievement
                    </button>
                  </div>

                  {reviewAchievements.map((ach, idx) => (
                    <div key={idx} className="p-3 border border-zinc-200 rounded-xl bg-zinc-50/40 space-y-2">
                      <div className="flex justify-between items-center gap-2">
                        <input
                          type="text"
                          placeholder="Achievement Title"
                          value={ach.title || ""}
                          onChange={(e) => {
                            const updated = [...reviewAchievements];
                            updated[idx].title = e.target.value;
                            setReviewAchievements(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white font-medium flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => setReviewAchievements(reviewAchievements.filter((_, i) => i !== idx))}
                          className="p-1 text-zinc-400 hover:text-red-600 rounded"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 6: Courses */}
              {reviewTab === "courses" && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-zinc-900">Extracted Courses & Certifications</h3>
                    <button
                      type="button"
                      onClick={() =>
                        setReviewCourses([
                          ...reviewCourses,
                          { name: "Course Title", issuer: "", issue_date: "", skills_covered: [] },
                        ])
                      }
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                    >
                      <Plus size={14} /> Add Course
                    </button>
                  </div>

                  {reviewCourses.map((crs, idx) => (
                    <div key={idx} className="p-3 border border-zinc-200 rounded-xl bg-zinc-50/40 space-y-2">
                      <div className="flex justify-between items-center gap-2">
                        <input
                          type="text"
                          placeholder="Course / Certification Title"
                          value={crs.name || ""}
                          onChange={(e) => {
                            const updated = [...reviewCourses];
                            updated[idx].name = e.target.value;
                            setReviewCourses(updated);
                          }}
                          className="px-3 py-1.5 border border-zinc-200 rounded-md text-sm bg-white font-medium flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => setReviewCourses(reviewCourses.filter((_, i) => i !== idx))}
                          className="p-1 text-zinc-400 hover:text-red-600 rounded"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer & Persistence Settings */}
            <div className="p-5 border-t border-zinc-200 bg-zinc-50 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <label className="flex items-center gap-2 text-xs font-semibold text-zinc-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={applyToMaster}
                    onChange={(e) => setApplyToMaster(e.target.checked)}
                    className="rounded text-indigo-600"
                  />
                  <span>Apply reviewed facts to Candidate Master Profile (Single Source of Truth)</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-zinc-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={setAsMaster}
                    onChange={(e) => setSetAsMaster(e.target.checked)}
                    className="rounded text-indigo-600"
                  />
                  <span>Set this version as your Master Resume</span>
                </label>
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                <button
                  type="button"
                  onClick={() => setIsReviewOpen(false)}
                  className="px-4 py-2 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:bg-zinc-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveReview}
                  disabled={isSavingReview}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm"
                >
                  {isSavingReview ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" /> Saving...
                    </>
                  ) : (
                    <>
                      <Check size={14} /> Save & Apply to Profile
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* NEW RESUME VERSION VARIANT MODAL                             */}
      {/* ============================================================ */}
      {isNewVersionOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-zinc-200 space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-semibold text-zinc-900">Create New Resume Version</h3>
              <button onClick={() => setIsNewVersionOpen(false)} className="text-zinc-400 hover:text-zinc-700">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateNewVersion} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-zinc-700">Version Name</label>
                <input
                  type="text"
                  placeholder="e.g. AI Engineering Specialist, Backend Heavy"
                  value={newVersionData.name}
                  onChange={(e) => setNewVersionData({ ...newVersionData, name: e.target.value })}
                  required
                  className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-700">Target Role Category</label>
                <input
                  type="text"
                  placeholder="e.g. AI / Machine Learning, Backend, Fullstack"
                  value={newVersionData.target_role}
                  onChange={(e) => setNewVersionData({ ...newVersionData, target_role: e.target.value })}
                  className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-700">Branch from Existing Resume</label>
                <select
                  value={newVersionData.base_resume_id || ""}
                  onChange={(e) =>
                    setNewVersionData({
                      ...newVersionData,
                      base_resume_id: e.target.value ? parseInt(e.target.value) : null,
                    })
                  }
                  className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm bg-white"
                >
                  <option value="">-- None (Start Clean) --</option>
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} {r.is_master ? "(Master)" : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-700">Notes & Tailoring Goals</label>
                <textarea
                  rows={2}
                  placeholder="Notes about when to use this variant..."
                  value={newVersionData.notes}
                  onChange={(e) => setNewVersionData({ ...newVersionData, notes: e.target.value })}
                  className="mt-1 w-full px-3 py-1.5 border border-zinc-200 rounded-lg text-sm"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsNewVersionOpen(false)}
                  className="px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-zinc-900 text-white rounded-lg text-xs font-medium hover:bg-zinc-800"
                >
                  Create Version
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
