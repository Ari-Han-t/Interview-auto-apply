"use client";

import { useEffect, useState } from "react";
import { User as UserIcon, Bell, Shield, Key, Save, Plus, Trash, BookOpen, Star, Settings } from "lucide-react";
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
    email: "",
    phone: "",
    github: "",
    linkedin: "",
    portfolio: "",
    current_location: "",
    preferred_locations: [],
    work_authorization: "",
    visa_required: false,
    willing_to_relocate: true,
    remote_preference: "any",
    graduation_year: null,
    degree: "Bachelors",
    cgpa: null,
    university: ""
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
    description: ""
  });

  // Projects
  const [projects, setProjects] = useState<any[]>([]);
  const [newProj, setNewProj] = useState({
    name: "",
    description: "",
    github: "",
    live_link: "",
    technologies: ""
  });

  // Skills
  const [skills, setSkills] = useState<any[]>([]);
  const [newSkill, setNewSkill] = useState({
    name: "",
    confidence: 5,
    years_used: 1.0
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
    maximum_daily_applications: 5
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

  const fetchSettings = async () => {
    try {
      const data = await apiFetch("/api/v1/profile/");
      if (data.profile) {
        setUserProfile(data.profile);
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

  const handleAddExperience = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiPost("/api/v1/profile/experiences", newExp);
      toast.success("Experience added!");
      setNewExp({
        company: "",
        title: "",
        internship_or_fulltime: "fulltime",
        start_date: "",
        end_date: "",
        currently_working: false,
        months_of_experience: 0,
        description: ""
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
        technologies: newProj.technologies.split(",").map(t => t.trim()).filter(Boolean)
      };
      await apiPost("/api/v1/profile/projects", payload);
      toast.success("Project added!");
      setNewProj({
        name: "",
        description: "",
        github: "",
        live_link: "",
        technologies: ""
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
        years_used: 1.0
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
              Eligibility Filters
            </button>
            <button
              onClick={() => setActiveTab("apikeys")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "apikeys" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Key size={16} />
              API Credentials
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
              onClick={() => setActiveTab("security")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === "security" ? "bg-indigo-50 text-indigo-700 font-bold" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <Shield size={16} />
              Security
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
                    <label className="text-xs font-semibold text-zinc-700">University</label>
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
                    <label className="text-xs font-semibold text-zinc-700">CGPA</label>
                    <input
                      type="number"
                      step="0.01"
                      value={userProfile.cgpa || ""}
                      onChange={e => setUserProfile({ ...userProfile, cgpa: e.target.value ? parseFloat(e.target.value) : null })}
                      className="px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                      placeholder="3.8"
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

            {activeTab === "experience" && (
              <div className="space-y-6">
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Work Experience</h2>
                
                {/* List Experiences */}
                <div className="space-y-3">
                  {experiences.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No work experience added yet.</p>
                  ) : (
                    experiences.map(exp => (
                      <div key={exp.id} className="p-4 border rounded-xl flex justify-between items-start gap-4 hover:bg-zinc-50/50">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-zinc-850">{exp.title} at {exp.company}</h4>
                          <p className="text-xs text-zinc-500 font-semibold">{exp.start_date} - {exp.currently_working ? "Present" : exp.end_date} ({exp.months_of_experience} months)</p>
                          <p className="text-xs text-zinc-600 leading-relaxed mt-1.5 whitespace-pre-line">{exp.description}</p>
                        </div>
                        <button
                          onClick={() => handleDeleteExperience(exp.id)}
                          className="text-red-500 hover:text-red-700 p-1 rounded-md hover:bg-red-50 transition-colors"
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
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Portfolio Projects</h2>
                
                {/* List Projects */}
                <div className="space-y-3">
                  {projects.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No projects added yet.</p>
                  ) : (
                    projects.map(proj => (
                      <div key={proj.id} className="p-4 border rounded-xl flex justify-between items-start gap-4 hover:bg-zinc-50/50">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-zinc-855">{proj.name}</h4>
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
                        </div>
                        <button
                          onClick={() => handleDeleteProject(proj.id)}
                          className="text-red-500 hover:text-red-700 p-1 rounded-md hover:bg-red-50 transition-colors"
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
                    <div className="grid gap-1">
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
                <h2 className="text-lg font-bold text-zinc-900 border-b pb-2">Skills Inventory</h2>
                
                {/* List Skills */}
                <div className="flex flex-wrap gap-2">
                  {skills.length === 0 ? (
                    <p className="text-sm text-zinc-400 italic">No skills listed yet.</p>
                  ) : (
                    skills.map(sk => (
                      <span key={sk.name} className="inline-flex items-center gap-1.5 bg-zinc-50 border border-zinc-200 text-zinc-700 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm">
                        {sk.name} ({sk.years_used} yrs, Level {sk.confidence}/5)
                        <button
                          type="button"
                          onClick={() => handleDeleteSkill(sk.name)}
                          className="text-zinc-400 hover:text-red-500 rounded-md transition-colors"
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
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
