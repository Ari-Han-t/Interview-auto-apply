"use client";

import { useState, useEffect } from "react";
import { apiFetch, apiPost, API_BASE } from "@/lib/api";
import { toast } from "react-hot-toast";
import {
  Search,
  ExternalLink,
  ChevronDown,
  Clock,
  Eye,
  CheckCircle2,
  Calendar,
  Download,
  Kanban as KanbanIcon,
  Table as TableIcon,
  FileText,
  Check,
  ShieldCheck,
  AlertCircle,
  Plus,
  GraduationCap,
  Building2,
  X,
  Bell,
  Award,
  Filter,
  ArrowUpDown,
  Copy,
  Trash2,
  Send,
  FileCheck,
} from "lucide-react";
import Link from "next/link";

const CANONICAL_STATUSES = [
  { value: "Discovered", label: "Discovered", color: "bg-slate-100 text-slate-700 border-slate-200" },
  { value: "Saved", label: "Saved", color: "bg-blue-100 text-blue-700 border-blue-200" },
  { value: "Shortlisted", label: "Shortlisted", color: "bg-indigo-100 text-indigo-700 border-indigo-200" },
  { value: "Preparing", label: "Preparing", color: "bg-amber-100 text-amber-700 border-amber-200" },
  { value: "Ready to Apply", label: "Ready to Apply", color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  { value: "Applied", label: "Applied", color: "bg-teal-100 text-teal-800 border-teal-200" },
  { value: "Assessment Received", label: "Assessment Received", color: "bg-orange-100 text-orange-700 border-orange-200" },
  { value: "Interview Scheduled", label: "Interview Scheduled", color: "bg-purple-100 text-purple-700 border-purple-200" },
  { value: "Interview Completed", label: "Interview Completed", color: "bg-violet-100 text-violet-700 border-violet-200" },
  { value: "Offer Received", label: "Offer Received", color: "bg-green-100 text-green-800 border-green-300" },
  { value: "Rejected", label: "Rejected", color: "bg-rose-100 text-rose-700 border-rose-200" },
  { value: "Withdrawn", label: "Withdrawn", color: "bg-zinc-100 text-zinc-600 border-zinc-200" },
  { value: "Position Closed", label: "Position Closed", color: "bg-gray-100 text-gray-600 border-gray-200" },
];

function getStatusBadge(status: string) {
  const match = CANONICAL_STATUSES.find(
    (s) => s.value.toLowerCase() === (status || "").toLowerCase()
  );
  if (match) return match;
  // Handle older raw statuses
  if (status === "generating") return { value: "Preparing", label: "Preparing", color: "bg-amber-100 text-amber-700 border-amber-200" };
  if (status === "generated") return { value: "Ready to Apply", label: "Ready to Apply", color: "bg-emerald-100 text-emerald-700 border-emerald-200" };
  if (status === "applied") return { value: "Applied", label: "Applied", color: "bg-teal-100 text-teal-800 border-teal-200" };
  if (status === "interview") return { value: "Interview Scheduled", label: "Interview", color: "bg-purple-100 text-purple-700 border-purple-200" };
  if (status === "oa") return { value: "Assessment Received", label: "Assessment", color: "bg-orange-100 text-orange-700 border-orange-200" };
  if (status === "offer") return { value: "Offer Received", label: "Offer", color: "bg-green-100 text-green-800 border-green-300" };
  if (status === "rejected") return { value: "Rejected", label: "Rejected", color: "bg-rose-100 text-rose-700 border-rose-200" };
  return { value: status, label: status, color: "bg-zinc-100 text-zinc-600 border-zinc-200" };
}

interface FollowUpItem {
  id?: string;
  title: string;
  due_date?: string | null;
  completed: boolean;
  notes?: string;
}

interface ReminderItem {
  id?: string;
  title: string;
  remind_at: string;
  reminder_type: string;
  notes?: string;
}

interface AppData {
  id: number;
  job_id: number;
  status: string;
  source?: string;
  applied_at?: string | null;
  submission_confirmed?: boolean;
  resume_version_id?: number | null;
  cover_letter_id?: number | null;
  submitted_resume_snapshot?: string | null;
  submitted_cover_letter_snapshot?: string | null;
  match_report?: any;
  assessment_deadline?: string | null;
  assessment_notes?: string | null;
  interview_date?: string | null;
  interview_round?: string | null;
  interview_notes?: string | null;
  notes?: string | null;
  follow_ups?: FollowUpItem[];
  reminders?: ReminderItem[];
  outcome?: string | null;
  outcome_notes?: string | null;
  offer_compensation?: string | null;
  resume_version_url?: string | null;
  cover_letter_url?: string | null;
  next_action?: string | null;
  user_instructions?: string | null;
  company: string;
  role: string;
  job_url: string;
  application_url?: string;
  job_location?: string;
  job_salary?: string;
  employment_type?: string;
  created_at?: string;
  updated_at?: string;
}

interface HistoryItem {
  id: number;
  status: string;
  notes: string;
  created_at: string;
}

interface SubmittedMaterialsData {
  application_id: number;
  company: string;
  role: string;
  submission_confirmed: boolean;
  applied_at: string | null;
  source: string;
  submitted_resume_snapshot: string | null;
  submitted_cover_letter_snapshot: string | null;
  has_frozen_resume: boolean;
  has_frozen_cover_letter: boolean;
  is_snapshot_immutable: boolean;
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<AppData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"kanban" | "table">("kanban");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [stageFilter, setStageFilter] = useState("all");
  const [sortBy, setSortBy] = useState<string>("updated_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // CRM Detail Drawer State
  const [selectedApp, setSelectedApp] = useState<AppData | null>(null);
  const [activeDrawerTab, setActiveDrawerTab] = useState<
    "overview" | "assisted_apply" | "timeline" | "schedule" | "followups" | "frozen_materials" | "outcome"
  >("overview");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [submittedMaterials, setSubmittedMaterials] = useState<SubmittedMaterialsData | null>(null);
  const [isLoadingMaterials, setIsLoadingMaterials] = useState(false);

  // Assisted Application Details State
  const [candidateProfile, setCandidateProfile] = useState<any | null>(null);
  const [coverLetterText, setCoverLetterText] = useState<string>("");
  const [isLoadingCoverLetter, setIsLoadingCoverLetter] = useState<boolean>(false);

  // Editable Drawer Form States
  const [drawerStatus, setDrawerStatus] = useState("");
  const [drawerNotes, setDrawerNotes] = useState("");
  const [drawerSource, setDrawerSource] = useState("");
  const [drawerInterviewDate, setDrawerInterviewDate] = useState("");
  const [drawerInterviewRound, setDrawerInterviewRound] = useState("");
  const [drawerInterviewNotes, setDrawerInterviewNotes] = useState("");
  const [drawerAssessmentDeadline, setDrawerAssessmentDeadline] = useState("");
  const [drawerAssessmentNotes, setDrawerAssessmentNotes] = useState("");
  const [drawerOutcome, setDrawerOutcome] = useState("");
  const [drawerOutcomeNotes, setDrawerOutcomeNotes] = useState("");
  const [drawerCompensation, setDrawerCompensation] = useState("");
  const [drawerNextAction, setDrawerNextAction] = useState("");
  const [newFollowUpTitle, setNewFollowUpTitle] = useState("");
  const [newFollowUpDate, setNewFollowUpDate] = useState("");
  const [isSavingCrm, setIsSavingCrm] = useState(false);

  // Reminder Form States
  const [newReminderTitle, setNewReminderTitle] = useState("");
  const [newReminderDate, setNewReminderDate] = useState("");
  const [newReminderType, setNewReminderType] = useState("interview");
  const [newReminderNotes, setNewReminderNotes] = useState("");
  const [isAddingReminder, setIsAddingReminder] = useState(false);

  // Confirmation Modal State
  const [confirmModalApp, setConfirmModalApp] = useState<AppData | null>(null);
  const [confirmSource, setConfirmSource] = useState("Company Portal");
  const [confirmNotes, setConfirmNotes] = useState("");
  const [isConfirming, setIsConfirming] = useState(false);

  useEffect(() => {
    fetchApps();
  }, []);

  const fetchApps = async () => {
    try {
      const data = await apiFetch<AppData[]>("/api/v1/applications/");
      setApps(data);
    } catch (err: any) {
      if (err.message !== "Unauthorized") {
        toast.error("Failed to load applications");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHistory = async (appId: number) => {
    setIsLoadingHistory(true);
    try {
      const data = await apiFetch<HistoryItem[]>(`/api/v1/applications/${appId}/history`);
      setHistory(data);
    } catch {
      // silent or mild toast
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const fetchSubmittedMaterials = async (appId: number) => {
    setIsLoadingMaterials(true);
    try {
      const data = await apiFetch<SubmittedMaterialsData>(
        `/api/v1/applications/${appId}/submitted-materials`
      );
      setSubmittedMaterials(data);
    } catch {
      setSubmittedMaterials(null);
    } finally {
      setIsLoadingMaterials(false);
    }
  };

  const handleOpenDrawer = (app: AppData, initialTab: typeof activeDrawerTab = "overview") => {
    setSelectedApp(app);
    setActiveDrawerTab(initialTab);
    setDrawerStatus(app.status || "Discovered");
    setDrawerNotes(app.notes || "");
    setDrawerSource(app.source || "Company Portal");
    setDrawerInterviewDate(app.interview_date ? app.interview_date.substring(0, 16) : "");
    setDrawerInterviewRound(app.interview_round || "");
    setDrawerInterviewNotes(app.interview_notes || "");
    setDrawerAssessmentDeadline(app.assessment_deadline ? app.assessment_deadline.substring(0, 16) : "");
    setDrawerAssessmentNotes(app.assessment_notes || "");
    setDrawerOutcome(app.outcome || "");
    setDrawerOutcomeNotes(app.outcome_notes || "");
    setDrawerCompensation(app.offer_compensation || "");
    setDrawerNextAction(app.next_action || "");
    fetchHistory(app.id);
    fetchSubmittedMaterials(app.id);
    fetchCandidateProfile();
    fetchCoverLetterText(app.job_id);
  };

  const handleSaveCrmDetails = async () => {
    if (!selectedApp) return;
    setIsSavingCrm(true);
    try {
      const updated = await apiFetch<AppData>(`/api/v1/applications/${selectedApp.id}/crm`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: drawerStatus,
          notes: drawerNotes,
          source: drawerSource,
          interview_date: drawerInterviewDate ? new Date(drawerInterviewDate).toISOString() : null,
          interview_round: drawerInterviewRound || null,
          interview_notes: drawerInterviewNotes || null,
          assessment_deadline: drawerAssessmentDeadline ? new Date(drawerAssessmentDeadline).toISOString() : null,
          assessment_notes: drawerAssessmentNotes || null,
          outcome: drawerOutcome || null,
          outcome_notes: drawerOutcomeNotes || null,
          offer_compensation: drawerCompensation || null,
          next_action: drawerNextAction || null,
        }),
      });
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedApp(updated);
      toast.success("CRM details saved successfully");
      fetchHistory(selectedApp.id);
    } catch (err: any) {
      toast.error(err.message || "Failed to update CRM details");
    } finally {
      setIsSavingCrm(false);
    }
  };

  const handleConfirmSubmission = async () => {
    if (!confirmModalApp) return;
    setIsConfirming(true);
    try {
      const updated = await apiFetch<AppData>(
        `/api/v1/applications/${confirmModalApp.id}/confirm-submission`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: confirmSource,
            notes: confirmNotes,
          }),
        }
      );
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      if (selectedApp && selectedApp.id === updated.id) {
        setSelectedApp(updated);
      }
      toast.success("Application confirmed! Submitted materials permanently frozen.", {
        icon: "🔒",
      });
      setConfirmModalApp(null);
      setConfirmNotes("");
    } catch (err: any) {
      toast.error(err.message || "Failed to confirm submission");
    } finally {
      setIsConfirming(false);
    }
  };

  const handleAddFollowUp = async () => {
    if (!selectedApp || !newFollowUpTitle.trim()) return;
    try {
      const updated = await apiFetch<AppData>(
        `/api/v1/applications/${selectedApp.id}/follow-ups`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: newFollowUpTitle.trim(),
            due_date: newFollowUpDate ? new Date(newFollowUpDate).toISOString() : null,
            completed: false,
          }),
        }
      );
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedApp(updated);
      setNewFollowUpTitle("");
      setNewFollowUpDate("");
      toast.success("Follow-up task added");
    } catch (err: any) {
      toast.error(err.message || "Failed to add follow-up");
    }
  };

  const handleToggleFollowUp = async (fu: FollowUpItem) => {
    if (!selectedApp) return;
    try {
      const updated = await apiFetch<AppData>(
        `/api/v1/applications/${selectedApp.id}/follow-ups`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: fu.id,
            title: fu.title,
            due_date: fu.due_date,
            completed: !fu.completed,
            notes: fu.notes,
          }),
        }
      );
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedApp(updated);
    } catch (err: any) {
      toast.error(err.message || "Failed to update follow-up");
    }
  };

  const handleDeleteFollowUp = async (fuId?: string) => {
    if (!selectedApp || !fuId) return;
    try {
      const updated = await apiFetch<AppData>(
        `/api/v1/applications/${selectedApp.id}/follow-ups/${fuId}`,
        { method: "DELETE" }
      );
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedApp(updated);
      toast.success("Follow-up item removed");
    } catch (err: any) {
      toast.error(err.message || "Failed to remove follow-up");
    }
  };

  const handleAddReminder = async () => {
    if (!selectedApp || !newReminderTitle.trim() || !newReminderDate) {
      toast.error("Please provide reminder title and date/time");
      return;
    }
    setIsAddingReminder(true);
    try {
      const updated = await apiFetch<AppData>(
        `/api/v1/applications/${selectedApp.id}/reminders`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: newReminderTitle.trim(),
            remind_at: new Date(newReminderDate).toISOString(),
            reminder_type: newReminderType,
            notes: newReminderNotes.trim() || null,
          }),
        }
      );
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedApp(updated);
      setNewReminderTitle("");
      setNewReminderDate("");
      setNewReminderNotes("");
      toast.success("Scheduled reminder added successfully!");
    } catch (err: any) {
      toast.error(err.message || "Failed to add reminder");
    } finally {
      setIsAddingReminder(false);
    }
  };

  const handleDeleteReminder = async (remId?: string) => {
    if (!selectedApp || !remId) return;
    try {
      const updated = await apiFetch<AppData>(
        `/api/v1/applications/${selectedApp.id}/reminders/${remId}`,
        { method: "DELETE" }
      );
      setApps((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedApp(updated);
      toast.success("Reminder dismissed");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete reminder");
    }
  };

  const fetchCandidateProfile = async () => {
    try {
      const data = await apiFetch<any>("/api/v1/profile/");
      setCandidateProfile(data);
    } catch {
      // ignore
    }
  };

  const fetchCoverLetterText = async (jobId: number) => {
    setIsLoadingCoverLetter(true);
    try {
      const data = await apiFetch<any>(`/api/v1/cover-letters/job/${jobId}`);
      if (data && data.content) {
        setCoverLetterText(data.content);
      } else {
        setCoverLetterText("");
      }
    } catch {
      setCoverLetterText("");
    } finally {
      setIsLoadingCoverLetter(false);
    }
  };

  const filteredApps = apps.filter((app) => {
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      app.company.toLowerCase().includes(q) ||
      app.role.toLowerCase().includes(q) ||
      (app.notes && app.notes.toLowerCase().includes(q));

    const matchesStatus =
      statusFilter === "all" ||
      app.status.toLowerCase() === statusFilter.toLowerCase();

    let matchesStage = true;
    if (stageFilter === "active") {
      matchesStage = ["preparing", "ready to apply", "applied", "generating", "generated"].includes(
        app.status.toLowerCase()
      );
    } else if (stageFilter === "interview") {
      matchesStage = [
        "assessment received",
        "interview scheduled",
        "interview completed",
        "interview",
        "oa",
      ].includes(app.status.toLowerCase());
    } else if (stageFilter === "outcomes") {
      matchesStage = ["offer received", "offer", "rejected", "withdrawn", "position closed"].includes(
        app.status.toLowerCase()
      );
    }

    return matchesSearch && matchesStatus && matchesStage;
  }).sort((a, b) => {
    let comparison = 0;
    if (sortBy === "company") {
      comparison = a.company.localeCompare(b.company);
    } else if (sortBy === "role") {
      comparison = a.role.localeCompare(b.role);
    } else if (sortBy === "status") {
      comparison = (a.status || "").localeCompare(b.status || "");
    } else if (sortBy === "applied_at") {
      const timeA = a.applied_at ? new Date(a.applied_at).getTime() : 0;
      const timeB = b.applied_at ? new Date(b.applied_at).getTime() : 0;
      comparison = timeA - timeB;
    } else if (sortBy === "interview_date") {
      const timeA = a.interview_date ? new Date(a.interview_date).getTime() : 0;
      const timeB = b.interview_date ? new Date(b.interview_date).getTime() : 0;
      comparison = timeA - timeB;
    } else if (sortBy === "assessment_deadline") {
      const timeA = a.assessment_deadline ? new Date(a.assessment_deadline).getTime() : 0;
      const timeB = b.assessment_deadline ? new Date(b.assessment_deadline).getTime() : 0;
      comparison = timeA - timeB;
    } else {
      // Default: updated_at descending
      const timeA = a.updated_at ? new Date(a.updated_at).getTime() : (a.created_at ? new Date(a.created_at).getTime() : a.id);
      const timeB = b.updated_at ? new Date(b.updated_at).getTime() : (b.created_at ? new Date(b.created_at).getTime() : b.id);
      comparison = timeA - timeB;
    }
    return sortOrder === "asc" ? comparison : -comparison;
  });

  // Kanban Columns Mapping
  const KANBAN_COLUMNS = [
    {
      id: "discovered_saved",
      title: "Discovered & Saved",
      statuses: ["Discovered", "Saved", "Shortlisted"],
      accent: "border-t-blue-500",
    },
    {
      id: "preparing_ready",
      title: "Preparing & Ready",
      statuses: ["Preparing", "Ready to Apply", "generating", "generated"],
      accent: "border-t-amber-500",
    },
    {
      id: "applied",
      title: "Applied (Confirmed)",
      statuses: ["Applied"],
      accent: "border-t-teal-500",
    },
    {
      id: "screening",
      title: "Assessments & OA",
      statuses: ["Assessment Received", "oa"],
      accent: "border-t-orange-500",
    },
    {
      id: "interviewing",
      title: "Interviews",
      statuses: ["Interview Scheduled", "Interview Completed", "interview"],
      accent: "border-t-purple-500",
    },
    {
      id: "outcomes",
      title: "Offers & Outcomes",
      statuses: ["Offer Received", "offer", "Rejected", "Withdrawn", "Position Closed"],
      accent: "border-t-emerald-500",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
              Application Tracker CRM
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              {apps.length} Total
            </span>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            Complete candidate CRM: Track stages, schedule interviews, freeze submitted snapshots, and sync calendar reminders.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Master Calendar Export */}
          <a
            href={`${API_BASE}/api/v1/applications/calendar/export.ics`}
            download="all_applications_calendar.ics"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-zinc-700 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 shadow-sm transition-colors"
            title="Download full RFC 5545 iCalendar stream with all interviews and deadlines"
          >
            <Download size={14} className="text-zinc-500" />
            Calendar Sync (.ics)
          </a>

          {/* View Mode Toggle */}
          <div className="inline-flex items-center bg-zinc-100 p-1 rounded-lg border border-zinc-200">
            <button
              onClick={() => setViewMode("kanban")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === "kanban"
                  ? "bg-white text-zinc-900 shadow-sm"
                  : "text-zinc-600 hover:text-zinc-900"
              }`}
            >
              <KanbanIcon size={14} />
              Kanban
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === "table"
                  ? "bg-white text-zinc-900 shadow-sm"
                  : "text-zinc-600 hover:text-zinc-900"
              }`}
            >
              <TableIcon size={14} />
              Table
            </button>
          </div>
        </div>
      </div>

      {/* Pipeline Quick Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-zinc-200 shadow-xs">
          <div className="text-xs font-medium text-zinc-500">Pipeline Total</div>
          <div className="text-xl font-bold text-zinc-900 mt-1">{apps.length}</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-zinc-200 shadow-xs">
          <div className="text-xs font-medium text-amber-600">Preparing / Ready</div>
          <div className="text-xl font-bold text-zinc-900 mt-1">
            {apps.filter((a) => ["preparing", "ready to apply", "generating", "generated"].includes(a.status.toLowerCase())).length}
          </div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-zinc-200 shadow-xs">
          <div className="text-xs font-medium text-teal-600">Applied (Confirmed)</div>
          <div className="text-xl font-bold text-zinc-900 mt-1">
            {apps.filter((a) => a.submission_confirmed || a.status.toLowerCase() === "applied").length}
          </div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-zinc-200 shadow-xs">
          <div className="text-xs font-medium text-purple-600">Interviews Active</div>
          <div className="text-xl font-bold text-zinc-900 mt-1">
            {apps.filter((a) => a.interview_date || a.status.toLowerCase().includes("interview")).length}
          </div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-zinc-200 shadow-xs">
          <div className="text-xs font-medium text-orange-600">Assessments Due</div>
          <div className="text-xl font-bold text-zinc-900 mt-1">
            {apps.filter((a) => a.assessment_deadline || a.status.toLowerCase().includes("assessment") || a.status.toLowerCase() === "oa").length}
          </div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-zinc-200 shadow-xs">
          <div className="text-xs font-medium text-emerald-600">Offers Received</div>
          <div className="text-xl font-bold text-zinc-900 mt-1">
            {apps.filter((a) => a.status.toLowerCase().includes("offer")).length}
          </div>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search candidate pipeline by company, title, notes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-zinc-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 shadow-xs"
          />
        </div>

        {/* Stage Filter */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <button
            onClick={() => setStageFilter("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              stageFilter === "all"
                ? "bg-zinc-900 text-white"
                : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50"
            }`}
          >
            All Stages
          </button>
          <button
            onClick={() => setStageFilter("active")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              stageFilter === "active"
                ? "bg-zinc-900 text-white"
                : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50"
            }`}
          >
            Active Pipeline
          </button>
          <button
            onClick={() => setStageFilter("interview")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              stageFilter === "interview"
                ? "bg-zinc-900 text-white"
                : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50"
            }`}
          >
            Interviews & OA
          </button>
          <button
            onClick={() => setStageFilter("outcomes")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              stageFilter === "outcomes"
                ? "bg-zinc-900 text-white"
                : "bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50"
            }`}
          >
            Outcomes
          </button>
        </div>

        {/* Specific Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-700 focus:outline-none focus:border-indigo-400 shadow-xs"
        >
          <option value="all">All Statuses</option>
          {CANONICAL_STATUSES.map((st) => (
            <option key={st.value} value={st.value}>
              {st.label}
            </option>
          ))}
        </select>

        {/* Sort Controls */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-700 focus:outline-none focus:border-indigo-400 shadow-xs"
            aria-label="Sort applications"
          >
            <option value="updated_at">Sort: Last Updated</option>
            <option value="applied_at">Sort: Applied Date</option>
            <option value="created_at">Sort: Date Added</option>
            <option value="match_score">Sort: Match Score</option>
            <option value="company">Sort: Company</option>
            <option value="role">Sort: Role</option>
            <option value="status">Sort: Status</option>
          </select>
          <button
            onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
            className="p-2 border border-zinc-200 rounded-lg text-xs bg-white hover:bg-zinc-50 text-zinc-700 transition-colors shadow-xs"
            title={`Order: ${sortOrder === "asc" ? "Ascending" : "Descending"} (Click to flip)`}
          >
            <ArrowUpDown size={14} className={sortOrder === "asc" ? "rotate-180 transition-transform" : "transition-transform"} />
          </button>
        </div>
      </div>

      {/* Main Content: Kanban or Table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-zinc-200 p-8 text-center text-zinc-400">
          Loading candidate applications CRM...
        </div>
      ) : filteredApps.length === 0 ? (
        <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center">
          <Building2 size={36} className="mx-auto text-zinc-300 mb-3" />
          <h3 className="text-sm font-semibold text-zinc-900">No applications match criteria</h3>
          <p className="text-xs text-zinc-500 mt-1">
            Try adjusting your search query or stage filter, or apply to a job from the Job Feed.
          </p>
        </div>
      ) : viewMode === "kanban" ? (
        /* ================= KANBAN BOARD VIEW ================= */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 items-start">
          {KANBAN_COLUMNS.map((col) => {
            const columnApps = filteredApps.filter((app) =>
              col.statuses.some((s) => s.toLowerCase() === app.status.toLowerCase())
            );

            return (
              <div
                key={col.id}
                className="bg-zinc-50/80 rounded-xl border border-zinc-200/80 flex flex-col max-h-[820px] shadow-xs"
              >
                {/* Column Header */}
                <div className={`p-3 border-t-4 ${col.accent} bg-white rounded-t-xl border-b border-zinc-200 flex items-center justify-between`}>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-zinc-800 tracking-tight">
                      {col.title}
                    </span>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-600">
                    {columnApps.length}
                  </span>
                </div>

                {/* Cards Container */}
                <div className="p-2 space-y-2.5 overflow-y-auto flex-1">
                  {columnApps.map((app) => {
                    const badge = getStatusBadge(app.status);

                    return (
                      <div
                        key={app.id}
                        onClick={() => handleOpenDrawer(app)}
                        className="bg-white p-3 rounded-lg border border-zinc-200/80 hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer group space-y-2.5"
                      >
                        {/* Company & Role */}
                        <div>
                          <div className="flex items-start justify-between gap-1">
                            <h4 className="text-xs font-bold text-zinc-900 line-clamp-1 group-hover:text-indigo-600 transition-colors">
                              {app.company}
                            </h4>
                            <span
                              className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${badge.color}`}
                            >
                              {badge.label}
                            </span>
                          </div>
                          <p className="text-xs text-zinc-600 line-clamp-1 font-medium mt-0.5">
                            {app.role}
                          </p>
                        </div>

                        {/* Submission Frozen Badge or Explicit Confirm Action */}
                        <div className="flex items-center justify-between text-[11px] pt-1 border-t border-zinc-100">
                          {app.submission_confirmed ? (
                            <span className="inline-flex items-center gap-1 text-teal-700 font-medium">
                              <ShieldCheck size={12} className="text-teal-600" />
                              Frozen Snapshot
                            </span>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setConfirmModalApp(app);
                              }}
                              className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 px-2 py-0.5 rounded border border-amber-200 transition-colors"
                              title="Require candidate approval to mark as applied and freeze snapshot"
                            >
                              <AlertCircle size={11} />
                              Confirm Applied
                            </button>
                          )}

                          {app.source && (
                            <span className="text-zinc-400 text-[10px] truncate max-w-[80px]">
                              {app.source}
                            </span>
                          )}
                        </div>

                        {/* Interview or Assessment Tags */}
                        {app.interview_date && (
                          <div className="flex items-center gap-1.5 text-[11px] text-purple-700 bg-purple-50 px-2 py-1 rounded border border-purple-100">
                            <Calendar size={12} />
                            <span className="truncate">
                              {new Date(app.interview_date).toLocaleDateString([], {
                                month: "short",
                                day: "numeric",
                              })}{" "}
                              • {app.interview_round || "Round"}
                            </span>
                          </div>
                        )}

                        {app.assessment_deadline && (
                          <div className="flex items-center gap-1.5 text-[11px] text-orange-700 bg-orange-50 px-2 py-1 rounded border border-orange-100">
                            <Clock size={12} />
                            <span className="truncate">
                              Due:{" "}
                              {new Date(app.assessment_deadline).toLocaleDateString([], {
                                month: "short",
                                day: "numeric",
                              })}
                            </span>
                          </div>
                        )}

                        {/* Card Footer Quick Actions */}
                        <div className="flex items-center justify-between pt-1 text-zinc-400">
                          <Link
                            href={`/interview-prep?jobId=${app.job_id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-[11px] text-zinc-600 hover:text-indigo-600 font-medium transition-colors"
                            title="Open interview prep workspace for this job"
                          >
                            <GraduationCap size={12} />
                            Prep
                          </Link>

                          <div className="flex items-center gap-1">
                            {app.application_url || app.job_url ? (
                              <a
                                href={app.application_url || app.job_url}
                                target="_blank"
                                rel="noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="p-1 hover:text-zinc-700 transition-colors"
                                title="Open official company job portal"
                              >
                                <ExternalLink size={12} />
                              </a>
                            ) : null}

                            <a
                              href={`${API_BASE}/api/v1/applications/${app.id}/calendar.ics`}
                              download={`application_${app.id}.ics`}
                              onClick={(e) => e.stopPropagation()}
                              className="p-1 hover:text-zinc-700 transition-colors"
                              title="Export application dates to iCalendar (.ics)"
                            >
                              <Calendar size={12} />
                            </a>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* ================= TABLE VIEW ================= */
        <div className="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-600 divide-y divide-zinc-200">
              <thead className="bg-zinc-50 font-semibold text-zinc-700 text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Company & Role</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Submission Verification</th>
                  <th className="py-3 px-4">Dates & Deadlines</th>
                  <th className="py-3 px-4">Next Action / Notes</th>
                  <th className="py-3 px-4 text-right">Quick Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {filteredApps.map((app) => {
                  const badge = getStatusBadge(app.status);

                  return (
                    <tr
                      key={app.id}
                      onClick={() => handleOpenDrawer(app)}
                      className="hover:bg-zinc-50/80 cursor-pointer transition-colors"
                    >
                      {/* Company & Role */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-zinc-900 text-xs">{app.company}</div>
                        <div className="text-zinc-500 font-medium text-[11px] mt-0.5">{app.role}</div>
                        {app.job_location && (
                          <div className="text-zinc-400 text-[10px] mt-0.5">{app.job_location}</div>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        <span className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-semibold border ${badge.color}`}>
                          {badge.label}
                        </span>
                      </td>

                      {/* Submission Verification */}
                      <td className="py-3.5 px-4">
                        {app.submission_confirmed ? (
                          <div>
                            <span className="inline-flex items-center gap-1 font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200 text-[11px]">
                              <ShieldCheck size={12} />
                              Snapshot Frozen
                            </span>
                            <div className="text-[10px] text-zinc-400 mt-1">
                              {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : "Confirmed"}
                            </div>
                          </div>
                        ) : (
                          <div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setConfirmModalApp(app);
                              }}
                              className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 px-2 py-1 rounded border border-amber-200 transition-colors"
                            >
                              <AlertCircle size={12} />
                              Confirm Submission
                            </button>
                            <div className="text-[10px] text-zinc-400 mt-1">Pending user approval</div>
                          </div>
                        )}
                      </td>

                      {/* Dates & Deadlines */}
                      <td className="py-3.5 px-4 space-y-1">
                        {app.interview_date ? (
                          <div className="text-purple-700 font-medium text-[11px] flex items-center gap-1">
                            <Calendar size={12} />
                            {new Date(app.interview_date).toLocaleDateString()} ({app.interview_round || "Round"})
                          </div>
                        ) : null}
                        {app.assessment_deadline ? (
                          <div className="text-orange-700 font-medium text-[11px] flex items-center gap-1">
                            <Clock size={12} />
                            Due: {new Date(app.assessment_deadline).toLocaleDateString()}
                          </div>
                        ) : null}
                        {!app.interview_date && !app.assessment_deadline && (
                          <span className="text-zinc-400 text-[11px]">None scheduled</span>
                        )}
                      </td>

                      {/* Next Action & Notes */}
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="text-xs text-zinc-800 line-clamp-1">
                          {app.next_action || "Awaiting recruiter response"}
                        </div>
                        {app.notes && (
                          <div className="text-[11px] text-zinc-400 line-clamp-1 mt-0.5">
                            {app.notes}
                          </div>
                        )}
                      </td>

                      {/* Quick Actions */}
                      <td className="py-3.5 px-4 text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                        <Link
                          href={`/interview-prep?jobId=${app.job_id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-zinc-700 bg-white border border-zinc-200 rounded hover:bg-zinc-50 transition-colors"
                        >
                          <GraduationCap size={12} className="text-indigo-600" />
                          Prep
                        </Link>

                        {app.application_url || app.job_url ? (
                          <a
                            href={app.application_url || app.job_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-zinc-700 bg-white border border-zinc-200 rounded hover:bg-zinc-50 transition-colors"
                          >
                            <ExternalLink size={12} />
                            Portal
                          </a>
                        ) : null}

                        <a
                          href={`${API_BASE}/api/v1/applications/${app.id}/calendar.ics`}
                          download={`application_${app.id}.ics`}
                          className="inline-flex items-center px-2 py-1 text-xs font-medium text-zinc-700 bg-white border border-zinc-200 rounded hover:bg-zinc-50 transition-colors"
                          title="Download Calendar (.ics)"
                        >
                          <Calendar size={12} />
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= CONFIRM SUBMISSION MODAL ================= */}
      {confirmModalApp && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-zinc-200 space-y-4 animate-in fade-in zoom-in duration-150">
            <div className="flex items-start justify-between">
              <div>
                <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200 mb-2">
                  <ShieldCheck size={12} />
                  Trustworthy Verification
                </span>
                <h3 className="text-lg font-bold text-zinc-900 tracking-tight">
                  Confirm Application Submission
                </h3>
              </div>
              <button
                onClick={() => setConfirmModalApp(null)}
                className="text-zinc-400 hover:text-zinc-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-zinc-600 leading-relaxed">
              Confirm that you have officially submitted your application for{" "}
              <strong className="text-zinc-900">{confirmModalApp.role}</strong> at{" "}
              <strong className="text-zinc-900">{confirmModalApp.company}</strong>.
            </p>

            <div className="bg-zinc-50 p-3 rounded-xl border border-zinc-200 text-xs text-zinc-600 space-y-1">
              <div className="font-semibold text-zinc-800 flex items-center gap-1">
                <CheckCircle2 size={13} className="text-teal-600" />
                Snapshot Immutability Guarantee
              </div>
              <p className="text-[11px] text-zinc-500 leading-normal">
                Confirming will freeze the exact submitted resume and cover letter versions permanently.
                Any subsequent edits to your master profile or resume will never alter this submitted record.
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-zinc-700 block mb-1">Application Source / Channel</label>
                <input
                  type="text"
                  value={confirmSource}
                  onChange={(e) => setConfirmSource(e.target.value)}
                  placeholder="e.g. Greenhouse, Workday, LinkedIn, Referral"
                  className="w-full px-3 py-2 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div>
                <label className="font-semibold text-zinc-700 block mb-1">
                  Submission Notes or Confirmation Number (Optional)
                </label>
                <textarea
                  value={confirmNotes}
                  onChange={(e) => setConfirmNotes(e.target.value)}
                  rows={2}
                  placeholder="e.g. Received confirmation email #REQ-89412"
                  className="w-full px-3 py-2 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setConfirmModalApp(null)}
                className="px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={isConfirming}
                onClick={handleConfirmSubmission}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-sm transition-colors disabled:opacity-50"
              >
                <Check size={14} />
                {isConfirming ? "Freezing Snapshot..." : "Confirm & Freeze Snapshot"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= CRM DRAWER ================= */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex justify-end">
          <div className="bg-white w-full max-w-2xl h-full shadow-2xl flex flex-col border-l border-zinc-200 animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-zinc-200 flex items-start justify-between bg-zinc-50/50">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                    Application Workspace
                  </span>
                  {selectedApp.submission_confirmed && (
                    <span className="text-[10px] font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-200 flex items-center gap-1">
                      <ShieldCheck size={11} />
                      Immutable Snapshot
                    </span>
                  )}
                </div>
                <h2 className="text-lg font-bold text-zinc-900 mt-1">{selectedApp.company}</h2>
                <p className="text-xs text-zinc-600 font-medium">{selectedApp.role}</p>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={`${API_BASE}/api/v1/applications/${selectedApp.id}/calendar.ics`}
                  download={`application_${selectedApp.id}.ics`}
                  className="p-1.5 rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 text-xs flex items-center gap-1"
                  title="Export application calendar (.ics)"
                >
                  <Calendar size={14} />
                  .ics
                </a>
                <button
                  onClick={() => setSelectedApp(null)}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Drawer Tabs */}
            <div className="flex items-center px-5 border-b border-zinc-200 gap-4 text-xs font-semibold text-zinc-500 overflow-x-auto bg-white">
              <button
                onClick={() => setActiveDrawerTab("overview")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  activeDrawerTab === "overview"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                Overview & Status
              </button>
              <button
                onClick={() => setActiveDrawerTab("assisted_apply")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  activeDrawerTab === "assisted_apply"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                <span>Assisted Apply</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] bg-indigo-50 text-indigo-700 font-bold border border-indigo-200">
                  Quick Flow
                </span>
              </button>
              <button
                onClick={() => setActiveDrawerTab("schedule")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  activeDrawerTab === "schedule"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                Interviews & Deadlines
              </button>
              <button
                onClick={() => setActiveDrawerTab("followups")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  activeDrawerTab === "followups"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                Follow-ups & Reminders
              </button>
              <button
                onClick={() => setActiveDrawerTab("frozen_materials")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  activeDrawerTab === "frozen_materials"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                Frozen Materials
              </button>
              <button
                onClick={() => setActiveDrawerTab("timeline")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  activeDrawerTab === "timeline"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                Timeline History
              </button>
              <button
                onClick={() => setActiveDrawerTab("outcome")}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  activeDrawerTab === "outcome"
                    ? "border-zinc-900 text-zinc-900"
                    : "border-transparent hover:text-zinc-700"
                }`}
              >
                Outcome & Offer
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 p-5 overflow-y-auto space-y-5 text-xs">
              {/* TAB 1: OVERVIEW */}
              {activeDrawerTab === "overview" && (
                <div className="space-y-4">
                  {/* Status Dropdown */}
                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1">CRM Status</label>
                    <select
                      value={drawerStatus}
                      onChange={(e) => setDrawerStatus(e.target.value)}
                      className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    >
                      {CANONICAL_STATUSES.map((st) => (
                        <option key={st.value} value={st.value}>
                          {st.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Submission Confirmation Banner */}
                  {!selectedApp.submission_confirmed ? (
                    <div className="bg-amber-50 p-3 rounded-xl border border-amber-200 flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-amber-900">Submission Unconfirmed</div>
                        <div className="text-[11px] text-amber-700 mt-0.5">
                          Confirming freezes the exact resume & cover letter versions.
                        </div>
                      </div>
                      <button
                        onClick={() => setConfirmModalApp(selectedApp)}
                        className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs transition-colors"
                      >
                        Confirm Now
                      </button>
                    </div>
                  ) : (
                    <div className="bg-teal-50 p-3 rounded-xl border border-teal-200 text-teal-800 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldCheck size={18} className="text-teal-600" />
                        <div>
                          <div className="font-semibold">Submitted & Snapshot Frozen</div>
                          <div className="text-[11px] text-teal-700">
                            Applied {selectedApp.applied_at ? new Date(selectedApp.applied_at).toLocaleString() : ""} via {selectedApp.source || "Portal"}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => setActiveDrawerTab("frozen_materials")}
                        className="text-xs text-teal-900 underline font-semibold"
                      >
                        View Snapshot
                      </button>
                    </div>
                  )}

                  {/* Source & Links */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="font-semibold text-zinc-700 block mb-1">Source / Portal</label>
                      <input
                        type="text"
                        value={drawerSource}
                        onChange={(e) => setDrawerSource(e.target.value)}
                        placeholder="e.g. Greenhouse, LinkedIn"
                        className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-zinc-700 block mb-1">Official Portal Link</label>
                      <div className="flex items-center gap-2">
                        {selectedApp.application_url || selectedApp.job_url ? (
                          <a
                            href={selectedApp.application_url || selectedApp.job_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:underline font-medium py-2"
                          >
                            <ExternalLink size={13} />
                            Open Job Post / Portal
                          </a>
                        ) : (
                          <span className="text-zinc-400 py-2">No portal link saved</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Next Action */}
                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1">Next Action Step</label>
                    <input
                      type="text"
                      value={drawerNextAction}
                      onChange={(e) => setDrawerNextAction(e.target.value)}
                      placeholder="e.g. Complete OA before Friday, follow up with recruiter"
                      className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                    />
                  </div>

                  {/* Notes */}
                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1">Application Notes</label>
                    <textarea
                      value={drawerNotes}
                      onChange={(e) => setDrawerNotes(e.target.value)}
                      rows={4}
                      placeholder="Recruiter names, interview focus areas, follow-up thoughts..."
                      className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>

                  {/* Quick Shortcut to Interview Prep */}
                  <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-indigo-950 flex items-center gap-1.5">
                        <GraduationCap size={15} className="text-indigo-600" />
                        Interview Prep Workspace
                      </div>
                      <div className="text-[11px] text-indigo-700 mt-0.5">
                        Practice role-specific mock questions, STAR behavioral responses, and get instant AI feedback.
                      </div>
                    </div>
                    <Link
                      href={`/interview-prep?jobId=${selectedApp.job_id}`}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-semibold hover:bg-indigo-700 transition-colors"
                    >
                      Start Prep
                    </Link>
                  </div>
                </div>
              )}

              {/* TAB: ASSISTED APPLICATION WORKFLOW */}
              {activeDrawerTab === "assisted_apply" && (
                <div className="space-y-4">
                  {/* Security & Authorization Guardrail */}
                  <div className="bg-amber-50/70 p-3.5 rounded-xl border border-amber-200 text-amber-950 text-xs flex items-start gap-2.5">
                    <AlertCircle size={18} className="text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold">Security & Authorization Guardrail</div>
                      <p className="text-[11px] text-amber-800 leading-relaxed mt-0.5">
                        This workflow respects third-party access controls and candidate privacy. No forms are submitted
                        and no personal information is disclosed without your explicit approval. Opening external portal
                        links will never mark an application as submitted.
                      </p>
                    </div>
                  </div>

                  {/* External Portal Launcher */}
                  <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-3 shadow-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-zinc-900 text-xs flex items-center gap-1.5">
                        <Building2 size={14} className="text-zinc-600" />
                        Original Application Portal
                      </span>
                      <span className="text-[10px] font-semibold text-zinc-500 bg-zinc-100 px-2 py-0.5 rounded-full">
                        Source: {selectedApp.source || "Portal"}
                      </span>
                    </div>

                    <p className="text-[11px] text-zinc-600">
                      Launch the employer&apos;s direct application link in a new tab. When finished submitting, return here to
                      explicitly confirm your application and permanently freeze your documents.
                    </p>

                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      {selectedApp.application_url || selectedApp.job_url ? (
                        <a
                          href={selectedApp.application_url || selectedApp.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-xs transition-colors"
                        >
                          <ExternalLink size={13} />
                          Launch Application Portal
                        </a>
                      ) : (
                        <span className="text-xs text-zinc-400 italic">No direct URL provided for this position.</span>
                      )}

                      {!selectedApp.submission_confirmed ? (
                        <button
                          onClick={() => setConfirmModalApp(selectedApp)}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-xs transition-colors"
                        >
                          <CheckCircle2 size={13} />
                          Confirm Submission & Freeze
                        </button>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-teal-50 text-teal-800 border border-teal-200 font-semibold text-xs">
                          <ShieldCheck size={14} className="text-teal-600" />
                          Submission Verified &amp; Frozen
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Prepared Application Documents */}
                  <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-3 shadow-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-zinc-900 text-xs flex items-center gap-1.5">
                        <FileText size={14} className="text-indigo-600" />
                        Prepared Documents
                      </span>
                      <span className="text-[10px] text-zinc-400">Ready to upload or submit</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      <a
                        href={`${API_BASE}/api/v1/applications/${selectedApp.id}/resume.pdf`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-2.5 rounded-lg border border-zinc-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <Download size={14} className="text-indigo-600" />
                          <span className="font-semibold text-zinc-800">Resume PDF</span>
                        </div>
                        <span className="text-[10px] text-zinc-400">Compiled PDF</span>
                      </a>

                      <a
                        href={`${API_BASE}/api/v1/applications/${selectedApp.id}/resume.tex`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-2.5 rounded-lg border border-zinc-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <FileCheck size={14} className="text-indigo-600" />
                          <span className="font-semibold text-zinc-800">Resume LaTeX</span>
                        </div>
                        <span className="text-[10px] text-zinc-400">Source (.tex)</span>
                      </a>
                    </div>

                    {/* Tailored Cover Letter Preview */}
                    <div className="pt-2 border-t border-zinc-100">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-semibold text-zinc-700 text-xs">Tailored Cover Letter</span>
                        {coverLetterText && (
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(coverLetterText);
                              toast.success("Cover letter copied to clipboard!");
                            }}
                            className="inline-flex items-center gap-1 text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold"
                          >
                            <Copy size={11} />
                            Copy Full Text
                          </button>
                        )}
                      </div>
                      {isLoadingCoverLetter ? (
                        <div className="p-3 text-center text-zinc-400 text-xs">Loading cover letter...</div>
                      ) : coverLetterText ? (
                        <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg text-xs text-zinc-700 font-sans max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                          {coverLetterText}
                        </div>
                      ) : (
                        <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-400 text-xs text-center">
                          No tailored cover letter generated yet.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Candidate Quick-Copy Fields */}
                  <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-3 shadow-xs">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-bold text-zinc-900 text-xs">Candidate Quick-Copy Assistant</span>
                        <p className="text-[10px] text-zinc-500 mt-0.5">
                          1-click copy verified candidate profile values into external forms
                        </p>
                      </div>
                      <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
                        Autofill Helper
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      {[
                        {
                          label: "Full Name",
                          val: candidateProfile?.name || candidateProfile?.full_name || "Candidate",
                        },
                        {
                          label: "Email Address",
                          val: candidateProfile?.email || "candidate@example.com",
                        },
                        {
                          label: "Phone Number",
                          val: candidateProfile?.phone || candidateProfile?.phone_number || "+1 (555) 000-0000",
                        },
                        {
                          label: "Location",
                          val: candidateProfile?.location || candidateProfile?.address || "United States",
                        },
                        {
                          label: "LinkedIn Profile",
                          val: candidateProfile?.linkedin || candidateProfile?.social_links?.linkedin || "https://linkedin.com",
                        },
                        {
                          label: "GitHub Profile",
                          val: candidateProfile?.github || candidateProfile?.social_links?.github || "https://github.com",
                        },
                        {
                          label: "Portfolio / Website",
                          val: candidateProfile?.portfolio || candidateProfile?.website || candidateProfile?.social_links?.portfolio || "https://portfolio.dev",
                        },
                        {
                          label: "Target Role",
                          val: selectedApp.role || "Software Engineer",
                        },
                      ].map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 border border-zinc-200"
                        >
                          <div className="overflow-hidden pr-2">
                            <div className="text-[10px] font-semibold text-zinc-500 uppercase">{item.label}</div>
                            <div className="text-xs text-zinc-800 font-medium truncate">{item.val}</div>
                          </div>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(item.val);
                              toast.success(`Copied ${item.label}!`);
                            }}
                            className="p-1.5 rounded-md hover:bg-zinc-200 text-zinc-600 transition-colors shrink-0"
                            title={`Copy ${item.label}`}
                          >
                            <Copy size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: SCHEDULE */}
              {activeDrawerTab === "schedule" && (
                <div className="space-y-4">
                  {/* Interview Date & Round */}
                  <div className="p-4 bg-purple-50/50 rounded-xl border border-purple-200 space-y-3">
                    <div className="font-bold text-purple-950 flex items-center gap-1.5 text-sm">
                      <Calendar size={15} className="text-purple-600" />
                      Interview Details
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="font-semibold text-zinc-700 block mb-1">Interview Date & Time</label>
                        <input
                          type="datetime-local"
                          value={drawerInterviewDate}
                          onChange={(e) => setDrawerInterviewDate(e.target.value)}
                          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                        />
                      </div>
                      <div>
                        <label className="font-semibold text-zinc-700 block mb-1">Interview Round</label>
                        <input
                          type="text"
                          value={drawerInterviewRound}
                          onChange={(e) => setDrawerInterviewRound(e.target.value)}
                          placeholder="e.g. Recruiter Screen, System Design, DSA Round 2"
                          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="font-semibold text-zinc-700 block mb-1">Interview Preparation Notes</label>
                      <textarea
                        value={drawerInterviewNotes}
                        onChange={(e) => setDrawerInterviewNotes(e.target.value)}
                        rows={2}
                        placeholder="Interviewers, format, Zoom links, behavioral topics..."
                        className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                      />
                    </div>
                  </div>

                  {/* Assessment Deadline */}
                  <div className="p-4 bg-orange-50/50 rounded-xl border border-orange-200 space-y-3">
                    <div className="font-bold text-orange-950 flex items-center gap-1.5 text-sm">
                      <Clock size={15} className="text-orange-600" />
                      Assessment & OA Deadline
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="font-semibold text-zinc-700 block mb-1">Deadline Date & Time</label>
                        <input
                          type="datetime-local"
                          value={drawerAssessmentDeadline}
                          onChange={(e) => setDrawerAssessmentDeadline(e.target.value)}
                          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                        />
                      </div>
                      <div>
                        <label className="font-semibold text-zinc-700 block mb-1">Platform / Assessment Notes</label>
                        <input
                          type="text"
                          value={drawerAssessmentNotes}
                          onChange={(e) => setDrawerAssessmentNotes(e.target.value)}
                          placeholder="e.g. HackerRank 90 mins, Take-home project on GitHub"
                          className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: FOLLOW-UPS & REMINDERS */}
              {activeDrawerTab === "followups" && (
                <div className="space-y-5">
                  {/* Follow-up Checklist */}
                  <div className="space-y-2">
                    <h4 className="font-bold text-zinc-900 text-sm">Follow-up Checklist</h4>
                    <div className="space-y-1.5">
                      {(selectedApp.follow_ups || []).length === 0 ? (
                        <div className="p-3 bg-zinc-50 rounded-lg text-zinc-500 text-center text-xs">
                          No follow-up action items created yet.
                        </div>
                      ) : (
                        (selectedApp.follow_ups || []).map((fu, idx) => (
                          <div
                            key={fu.id || idx}
                            onClick={() => handleToggleFollowUp(fu)}
                            className="flex items-center justify-between p-2.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 cursor-pointer transition-colors"
                          >
                            <div className="flex items-center gap-2.5">
                              <input
                                type="checkbox"
                                checked={fu.completed}
                                onChange={() => {}}
                                className="rounded text-indigo-600 focus:ring-0 cursor-pointer"
                              />
                              <span
                                className={`text-xs font-medium ${
                                  fu.completed ? "line-through text-zinc-400" : "text-zinc-800"
                                }`}
                              >
                                {fu.title}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              {fu.due_date && (
                                <span className="text-[11px] text-zinc-400">
                                  Due: {new Date(fu.due_date).toLocaleDateString()}
                                </span>
                              )}
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteFollowUp(fu.id);
                                }}
                                className="p-1 rounded text-zinc-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                                title="Delete task"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Add Follow-up Form */}
                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="text"
                        placeholder="Add follow-up task (e.g. email recruiter)..."
                        value={newFollowUpTitle}
                        onChange={(e) => setNewFollowUpTitle(e.target.value)}
                        className="flex-1 px-3 py-2 border border-zinc-200 rounded-lg text-xs"
                      />
                      <input
                        type="date"
                        value={newFollowUpDate}
                        onChange={(e) => setNewFollowUpDate(e.target.value)}
                        className="px-2 py-2 border border-zinc-200 rounded-lg text-xs text-zinc-600"
                      />
                      <button
                        onClick={handleAddFollowUp}
                        className="px-3 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white font-semibold text-xs flex items-center gap-1 transition-colors"
                      >
                        <Plus size={13} />
                        Add
                      </button>
                    </div>
                  </div>

                  {/* Scheduled Reminders Section */}
                  <div className="pt-4 border-t border-zinc-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-zinc-900 text-sm flex items-center gap-1.5">
                        <Bell size={15} className="text-indigo-600" />
                        Configurable Reminders
                      </h4>
                      <span className="text-[10px] text-zinc-400">
                        Exports into calendar stream (.ics)
                      </span>
                    </div>

                    <div className="space-y-2">
                      {(!selectedApp.reminders || selectedApp.reminders.length === 0) ? (
                        <div className="p-3 bg-zinc-50 rounded-lg text-zinc-500 text-center text-xs">
                          No scheduled reminders set for this application.
                        </div>
                      ) : (
                        selectedApp.reminders.map((rem: any) => (
                          <div
                            key={rem.id}
                            className="p-2.5 rounded-lg border border-zinc-200 bg-white flex items-center justify-between shadow-xs"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-zinc-800 text-xs">
                                  {rem.title}
                                </span>
                                <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600">
                                  {rem.reminder_type || "reminder"}
                                </span>
                              </div>
                              <div className="text-[11px] text-zinc-500 flex items-center gap-2">
                                <Clock size={12} className="text-zinc-400" />
                                <span>{new Date(rem.remind_at).toLocaleString()}</span>
                                {rem.notes && <span>• {rem.notes}</span>}
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleDeleteReminder(rem.id)}
                              className="p-1.5 rounded-md text-zinc-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                              title="Dismiss reminder"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Add Reminder Form */}
                    <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200 space-y-2.5">
                      <div className="text-xs font-bold text-zinc-700">Schedule New Reminder</div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <input
                          type="text"
                          placeholder="Reminder title (e.g. Prep for Round 1)..."
                          value={newReminderTitle}
                          onChange={(e) => setNewReminderTitle(e.target.value)}
                          className="px-3 py-1.5 border border-zinc-200 rounded-lg text-xs bg-white"
                        />
                        <select
                          value={newReminderType}
                          onChange={(e) => setNewReminderType(e.target.value)}
                          className="px-2 py-1.5 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-700"
                        >
                          <option value="interview">Interview Reminder</option>
                          <option value="assessment">Assessment Deadline</option>
                          <option value="deadline">Application Deadline</option>
                          <option value="follow_up">Recruiter Follow-up</option>
                        </select>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <input
                          type="datetime-local"
                          value={newReminderDate}
                          onChange={(e) => setNewReminderDate(e.target.value)}
                          className="px-2 py-1.5 border border-zinc-200 rounded-lg text-xs bg-white text-zinc-700"
                        />
                        <input
                          type="text"
                          placeholder="Optional notes or link..."
                          value={newReminderNotes}
                          onChange={(e) => setNewReminderNotes(e.target.value)}
                          className="px-3 py-1.5 border border-zinc-200 rounded-lg text-xs bg-white"
                        />
                      </div>
                      <button
                        type="button"
                        disabled={isAddingReminder}
                        onClick={handleAddReminder}
                        className="w-full py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                      >
                        <Bell size={13} />
                        {isAddingReminder ? "Scheduling..." : "Schedule Reminder"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: FROZEN SUBMITTED MATERIALS */}
              {activeDrawerTab === "frozen_materials" && (
                <div className="space-y-4">
                  <div className="bg-teal-50 p-3.5 rounded-xl border border-teal-200 text-teal-900 text-xs flex items-start gap-2.5">
                    <ShieldCheck size={18} className="text-teal-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold">Permanent Document Snapshot</div>
                      <p className="text-[11px] text-teal-700 leading-relaxed mt-0.5">
                        These are the exact document versions captured when you confirmed application submission.
                        Even if your Master Resume or Content Library is edited, these records remain 100% frozen.
                      </p>
                    </div>
                  </div>

                  {isLoadingMaterials ? (
                    <div className="p-8 text-center text-zinc-400">Loading frozen materials...</div>
                  ) : !submittedMaterials?.submitted_resume_snapshot &&
                    !submittedMaterials?.submitted_cover_letter_snapshot ? (
                    <div className="p-8 text-center bg-zinc-50 rounded-xl border border-zinc-200">
                      <AlertCircle size={28} className="mx-auto text-amber-500 mb-2" />
                      <div className="font-bold text-zinc-800">No Frozen Snapshot Saved</div>
                      <p className="text-[11px] text-zinc-500 mt-1 max-w-sm mx-auto">
                        This application has not been confirmed yet. Click &ldquo;Confirm Submission&rdquo; to freeze
                        and permanently preserve the submitted materials.
                      </p>
                      <button
                        onClick={() => setConfirmModalApp(selectedApp)}
                        className="mt-3 px-4 py-1.5 rounded-lg bg-teal-600 text-white font-semibold text-xs hover:bg-teal-700 transition-colors"
                      >
                        Confirm Submission & Freeze
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Frozen Resume Snapshot */}
                      <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-zinc-900 flex items-center gap-1.5">
                            <FileText size={14} className="text-zinc-600" />
                            Submitted Resume Snapshot (LaTeX)
                          </span>
                          <button
                            onClick={() => {
                              if (submittedMaterials?.submitted_resume_snapshot) {
                                navigator.clipboard.writeText(submittedMaterials.submitted_resume_snapshot);
                                toast.success("Frozen resume LaTeX copied to clipboard");
                              }
                            }}
                            className="text-[11px] text-indigo-600 hover:underline font-semibold"
                          >
                            Copy Source
                          </button>
                        </div>
                        <pre className="p-3 bg-zinc-900 text-zinc-100 rounded-lg text-[11px] font-mono max-h-56 overflow-y-auto whitespace-pre-wrap">
                          {submittedMaterials?.submitted_resume_snapshot || "No resume snapshot available."}
                        </pre>
                      </div>

                      {/* Frozen Cover Letter Snapshot */}
                      <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-zinc-900 flex items-center gap-1.5">
                            <FileText size={14} className="text-zinc-600" />
                            Submitted Cover Letter Snapshot
                          </span>
                          <button
                            onClick={() => {
                              if (submittedMaterials?.submitted_cover_letter_snapshot) {
                                navigator.clipboard.writeText(submittedMaterials.submitted_cover_letter_snapshot);
                                toast.success("Frozen cover letter copied to clipboard");
                              }
                            }}
                            className="text-[11px] text-indigo-600 hover:underline font-semibold"
                          >
                            Copy Text
                          </button>
                        </div>
                        <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg text-xs text-zinc-800 leading-relaxed max-h-56 overflow-y-auto whitespace-pre-wrap">
                          {submittedMaterials?.submitted_cover_letter_snapshot ||
                            "No cover letter snapshot available."}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: TIMELINE */}
              {activeDrawerTab === "timeline" && (
                <div className="space-y-4">
                  <h4 className="font-bold text-zinc-900 text-sm">Status Transition Timeline</h4>
                  {isLoadingHistory ? (
                    <div className="p-8 text-center text-zinc-400">Loading timeline...</div>
                  ) : history.length === 0 ? (
                    <div className="p-6 text-center text-zinc-400 bg-zinc-50 rounded-xl">
                      No status transitions recorded yet.
                    </div>
                  ) : (
                    <div className="relative pl-6 border-l-2 border-zinc-200 space-y-4">
                      {history.map((h) => (
                        <div key={h.id} className="relative">
                          <div className="absolute -left-[31px] top-0.5 w-3 h-3 rounded-full bg-indigo-600 border-2 border-white" />
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-zinc-900 text-xs capitalize">
                              {h.status}
                            </span>
                            <span className="text-[10px] text-zinc-400">
                              {new Date(h.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-xs text-zinc-600 mt-0.5">{h.notes}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: OUTCOME & OFFER */}
              {activeDrawerTab === "outcome" && (
                <div className="space-y-4">
                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1">Final Outcome</label>
                    <select
                      value={drawerOutcome}
                      onChange={(e) => setDrawerOutcome(e.target.value)}
                      className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                    >
                      <option value="">Pending / In Progress</option>
                      <option value="Offer Received">Offer Received</option>
                      <option value="Rejected">Rejected</option>
                      <option value="Withdrawn">Withdrawn</option>
                      <option value="Position Closed">Position Closed</option>
                    </select>
                  </div>

                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1">
                      Offer Compensation / Package (if applicable)
                    </label>
                    <input
                      type="text"
                      value={drawerCompensation}
                      onChange={(e) => setDrawerCompensation(e.target.value)}
                      placeholder="e.g. $185,000 Base + $40k Equity + $15k Sign-on"
                      className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                    />
                  </div>

                  <div>
                    <label className="font-semibold text-zinc-700 block mb-1">Outcome Reflections & Feedback</label>
                    <textarea
                      value={drawerOutcomeNotes}
                      onChange={(e) => setDrawerOutcomeNotes(e.target.value)}
                      rows={3}
                      placeholder="Lessons learned, feedback given by recruiter, reason for withdrawal..."
                      className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-xs bg-white"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between">
              <button
                onClick={() => setSelectedApp(null)}
                className="px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-200 rounded-lg transition-colors"
              >
                Close
              </button>
              <button
                disabled={isSavingCrm}
                onClick={handleSaveCrmDetails}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-zinc-900 hover:bg-zinc-800 rounded-lg shadow-sm transition-colors disabled:opacity-50"
              >
                <Check size={14} />
                {isSavingCrm ? "Saving Changes..." : "Save CRM Updates"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
