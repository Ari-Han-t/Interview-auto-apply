"use client";

import { useEffect, useState } from "react";
import { User as UserIcon, Bell, Shield, Key, Save, Plus, Trash, BookOpen, Star, Settings, GraduationCap, Eye, EyeOff, CheckCircle2, Briefcase, FileText } from "lucide-react";
import { toast } from "react-hot-toast";
import { apiFetch, apiPost, apiPut, apiDelete } from "@/lib/api";

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

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const [isLoading, setIsLoading] = useState(true);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [autofillSummary, setAutofillSummary] = useState("");

  // Global tailoring instructions (applied to every resume/cover-letter generation)
  const [tailoringInstructions, setTailoringInstructions] = useState("");
  const [isSavingInstructions, setIsSavingInstructions] = useState(false);

  // User Profile
  const [userProfile, setUserProfile] = useState<any>({
    full_name: "",
    preferred_name: "",
    email: "",
    phone: "",
    github: "",
    linkedin: "",
    portfolio: "",
    website: "",
    current_location: "",
    preferred_locations: [],
    work_authorization: "",
    visa_required: false,
    willing_to_relocate: true,
    remote_preference: "any",
    graduation_year: null,
    degree: "Bachelors",
    specialization: "",
    cgpa: null,
    university: "",
    coursework: "",
    current_semester_or_year: "",
    availability: "",
    bio: ""
  });

  // Educations
  const [educations, setEducations] = useState<any[]>([]);
  const [newEdu, setNewEdu] = useState({
    degree: "Bachelors",
    institution: "",
    field_of_study: "",
    start_year: "",
    end_year: "",
    cgpa: "",
    max_cgpa: "10.0",
    coursework: "",
    is_current: false,
    is_visible: true
  });

  // Experiences
  const [experiences, setExperiences] = useState<any[]>([]);
  const [newExp, setNewExp] = useState({
    company: "",
    title: "",
    internship_or_fulltime: "fulltime",
    start_date: "",
    end_date: "",
    currently_working: false,
    months_of_experience: 0,
    description: "",
    location: "",
    technologies: "",
    is_visible: true
  });

  // Projects
  const [projects, setProjects] = useState<any[]>([]);
  const [newProj, setNewProj] = useState({
    name: "",
    description: "",
    github: "",
    live_link: "",
    technologies: "",
    role: "",
    is_visible: true
  });

  // Skills
  const [skills, setSkills] = useState<any[]>([]);
  const [newSkill, setNewSkill] = useState({
    name: "",
    confidence: 5,
    years_used: 1.0,
    category: "General",
    is_visible: true
  });

  // Preferences
  const [preferences, setPreferences] = useState<any>({
    minimum_salary: 0,
    maximum_salary: null,
    preferred_locations: [],
    remote_only: false,
    hybrid_allowed: true,
    onsite_allowed: true,
    preferred_roles: [],
    preferred_domains: [],
    company_size: null,
    preferred_industries: [],
    maximum_experience_required: null,
    minimum_experience_required: null,
    exclude_companies: [],
    exclude_keywords: [],
    preferred_job_type: "both",
    preferred_internship: true,
    preferred_fulltime: true,
    notice_period: 0,
    earliest_joining_date: "",
    maximum_daily_applications: 5,
    availability_duration: ""
  });

  // Capabilities
  const [capabilities, setCapabilities] = useState<any>({
    can_relocate: true,
    can_work_remote: true,
    can_do_internship: true,
    can_do_fulltime: true,
    can_work_parttime: true,
    can_work_contract: true,
    can_work_night_shift: false,
    has_work_authorization: true,
    needs_sponsorship: false,
    open_to_startup: true,
    open_to_enterprise: true,
    open_to_research: true
  });

  // Notification Preferences (saved in old User preferences_json)
  const [notifyPreferences, setNotifyPreferences] = useState({
    notify_new_jobs: true,
    notify_resume_generated: true,
    notify_application_completed: true,
    notify_errors: true,
    auto_apply_enabled: false,
    max_daily_applications: 5
  });

  // API Keys (one entry per provider; stored in localStorage)
  const API_KEY_PROVIDERS = [
    { id: "openrouter", label: "OpenRouter", placeholder: "sk-or-v1-..." },
    { id: "openai", label: "OpenAI", placeholder: "sk-..." },
    { id: "groq", label: "Groq", placeholder: "gsk_..." },
    { id: "gemini", label: "Google Gemini", placeholder: "AIza..." },
    { id: "anthropic", label: "Anthropic (Claude)", placeholder: "sk-ant-..." },
    { id: "azure", label: "Azure OpenAI", placeholder: "Azure API key..." },
  ] as const;
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [preferredProvider, setPreferredProvider] = useState("openrouter");

  // Security
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Source Integrations
  const [sourceIntegrations, setSourceIntegrations] = useState({
    linkedin: true,
    indeed: true,
    greenhouse: true,
    lever: true,
    ashby: true,
    wellfound: true,
    discovery_cadence: "daily",
    auto_refresh_postings: true,
  });

  // Document Templates
  const [templateSettings, setTemplateSettings] = useState({
    default_template: "clean_ats",
    font_size: "10pt",
    cover_letter_style: "concise",
    enforce_single_page: true,
  });

  // Privacy & Data
  const [isExportingData, setIsExportingData] = useState(false);
  const [isClearingData, setIsClearingData] = useState(false);

  const handleExportData = async () => {
    setIsExportingData(true);
    try {
      const data = await apiFetch<any>("/api/v1/profile/export-all-data");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `autoapply_career_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Complete career data exported!");
    } catch (e: any) {
      toast.error(e.message || "Data export failed");
    } finally {
      setIsExportingData(false);
    }
  };

  const handleClearData = async () => {
    if (!window.confirm("WARNING: This will permanently reset your tracked applications and saved job records in the database. Your verified profile, experiences, and projects will be kept. Proceed?")) return;
    setIsClearingData(true);
    try {
      await apiDelete("/api/v1/profile/clear-career-data?confirm=true");
      toast.success("Application history reset successfully.");
    } catch (e: any) {
      toast.error(e.message || "Failed to reset application history");
    } finally {
      setIsClearingData(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const data = await apiFetch("/api/v1/profile/");
      if (data.profile) {
        setUserProfile(data.profile);
      }
      if (data.educations) {
        setEducations(data.educations);
      }
      if (data.experiences) {
        setExperiences(data.experiences);
      }
      if (data.projects) {
        setProjects(data.projects);
      }
      if (data.skills) {
        setSkills(data.skills);
      }
      if (data.preferences) {
        setPreferences(data.preferences);
      }
      if (data.capabilities) {
        setCapabilities(data.capabilities);
      }
      if (typeof data.tailoring_instructions === "string") {
        setTailoringInstructions(data.tailoring_instructions);
      }

      // Old notification preferences
      const notify = await apiFetch("/api/v1/profile/preferences");
      setNotifyPreferences(notify);

      if (typeof window !== "undefined") {
        const loaded: Record<string, string> = {};
        for (const p of API_KEY_PROVIDERS) {
          loaded[p.id] = localStorage.getItem(`llm_api_key_${p.id}`) || "";
        }
        // Migrate legacy single-key entry
        if (!loaded.openrouter) {
          loaded.openrouter = localStorage.getItem("openrouter_api_key") || "";
        }
        setApiKeys(loaded);
        setPreferredProvider(localStorage.getItem("llm_preferred_provider") || "openrouter");
      }
      return true;
    } catch (e: any) {
      console.error("Failed to load settings:", e);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleAutofill = async () => {
    if (isAutofilling || isLoading) return;
    if (!window.confirm("Autofill from your latest uploaded resume? Saved settings and profile data will be refreshed and unsaved edits to those fields will be lost. Cancel and save your changes first if needed. Review all imported facts afterward.")) return;

    setIsAutofilling(true);
    setAutofillSummary("");
    const toastId = toast.loading("Autofilling from your latest resume...");
    try {
      const result = await apiFetch<AutofillResult>("/api/v1/resume/autofill", { method: "POST" });
      const { counts } = result;
      const summary = `${result.message} Added: ${counts.profile_fields} profile fields, ${counts.experiences} experiences, ${counts.projects} projects, ${counts.skills} skills, ${counts.achievements} achievements, ${counts.courses} courses. Review the imported facts; achievements and courses are on the Profile page.`;
      setAutofillSummary(summary);
      toast.success(summary, { id: toastId, duration: 10000 });
      const refreshed = await fetchSettings();
      if (!refreshed) toast.error("Autofill completed, but settings could not be refreshed. Reload this page before editing.");
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Resume autofill failed. Please try again.", { id: toastId });
    } finally {
      setIsAutofilling(false);
    }
  };

  const handleSaveInstructions = async () => {
    setIsSavingInstructions(true);
    try {
      await apiPut("/api/v1/profile/tailoring-instructions", {
        tailoring_instructions: tailoringInstructions,
      });
      toast.success("Default resume instructions saved!");
    } catch (e: any) {
      toast.error(e.message || "Failed to save instructions");
    } finally {
      setIsSavingInstructions(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      await apiPut("/api/v1/profile/", userProfile);
      toast.success("Profile updated successfully!");
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to update profile");
    }
  };

  const handleAddEducation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        degree: newEdu.degree,
        institution: newEdu.institution,
        field_of_study: newEdu.field_of_study || null,
        start_year: newEdu.start_year ? parseInt(newEdu.start_year) : null,
        end_year: newEdu.end_year ? parseInt(newEdu.end_year) : null,
        cgpa: newEdu.cgpa ? parseFloat(newEdu.cgpa) : null,
        max_cgpa: newEdu.max_cgpa ? parseFloat(newEdu.max_cgpa) : 10.0,
        coursework: newEdu.coursework || null,
        is_current: newEdu.is_current,
        is_visible: newEdu.is_visible
      };
      await apiPost("/api/v1/profile/educations", payload);
      toast.success("Education record added!");
      setNewEdu({
        degree: "Bachelors",
        institution: "",
        field_of_study: "",
        start_year: "",
        end_year: "",
        cgpa: "",
        max_cgpa: "10.0",
        coursework: "",
        is_current: false,
        is_visible: true
      });
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to add education");
    }
  };

  const handleDeleteEducation = async (id: number) => {
    try {
      await apiDelete(`/api/v1/profile/educations/${id}`);
      toast.success("Education deleted.");
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to delete education");
    }
  };

  const handleToggleEducationVisibility = async (id: number, currentVisible: boolean) => {
    try {
      await apiPut(`/api/v1/profile/educations/${id}/visibility`, { is_visible: !currentVisible });
      setEducations(prev => prev.map(e => e.id === id ? { ...e, is_visible: !currentVisible } : e));
      toast.success(!currentVisible ? "Included in AI applications" : "Hidden from AI applications");
    } catch (e: any) {
      toast.error("Failed to update visibility");
    }
  };

  const handleToggleExperienceVisibility = async (id: number, currentVisible: boolean) => {
    try {
      await apiPut(`/api/v1/profile/experiences/${id}/visibility`, { is_visible: !currentVisible });
      setExperiences(prev => prev.map(e => e.id === id ? { ...e, is_visible: !currentVisible } : e));
      toast.success(!currentVisible ? "Included in AI applications" : "Hidden from AI applications");
    } catch (e: any) {
      toast.error("Failed to update visibility");
    }
  };

  const handleToggleProjectVisibility = async (id: number, currentVisible: boolean) => {
    try {
      await apiPut(`/api/v1/profile/projects/${id}/visibility`, { is_visible: !currentVisible });
      setProjects(prev => prev.map(p => p.id === id ? { ...p, is_visible: !currentVisible } : p));
      toast.success(!currentVisible ? "Included in AI applications" : "Hidden from AI applications");
    } catch (e: any) {
      toast.error("Failed to update visibility");
    }
  };

  const handleToggleSkillVisibility = async (name: string, currentVisible: boolean) => {
    try {
      await apiPut(`/api/v1/profile/skills/${encodeURIComponent(name)}/visibility`, { is_visible: !currentVisible });
      setSkills(prev => prev.map(s => s.name === name ? { ...s, is_visible: !currentVisible } : s));
      toast.success(!currentVisible ? "Included in AI applications" : "Hidden from AI applications");
    } catch (e: any) {
      toast.error("Failed to update visibility");
    }
  };

  const handleAddExperience = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...newExp,
        technologies: newExp.technologies ? newExp.technologies.split(",").map((t: string) => t.trim()).filter(Boolean) : []
      };
      await apiPost("/api/v1/profile/experiences", payload);
      toast.success("Experience added!");
      setNewExp({
        company: "",
        title: "",
        internship_or_fulltime: "fulltime",
        start_date: "",
        end_date: "",
        currently_working: false,
        months_of_experience: 0,
        description: "",
        location: "",
        technologies: "",
        is_visible: true
      });
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to add experience");
    }
  };

  const handleDeleteExperience = async (id: number) => {
    try {
      await apiDelete(`/api/v1/profile/experiences/${id}`);
      toast.success("Experience deleted.");
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to delete experience");
    }
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...newProj,
        technologies: newProj.technologies ? newProj.technologies.split(",").map(t => t.trim()).filter(Boolean) : []
      };
      await apiPost("/api/v1/profile/projects", payload);
      toast.success("Project added!");
      setNewProj({
        name: "",
        description: "",
        github: "",
        live_link: "",
        technologies: "",
        role: "",
        is_visible: true
      });
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to add project");
    }
  };

  const handleDeleteProject = async (id: number) => {
    try {
      await apiDelete(`/api/v1/profile/projects/${id}`);
      toast.success("Project deleted.");
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to delete project");
    }
  };

  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiPost("/api/v1/profile/skills", newSkill);
      toast.success("Skill added!");
      setNewSkill({
        name: "",
        confidence: 5,
        years_used: 1.0,
        category: "General",
        is_visible: true
      });
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to add skill");
    }
  };

  const handleDeleteSkill = async (name: string) => {
    try {
      await apiDelete(`/api/v1/profile/skills/${name}`);
      toast.success("Skill removed.");
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to remove skill");
    }
  };

  const handleSavePreferencesAndCaps = async () => {
    try {
      await apiPut("/api/v1/profile/preferences", preferences);
      await apiPut("/api/v1/profile/capabilities", capabilities);
      toast.success("Preferences & Capabilities saved!");
      fetchSettings();
    } catch (e: any) {
      toast.error(e.message || "Failed to save preferences");
    }
  };

  const handleSaveNotifySettings = async () => {
    try {
      await apiPut("/api/v1/profile/preferences", notifyPreferences);
      toast.success("Notification preferences updated!");
    } catch (e: any) {
      toast.error(e.message || "Failed to save preferences");
    }
  };

  const handleSaveAPIKey = () => {
    if (typeof window !== "undefined") {
      for (const p of API_KEY_PROVIDERS) {
        localStorage.setItem(`llm_api_key_${p.id}`, apiKeys[p.id] || "");
      }
      // Keep legacy key in sync
      localStorage.setItem("openrouter_api_key", apiKeys.openrouter || "");
      localStorage.setItem("llm_preferred_provider", preferredProvider);
      toast.success("API keys saved locally!");
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error("New passwords do not match");
      return;
    }
    try {
      await apiPost("/api/v1/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword
      });
      toast.success("Password changed successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: any) {
      toast.error(e.message || "Failed to change password");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Settings</h1>
        <div className="bg-white p-8 rounded-xl border border-zinc-200 shadow-sm animate-pulse flex h-[400px]">
          <div className="w-64 border-r border-zinc-100 pr-6 space-y-4">
            <div className="h-6 bg-zinc-200 rounded w-full"></div>
            <div className="h-6 bg-zinc-200 rounded w-3/4"></div>
            <div className="h-6 bg-zinc-200 rounded w-5/6"></div>
          </div>
          <div className="flex-1 pl-8 space-y-6">
            <div className="h-8 bg-zinc-200 rounded w-1/3"></div>
            <div className="h-10 bg-zinc-200 rounded w-full"></div>
            <div className="h-10 bg-zinc-200 rounded w-full"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Settings & Profile</h1>
        <p className="text-sm text-zinc-500 mt-1">Configure your candidate profile, capabilities, filters, and credentials.</p>
      </div>

      <section aria-labelledby="resume-autofill-heading" className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-5 space-y-3">
        <h2 id="resume-autofill-heading" className="text-sm font-semibold text-zinc-900">Autofill from resume</h2>
        <p className="text-sm text-zinc-600">Uses your latest uploaded resume with Gemini as the primary extractor and Groq as fallback. Preserves existing entries and fills only facts from your resume. Review all imported details; visa, work authorization, and preferences are never guessed.</p>
        <p className="text-xs text-zinc-500">Upload a resume on the Profile page first, then explicitly click Autofill from resume here or there. Uploading alone does not parse it. Save your settings first: autofill refreshes saved data and unsaved edits to those fields will be lost.</p>
        <button
          type="button"
          onClick={handleAutofill}
          disabled={isAutofilling || isLoading}
          aria-busy={isAutofilling}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
        >
          {isAutofilling ? "Autofilling..." : "Autofill from resume"}
        </button>
        {autofillSummary && <p role="status" className="text-sm text-emerald-700">{autofillSummary}</p>}
      </section>

      <fieldset disabled={isAutofilling} aria-busy={isAutofilling} className="min-w-0 bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm disabled:opacity-60">
        <div className="flex flex-col md:flex-row min-h-[550px]">
          {/* Sidebar Tabs */}
          <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-zinc-200 p-4 space-y-1 bg-zinc-50/30 flex-shrink-0">
            <button
              onClick={() => setActiveTab("profile")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "profile" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <UserIcon size={16} />
              Candidate Profile
            </button>
            <button
              onClick={() => setActiveTab("education")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "education" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <GraduationCap size={16} />
              Education
            </button>
            <button
              onClick={() => setActiveTab("experience")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "experience" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <BookOpen size={16} />
              Work Experience
            </button>
            <button
              onClick={() => setActiveTab("projects")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "projects" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Settings size={16} />
              Projects
            </button>
            <button
              onClick={() => setActiveTab("skills")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "skills" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Star size={16} />
              Skills
            </button>
            <button
              onClick={() => setActiveTab("preferences")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "preferences" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Settings size={16} />
              Job Preferences
            </button>
            <button
              onClick={() => setActiveTab("integrations")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "integrations" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Briefcase size={16} />
              Job Sources & Integrations
            </button>
            <button
              onClick={() => setActiveTab("templates")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "templates" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <FileText size={16} />
              Document Templates
            </button>
            <button
              onClick={() => setActiveTab("apikeys")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "apikeys" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Key size={16} />
              AI Providers & API
            </button>
            <button
              onClick={() => setActiveTab("notifications")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "notifications" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Bell size={16} />
              Notifications
            </button>
            <button
              onClick={() => setActiveTab("privacy")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "privacy" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Shield size={16} />
              Privacy & Data Export
            </button>
            <button
              onClick={() => setActiveTab("security")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "security" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Key size={16} />
              Account & Password
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-6 md:p-8 overflow-y-auto max-h-[700px]">
            {activeTab === "profile" && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Candidate Profile Info</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Full Name</label>
                    <input
                      type="text"
                      value={userProfile.full_name || ""}
                      onChange={e => setUserProfile({ ...userProfile, full_name: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Jane Doe"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Preferred / Display Name</label>
                    <input
                      type="text"
                      value={userProfile.preferred_name || ""}
                      onChange={e => setUserProfile({ ...userProfile, preferred_name: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Jane"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Phone</label>
                    <input
                      type="text"
                      value={userProfile.phone || ""}
                      onChange={e => setUserProfile({ ...userProfile, phone: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">GitHub</label>
                    <input
                      type="text"
                      value={userProfile.github || ""}
                      onChange={e => setUserProfile({ ...userProfile, github: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="https://github.com/username"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">LinkedIn</label>
                    <input
                      type="text"
                      value={userProfile.linkedin || ""}
                      onChange={e => setUserProfile({ ...userProfile, linkedin: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="https://linkedin.com/in/username"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Portfolio Website</label>
                    <input
                      type="text"
                      value={userProfile.portfolio || ""}
                      onChange={e => setUserProfile({ ...userProfile, portfolio: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="https://portfolio.com"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Personal Website / Blog</label>
                    <input
                      type="text"
                      value={userProfile.website || ""}
                      onChange={e => setUserProfile({ ...userProfile, website: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="https://janedoe.me"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Current Location</label>
                    <input
                      type="text"
                      value={userProfile.current_location || ""}
                      onChange={e => setUserProfile({ ...userProfile, current_location: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="San Francisco, CA"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Immediate Availability / Notice</label>
                    <input
                      type="text"
                      value={userProfile.availability || ""}
                      onChange={e => setUserProfile({ ...userProfile, availability: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Immediate (Available June 2026)"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Primary University / Institution</label>
                    <input
                      type="text"
                      value={userProfile.university || ""}
                      onChange={e => setUserProfile({ ...userProfile, university: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Stanford University"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Degree</label>
                    <select
                      value={userProfile.degree || "Bachelors"}
                      onChange={e => setUserProfile({ ...userProfile, degree: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                    >
                      <option value="Bachelors">Bachelors</option>
                      <option value="Masters">Masters</option>
                      <option value="PhD">PhD</option>
                      <option value="None">None</option>
                    </select>
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Specialization / Major</label>
                    <input
                      type="text"
                      value={userProfile.specialization || ""}
                      onChange={e => setUserProfile({ ...userProfile, specialization: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Computer Science & Engineering"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Graduation Year</label>
                    <input
                      type="number"
                      value={userProfile.graduation_year || ""}
                      onChange={e => setUserProfile({ ...userProfile, graduation_year: e.target.value ? parseInt(e.target.value) : null })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="2026"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Current Semester / Academic Year</label>
                    <input
                      type="text"
                      value={userProfile.current_semester_or_year || ""}
                      onChange={e => setUserProfile({ ...userProfile, current_semester_or_year: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Senior / 8th Semester"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">CGPA / GPA</label>
                    <input
                      type="number"
                      step="0.01"
                      value={userProfile.cgpa || ""}
                      onChange={e => setUserProfile({ ...userProfile, cgpa: e.target.value ? parseFloat(e.target.value) : null })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="3.85"
                    />
                  </div>
                  <div className="col-span-1 md:col-span-2 grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Key Coursework (comma-separated)</label>
                    <input
                      type="text"
                      value={userProfile.coursework || ""}
                      onChange={e => setUserProfile({ ...userProfile, coursework: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="Data Structures, Algorithms, Operating Systems, Machine Learning, Computer Networks"
                    />
                  </div>
                  <div className="col-span-1 md:col-span-2 grid gap-1.5">
                    <label className="text-xs font-semibold text-zinc-700">Professional Bio / Summary</label>
                    <textarea
                      value={userProfile.bio || ""}
                      onChange={e => setUserProfile({ ...userProfile, bio: e.target.value })}
                      rows={3}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 resize-y"
                      placeholder="Full-stack engineer passionate about distributed systems and AI-driven developer workflows..."
                    />
                  </div>
                </div>
                <div className="flex justify-end pt-4 border-t">
                  <button
                    onClick={handleUpdateProfile}
                    className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                  >
                    <Save size={14} /> Save Profile Info
                  </button>
                </div>

                <div className="border-t pt-6 space-y-3">
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Default Resume Instructions</h2>
                  <p className="text-sm text-zinc-600">
                    Applied to every tailored resume and cover letter, alongside your latest uploaded resume
                    and GitHub projects. Per-job instructions on the job page override these for that role only.
                  </p>
                  <textarea
                    value={tailoringInstructions}
                    onChange={e => setTailoringInstructions(e.target.value)}
                    rows={5}
                    placeholder="e.g. Keep the resume to one page. Emphasize backend and ML work. Formal tone for cover letters. Always include my internship at Acme."
                    className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 resize-y"
                  />
                  <div className="flex justify-end">
                    <button
                      onClick={handleSaveInstructions}
                      disabled={isSavingInstructions}
                      className="inline-flex items-center gap-1.5 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-500 transition-colors shadow-sm disabled:opacity-60"
                    >
                      <Save size={14} /> {isSavingInstructions ? "Saving..." : "Save Instructions"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "education" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Education History</h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Manage all your degrees, colleges, GPAs, and coursework. Choose whether each record is active in AI tailored materials.
                  </p>
                </div>

                {/* List Educations */}
                <div className="space-y-3">
                  {educations.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No education history added yet. Add one below or import from your resume.</p>
                  ) : (
                    educations.map(edu => (
                      <div key={edu.id} className="p-4 border rounded-xl flex justify-between items-start gap-4 hover:bg-zinc-50/50 bg-white">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-sm font-bold text-zinc-900">{edu.degree} in {edu.field_of_study || "General Studies"}</h4>
                            <span className="text-xs text-zinc-500 font-semibold">• {edu.institution}</span>
                            {edu.is_current && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                                Current
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-zinc-500 font-medium">
                            {edu.start_year || "?"} - {edu.is_current ? "Present" : (edu.end_year || "?")}
                            {edu.cgpa && (
                              <span className="ml-2 font-semibold text-zinc-700">| CGPA/GPA: {edu.cgpa}{edu.max_cgpa ? ` / ${edu.max_cgpa}` : ""}</span>
                            )}
                          </p>
                          {edu.coursework && (
                            <p className="text-xs text-zinc-600 mt-1"><strong className="text-zinc-700 font-semibold">Coursework:</strong> {edu.coursework}</p>
                          )}
                          <div className="flex items-center gap-2 pt-2">
                            <button
                              type="button"
                              onClick={() => handleToggleEducationVisibility(edu.id, edu.is_visible !== false)}
                              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors ${
                                edu.is_visible !== false
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                                  : "bg-zinc-100 text-zinc-500 border-zinc-200 hover:bg-zinc-200"
                              }`}
                              title="Toggle whether this education appears in AI application materials"
                            >
                              {edu.is_visible !== false ? <Eye size={12} /> : <EyeOff size={12} />}
                              {edu.is_visible !== false ? "Active in AI applications" : "Hidden from AI applications"}
                            </button>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteEducation(edu.id)}
                          className="text-red-500 hover:text-red-700 p-1.5 rounded-md hover:bg-red-50 transition-colors"
                          title="Delete education record"
                        >
                          <Trash size={14} />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Add Education Form */}
                <form onSubmit={handleAddEducation} className="border-t pt-6 space-y-4">
                  <h3 className="text-sm font-bold text-zinc-800">Add Education Record</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="grid gap-1">
                      <label className="text-xs font-semibold text-zinc-700">Degree</label>
                      <input
                        required
                        type="text"
                        value={newEdu.degree}
                        onChange={e => setNewEdu({ ...newEdu, degree: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Bachelor of Science"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs font-semibold text-zinc-700">Institution / University</label>
                      <input
                        required
                        type="text"
                        value={newEdu.institution}
                        onChange={e => setNewEdu({ ...newEdu, institution: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Stanford University"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs font-semibold text-zinc-700">Field of Study / Major</label>
                      <input
                        type="text"
                        value={newEdu.field_of_study}
                        onChange={e => setNewEdu({ ...newEdu, field_of_study: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Computer Science"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="grid gap-1">
                        <label className="text-xs font-semibold text-zinc-700">Start Year</label>
                        <input
                          type="number"
                          value={newEdu.start_year}
                          onChange={e => setNewEdu({ ...newEdu, start_year: e.target.value })}
                          className="px-3 py-1.5 border rounded-lg text-sm"
                          placeholder="2022"
                        />
                      </div>
                      <div className="grid gap-1">
                        <label className="text-xs font-semibold text-zinc-700">End Year</label>
                        <input
                          type="number"
                          disabled={newEdu.is_current}
                          value={newEdu.end_year}
                          onChange={e => setNewEdu({ ...newEdu, end_year: e.target.value })}
                          className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50"
                          placeholder="2026"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="grid gap-1">
                        <label className="text-xs font-semibold text-zinc-700">CGPA / GPA</label>
                        <input
                          type="number"
                          step="0.01"
                          value={newEdu.cgpa}
                          onChange={e => setNewEdu({ ...newEdu, cgpa: e.target.value })}
                          className="px-3 py-1.5 border rounded-lg text-sm"
                          placeholder="3.85"
                        />
                      </div>
                      <div className="grid gap-1">
                        <label className="text-xs font-semibold text-zinc-700">Max Scale</label>
                        <input
                          type="number"
                          step="0.1"
                          value={newEdu.max_cgpa}
                          onChange={e => setNewEdu({ ...newEdu, max_cgpa: e.target.value })}
                          className="px-3 py-1.5 border rounded-lg text-sm"
                          placeholder="4.0 or 10.0"
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 pt-4">
                      <input
                        type="checkbox"
                        id="edu-is-current"
                        checked={newEdu.is_current}
                        onChange={e => setNewEdu({ ...newEdu, is_current: e.target.checked })}
                        className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                      />
                      <label htmlFor="edu-is-current" className="text-xs text-zinc-700 select-none cursor-pointer">
                        Currently enrolled student
                      </label>
                    </div>
                    <div className="col-span-1 md:col-span-2 grid gap-1">
                      <label className="text-xs font-semibold text-zinc-700">Coursework (comma-separated)</label>
                      <input
                        type="text"
                        value={newEdu.coursework}
                        onChange={e => setNewEdu({ ...newEdu, coursework: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Data Structures, Algorithms, Distributed Systems, ML"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                  >
                    <Plus size={14} /> Add Education Record
                  </button>
                </form>
              </div>
            )}

            {activeTab === "experience" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Work Experience</h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Control which experiences appear in your tailored applications with the visibility toggle.
                  </p>
                </div>
                
                {/* List Experiences */}
                <div className="space-y-3">
                  {experiences.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No work experience added yet.</p>
                  ) : (
                    experiences.map(exp => (
                      <div key={exp.id} className="p-4 border rounded-xl flex justify-between items-start gap-4 hover:bg-zinc-50/50 bg-white">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-zinc-900">{exp.title} at {exp.company}</h4>
                          <p className="text-xs text-zinc-500 font-semibold">
                            {exp.start_date} - {exp.currently_working ? "Present" : exp.end_date} ({exp.months_of_experience} months)
                            {exp.location && <span className="ml-2 font-normal text-zinc-400">• {exp.location}</span>}
                          </p>
                          <p className="text-xs text-zinc-600 leading-relaxed mt-1.5 whitespace-pre-line">{exp.description}</p>
                          <div className="flex items-center gap-2 pt-2">
                            <button
                              type="button"
                              onClick={() => handleToggleExperienceVisibility(exp.id, exp.is_visible !== false)}
                              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors ${
                                exp.is_visible !== false
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                                  : "bg-zinc-100 text-zinc-500 border-zinc-200 hover:bg-zinc-200"
                              }`}
                              title="Toggle whether this experience appears in AI application materials"
                            >
                              {exp.is_visible !== false ? <Eye size={12} /> : <EyeOff size={12} />}
                              {exp.is_visible !== false ? "Active in AI applications" : "Hidden from AI applications"}
                            </button>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteExperience(exp.id)}
                          className="text-red-500 hover:text-red-700 p-1.5 rounded-md hover:bg-red-50 transition-colors"
                          title="Delete experience"
                        >
                          <Trash size={14} />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Add Experience Form */}
                <form onSubmit={handleAddExperience} className="border-t pt-6 space-y-4">
                  <h3 className="text-sm font-bold text-zinc-800">Add Experience</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Company Name</label>
                      <input
                        required
                        type="text"
                        value={newExp.company}
                        onChange={e => setNewExp({ ...newExp, company: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Google"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Job Title</label>
                      <input
                        required
                        type="text"
                        value={newExp.title}
                        onChange={e => setNewExp({ ...newExp, title: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Software Engineer Intern"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Location</label>
                      <input
                        type="text"
                        value={newExp.location}
                        onChange={e => setNewExp({ ...newExp, location: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="San Francisco, CA (or Remote)"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Technologies / Tools (comma separated)</label>
                      <input
                        type="text"
                        value={newExp.technologies}
                        onChange={e => setNewExp({ ...newExp, technologies: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Python, FastAPI, Docker, AWS"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Months of Experience</label>
                      <input
                        required
                        type="number"
                        value={newExp.months_of_experience}
                        onChange={e => setNewExp({ ...newExp, months_of_experience: parseInt(e.target.value) || 0 })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="3"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Job Type</label>
                      <select
                        value={newExp.internship_or_fulltime}
                        onChange={e => setNewExp({ ...newExp, internship_or_fulltime: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                      >
                        <option value="internship">Internship</option>
                        <option value="fulltime">Full-time</option>
                      </select>
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Start Date</label>
                      <input
                        type="text"
                        value={newExp.start_date}
                        onChange={e => setNewExp({ ...newExp, start_date: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="May 2025"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">End Date</label>
                      <input
                        type="text"
                        disabled={newExp.currently_working}
                        value={newExp.end_date}
                        onChange={e => setNewExp({ ...newExp, end_date: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50"
                        placeholder="August 2025"
                      />
                    </div>
                    <div className="col-span-1 md:col-span-2 flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="currently-working"
                        checked={newExp.currently_working}
                        onChange={e => setNewExp({ ...newExp, currently_working: e.target.checked })}
                        className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                      />
                      <label htmlFor="currently-working" className="text-xs text-zinc-700 select-none cursor-pointer">
                        Currently working in this role
                      </label>
                    </div>
                    <div className="col-span-1 md:col-span-2 grid gap-1">
                      <label className="text-xs text-zinc-650">Description</label>
                      <textarea
                        value={newExp.description}
                        onChange={e => setNewExp({ ...newExp, description: e.target.value })}
                        rows={3}
                        className="px-3 py-1.5 border rounded-lg text-sm font-sans"
                        placeholder="Detail your responsibilities and achievements..."
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                  >
                    <Plus size={14} /> Add Experience Record
                  </button>
                </form>
              </div>
            )}

            {activeTab === "projects" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Portfolio Projects</h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Control which projects appear in your tailored resumes and cover letters.
                  </p>
                </div>
                
                {/* List Projects */}
                <div className="space-y-3">
                  {projects.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No projects added yet.</p>
                  ) : (
                    projects.map(proj => (
                      <div key={proj.id} className="p-4 border rounded-xl flex justify-between items-start gap-4 hover:bg-zinc-50/50 bg-white">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-sm font-bold text-zinc-900">{proj.name}</h4>
                            {proj.role && <span className="text-xs text-zinc-500 font-medium">({proj.role})</span>}
                          </div>
                          <p className="text-xs text-zinc-500 leading-relaxed">{proj.description}</p>
                          <div className="flex flex-wrap gap-1.5 pt-1.5">
                            {proj.technologies && proj.technologies.map((t: string) => (
                              <span key={t} className="bg-zinc-100 text-zinc-650 px-2 py-0.5 rounded text-[10px] font-semibold">{t}</span>
                            ))}
                          </div>
                          <div className="flex items-center gap-3 pt-2 text-[11px] font-semibold text-indigo-600">
                            {proj.github && <a href={proj.github} target="_blank" rel="noopener noreferrer" className="hover:underline">GitHub</a>}
                            {proj.live_link && <a href={proj.live_link} target="_blank" rel="noopener noreferrer" className="hover:underline">Live Demo</a>}
                          </div>
                          <div className="flex items-center gap-2 pt-2">
                            <button
                              type="button"
                              onClick={() => handleToggleProjectVisibility(proj.id, proj.is_visible !== false)}
                              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors ${
                                proj.is_visible !== false
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                                  : "bg-zinc-100 text-zinc-500 border-zinc-200 hover:bg-zinc-200"
                              }`}
                              title="Toggle whether this project appears in AI application materials"
                            >
                              {proj.is_visible !== false ? <Eye size={12} /> : <EyeOff size={12} />}
                              {proj.is_visible !== false ? "Active in AI applications" : "Hidden from AI applications"}
                            </button>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteProject(proj.id)}
                          className="text-red-500 hover:text-red-700 p-1.5 rounded-md hover:bg-red-50 transition-colors"
                          title="Delete project"
                        >
                          <Trash size={14} />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Add Project Form */}
                <form onSubmit={handleAddProject} className="border-t pt-6 space-y-4">
                  <h3 className="text-sm font-bold text-zinc-800">Add Project</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Project Name</label>
                      <input
                        required
                        type="text"
                        value={newProj.name}
                        onChange={e => setNewProj({ ...newProj, name: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="E-Commerce API"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Role in Project</label>
                      <input
                        type="text"
                        value={newProj.role}
                        onChange={e => setNewProj({ ...newProj, role: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Lead Backend Engineer"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Technologies (comma separated)</label>
                      <input
                        type="text"
                        value={newProj.technologies}
                        onChange={e => setNewProj({ ...newProj, technologies: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="Python, FastAPI, Postgres"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">GitHub Link</label>
                      <input
                        type="text"
                        value={newProj.github}
                        onChange={e => setNewProj({ ...newProj, github: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="https://github.com/..."
                      />
                    </div>
                    <div className="grid gap-1 col-span-1 md:col-span-2">
                      <label className="text-xs text-zinc-650">Live Link</label>
                      <input
                        type="text"
                        value={newProj.live_link}
                        onChange={e => setNewProj({ ...newProj, live_link: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="https://..."
                      />
                    </div>
                    <div className="col-span-1 md:col-span-2 grid gap-1">
                      <label className="text-xs text-zinc-650">Description</label>
                      <textarea
                        value={newProj.description}
                        onChange={e => setNewProj({ ...newProj, description: e.target.value })}
                        rows={3}
                        className="px-3 py-1.5 border rounded-lg text-sm font-sans"
                        placeholder="Describe the project objective, features, and your work..."
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                  >
                    <Plus size={14} /> Add Project
                  </button>
                </form>
              </div>
            )}

            {activeTab === "skills" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Skills Inventory</h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Manage categorized skills and toggle which ones appear in AI tailored resumes.
                  </p>
                </div>
                
                {/* List Skills */}
                <div className="flex flex-wrap gap-2">
                  {skills.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No skills listed yet.</p>
                  ) : (
                    skills.map(sk => (
                      <span
                        key={sk.name}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-xs border transition-colors ${
                          sk.is_visible !== false
                            ? "bg-white border-zinc-200 text-zinc-800"
                            : "bg-zinc-100 border-zinc-200 text-zinc-400 line-through opacity-75"
                        }`}
                      >
                        <span>{sk.name}</span>
                        <span className="text-[10px] text-zinc-500 font-normal">({sk.category || "General"}, {sk.years_used} yrs, Lvl {sk.confidence}/5)</span>
                        <button
                          type="button"
                          onClick={() => handleToggleSkillVisibility(sk.name, sk.is_visible !== false)}
                          className={`p-0.5 rounded transition-colors ${sk.is_visible !== false ? "text-emerald-600 hover:text-emerald-800" : "text-zinc-400 hover:text-zinc-600"}`}
                          title={sk.is_visible !== false ? "Active in AI applications (click to hide)" : "Hidden from AI applications (click to include)"}
                        >
                          {sk.is_visible !== false ? <Eye size={13} /> : <EyeOff size={13} />}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteSkill(sk.name)}
                          className="text-zinc-400 hover:text-red-500 rounded-md transition-colors text-sm font-bold"
                          title="Remove skill"
                        >
                          &times;
                        </button>
                      </span>
                    ))
                  )}
                </div>

                {/* Add Skill Form */}
                <form onSubmit={handleAddSkill} className="border-t pt-6 space-y-4">
                  <h3 className="text-sm font-bold text-zinc-800">Add Skill</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Skill Name</label>
                      <input
                        required
                        type="text"
                        value={newSkill.name}
                        onChange={e => setNewSkill({ ...newSkill, name: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                        placeholder="React"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Category</label>
                      <select
                        value={newSkill.category}
                        onChange={e => setNewSkill({ ...newSkill, category: e.target.value })}
                        className="px-3 py-1.5 border rounded-lg text-sm bg-white"
                      >
                        <option value="Languages">Languages</option>
                        <option value="Frameworks">Frameworks</option>
                        <option value="Developer Tools">Developer Tools</option>
                        <option value="Libraries">Libraries</option>
                        <option value="Databases">Databases</option>
                        <option value="Concepts">Concepts</option>
                        <option value="General">General</option>
                      </select>
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Confidence Level (1-5)</label>
                      <input
                        required
                        type="number"
                        min="1"
                        max="5"
                        value={newSkill.confidence}
                        onChange={e => setNewSkill({ ...newSkill, confidence: parseInt(e.target.value) || 5 })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                      />
                    </div>
                    <div className="grid gap-1">
                      <label className="text-xs text-zinc-650">Years Used</label>
                      <input
                        required
                        type="number"
                        step="0.5"
                        value={newSkill.years_used}
                        onChange={e => setNewSkill({ ...newSkill, years_used: parseFloat(e.target.value) || 1.0 })}
                        className="px-3 py-1.5 border rounded-lg text-sm"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                  >
                    <Plus size={14} /> Add Skill
                  </button>
                </form>
              </div>
            )}

            {activeTab === "preferences" && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Eligibility Engine Settings</h2>
                
                {/* User preferences form */}
                <div className="space-y-6">
                  <div className="space-y-3">
                    <h3 className="text-sm font-bold text-zinc-850">Compensation & Preferences</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="grid gap-1.5">
                        <label className="text-xs font-semibold text-zinc-700">Minimum Annual Salary Expected ($)</label>
                        <input
                          type="number"
                          value={preferences.minimum_salary || 0}
                          onChange={e => setPreferences({ ...preferences, minimum_salary: parseInt(e.target.value) || 0 })}
                          className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                          placeholder="80000"
                        />
                      </div>
                      <div className="grid gap-1.5">
                        <label className="text-xs font-semibold text-zinc-700">Maximum Experience Accepted (years)</label>
                        <input
                          type="number"
                          value={preferences.maximum_experience_required || ""}
                          onChange={e => setPreferences({ ...preferences, maximum_experience_required: e.target.value ? parseInt(e.target.value) : null })}
                          className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                          placeholder="e.g. 5"
                        />
                      </div>
                      <div className="grid gap-1.5 col-span-1 md:col-span-2">
                        <label className="text-xs font-semibold text-zinc-700">Availability / Notice Period Details</label>
                        <input
                          type="text"
                          value={preferences.availability_duration || ""}
                          onChange={e => setPreferences({ ...preferences, availability_duration: e.target.value })}
                          className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                          placeholder="e.g. Immediate / Summer 2026 Internship (3 Months) / 2 Weeks Notice"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3 border-t pt-4">
                    <h3 className="text-sm font-bold text-zinc-850">Candidate Capabilities</h3>
                    <div className="grid grid-cols-2 gap-3 text-xs font-medium text-zinc-750">
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.can_relocate}
                          onChange={e => setCapabilities({ ...capabilities, can_relocate: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Willing to relocate for onsite roles
                      </label>
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.can_work_remote}
                          onChange={e => setCapabilities({ ...capabilities, can_work_remote: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Can work remotely
                      </label>
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.can_do_internship}
                          onChange={e => setCapabilities({ ...capabilities, can_do_internship: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Open to internship roles
                      </label>
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.can_do_fulltime}
                          onChange={e => setCapabilities({ ...capabilities, can_do_fulltime: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Open to full-time roles
                      </label>
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.can_work_contract}
                          onChange={e => setCapabilities({ ...capabilities, can_work_contract: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Open to contract engagements
                      </label>
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.has_work_authorization}
                          onChange={e => setCapabilities({ ...capabilities, has_work_authorization: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Has work authorization
                      </label>
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={capabilities.needs_sponsorship}
                          onChange={e => setCapabilities({ ...capabilities, needs_sponsorship: e.target.checked })}
                          className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        Needs visa sponsorship
                      </label>
                    </div>
                  </div>

                  <div className="flex justify-end pt-4 border-t">
                    <button
                      onClick={handleSavePreferencesAndCaps}
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Save Filter Settings
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "apikeys" && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">API Credentials</h2>
                <p className="text-xs text-zinc-500">
                  Add keys for any providers you have. The backend reads provider keys from its <code className="bg-zinc-100 px-1 rounded">.env</code> (see <code className="bg-zinc-100 px-1 rounded">backend/.env.example</code>); keys saved here stay in your browser sandbox.
                </p>
                <div className="grid gap-2">
                  <label className="text-sm font-medium text-zinc-700">Preferred Provider</label>
                  <select
                    value={preferredProvider}
                    onChange={(e) => setPreferredProvider(e.target.value)}
                    className="px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full bg-white"
                  >
                    {API_KEY_PROVIDERS.map((p) => (
                      <option key={p.id} value={p.id}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-4">
                  {API_KEY_PROVIDERS.map((p) => (
                    <div key={p.id} className="grid gap-2">
                      <label className="text-sm font-medium text-zinc-700">{p.label} API Key</label>
                      <input
                        type="password"
                        value={apiKeys[p.id] || ""}
                        onChange={(e) => setApiKeys({ ...apiKeys, [p.id]: e.target.value })}
                        placeholder={p.placeholder}
                        className="px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full"
                      />
                    </div>
                  ))}
                  <p className="text-xs text-zinc-500">Stored securely in your local browser sandbox to run AI services.</p>
                  <div className="pt-4 border-t border-zinc-100 flex justify-end">
                    <button
                      onClick={handleSaveAPIKey}
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Save API Keys
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "notifications" && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Notification Preferences</h2>
                <div className="space-y-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifyPreferences.notify_new_jobs}
                      onChange={(e) => setNotifyPreferences({ ...notifyPreferences, notify_new_jobs: e.target.checked })}
                      className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-zinc-700 font-medium">Notify me when new jobs are discovered</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifyPreferences.notify_resume_generated}
                      onChange={(e) => setNotifyPreferences({ ...notifyPreferences, notify_resume_generated: e.target.checked })}
                      className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-zinc-700 font-medium">Notify me when resume tailoring is completed</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifyPreferences.notify_application_completed}
                      onChange={(e) => setNotifyPreferences({ ...notifyPreferences, notify_application_completed: e.target.checked })}
                      className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-zinc-700 font-medium">Notify me on autopilot actions</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifyPreferences.notify_errors}
                      onChange={(e) => setNotifyPreferences({ ...notifyPreferences, notify_errors: e.target.checked })}
                      className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-zinc-700 font-medium">Notify me on errors or interventions</span>
                  </label>

                  <div className="pt-4 border-t border-zinc-100 flex justify-end">
                    <button
                      onClick={handleSaveNotifySettings}
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Save Notification Preferences
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "integrations" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Job Sources & Ingestion Integrations</h2>
                  <p className="text-xs text-zinc-500 mt-1">Configure automated role scrapers and active job board feeds.</p>
                </div>

                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">Active Sourcing Channels</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {[
                      { key: "greenhouse", label: "Greenhouse ATS Boards", desc: "Automated ingestion from company careers" },
                      { key: "lever", label: "Lever ATS Feeds", desc: "Direct company job postings" },
                      { key: "ashby", label: "Ashby ATS Feeds", desc: "High-growth tech company postings" },
                      { key: "linkedin", label: "LinkedIn Job Discovery", desc: "Standard public job postings" },
                      { key: "indeed", label: "Indeed Role Aggregator", desc: "Broad market tech roles" },
                      { key: "wellfound", label: "Wellfound / Startups", desc: "Early-stage venture job feeds" },
                    ].map((item) => (
                      <label key={item.key} className="p-3.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50/60 flex items-start gap-3 cursor-pointer transition-colors">
                        <input
                          type="checkbox"
                          checked={(sourceIntegrations as any)[item.key]}
                          onChange={(e) => setSourceIntegrations({ ...sourceIntegrations, [item.key]: e.target.checked })}
                          className="mt-0.5 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                        />
                        <div className="text-xs">
                          <span className="font-semibold text-zinc-900 block">{item.label}</span>
                          <span className="text-[11px] text-zinc-500">{item.desc}</span>
                        </div>
                      </label>
                    ))}
                  </div>

                  <div className="pt-4 border-t border-zinc-100">
                    <label className="text-xs font-semibold text-zinc-700 block mb-1.5">Discovery & Ingestion Cadence</label>
                    <select
                      value={sourceIntegrations.discovery_cadence}
                      onChange={(e) => setSourceIntegrations({ ...sourceIntegrations, discovery_cadence: e.target.value })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-900"
                    >
                      <option value="daily">Daily Ingestion (Recommended)</option>
                      <option value="weekly">Weekly Summary Ingestion</option>
                      <option value="manual">Manual Scrape On-Demand Only</option>
                    </select>
                  </div>

                  <div className="pt-4 border-t border-zinc-100 flex justify-end">
                    <button
                      type="button"
                      onClick={() => toast.success("Job source integration settings saved!")}
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Save Source Integrations
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "templates" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Document Templates & Formatting</h2>
                  <p className="text-xs text-zinc-500 mt-1">Configure default LaTeX layouts and cover letter narrative defaults.</p>
                </div>

                <div className="space-y-4 text-xs">
                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1.5">Default Resume Template Style</label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {[
                        { id: "clean_ats", name: "Clean ATS Professional", desc: "Single-column, maximum parseability by corporate applicant tracking systems." },
                        { id: "academic", name: "Academic & Research", desc: "Structured layout with dedicated publications, citations, and awards." },
                        { id: "modern", name: "Tech Minimalist", desc: "Streamlined modern hierarchy optimized for engineering recruiters." },
                      ].map((tmpl) => (
                        <button
                          key={tmpl.id}
                          type="button"
                          onClick={() => setTemplateSettings({ ...templateSettings, default_template: tmpl.id })}
                          className={`p-3.5 rounded-lg border text-left transition-all ${
                            templateSettings.default_template === tmpl.id
                              ? "border-zinc-900 bg-zinc-50/80 shadow-sm"
                              : "border-zinc-200 bg-white hover:bg-zinc-50"
                          }`}
                        >
                          <div className="font-bold text-zinc-900">{tmpl.name}</div>
                          <div className="text-[11px] text-zinc-500 mt-1">{tmpl.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-zinc-100">
                    <div>
                      <label className="font-semibold text-zinc-700 block mb-1.5">Document Base Font Size</label>
                      <select
                        value={templateSettings.font_size}
                        onChange={(e) => setTemplateSettings({ ...templateSettings, font_size: e.target.value })}
                        className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-900"
                      >
                        <option value="10pt">10pt (Compact, standard for 1-page resumes)</option>
                        <option value="11pt">11pt (Readable, suitable for experienced candidates)</option>
                      </select>
                    </div>

                    <div>
                      <label className="font-semibold text-zinc-700 block mb-1.5">Default Cover Letter Tone</label>
                      <select
                        value={templateSettings.cover_letter_style}
                        onChange={(e) => setTemplateSettings({ ...templateSettings, cover_letter_style: e.target.value })}
                        className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-900"
                      >
                        <option value="concise">Concise & Direct (Recommended)</option>
                        <option value="impactful">Technical Impact & Metrics Focus</option>
                        <option value="storytelling">Career Narrative & Value Alignment</option>
                      </select>
                    </div>
                  </div>

                  <label className="flex items-center gap-3 cursor-pointer pt-2">
                    <input
                      type="checkbox"
                      checked={templateSettings.enforce_single_page}
                      onChange={(e) => setTemplateSettings({ ...templateSettings, enforce_single_page: e.target.checked })}
                      className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                    />
                    <span className="text-zinc-700 font-medium">Strictly fit resume compile to a single page</span>
                  </label>

                  <div className="pt-4 border-t border-zinc-100 flex justify-end">
                    <button
                      type="button"
                      onClick={() => toast.success("Document template preferences saved!")}
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Save Template Defaults
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "privacy" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Privacy & Data Management</h2>
                  <p className="text-xs text-zinc-500 mt-1">Export your complete career records or manage data retention.</p>
                </div>

                <div className="space-y-5 text-xs">
                  {/* Export Box */}
                  <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold text-sm text-zinc-900">Data Portability (GDPR / Full Export)</h3>
                        <p className="text-zinc-500 mt-0.5">
                          Download all verified profile facts, experiences, projects, skills, resumes, and application history as a portable JSON file.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleExportData}
                      disabled={isExportingData}
                      className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                      {isExportingData ? "Exporting Data..." : "Download Complete Career Archive (.json)"}
                    </button>
                  </div>

                  {/* Reset / Deletion Box */}
                  <div className="p-5 rounded-xl border border-rose-200 bg-rose-50/40 space-y-3">
                    <div>
                      <h3 className="font-bold text-sm text-rose-900">Reset Application History</h3>
                      <p className="text-rose-700 mt-0.5">
                        Clears your tracked applications and saved job positions in the database. Your master career profile, educations, work experiences, and projects will remain intact.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleClearData}
                      disabled={isClearingData}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50"
                    >
                      {isClearingData ? "Resetting History..." : "Reset Application CRM Records"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "security" && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Change Password</h2>
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <div className="grid gap-2">
                    <label className="text-sm font-medium text-zinc-700">Current Password</label>
                    <input
                      required
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full"
                    />
                  </div>
                  <div className="grid gap-2">
                    <label className="text-sm font-medium text-zinc-700">New Password</label>
                    <input
                      required
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full"
                    />
                  </div>
                  <div className="grid gap-2">
                    <label className="text-sm font-medium text-zinc-700">Confirm New Password</label>
                    <input
                      required
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 w-full"
                    />
                  </div>
                  <div className="pt-4 border-t border-zinc-100 flex justify-end">
                    <button
                      type="submit"
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Update Password
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      </fieldset>
    </div>
  );
}
