"use client";

import { useEffect, useState } from "react";
import { apiFetch, apiPut, apiDelete, API_BASE } from "@/lib/api";
import { toast } from "react-hot-toast";
import {
  FileText,
  Download,
  Trash2,
  Edit3,
  Save,
  Eye,
  Mail,
  ArrowLeft,
  RefreshCw,
  X,
  Copy,
  Check,
  CheckCheck,
  History,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

interface CoverLetter {
  id: number;
  job_id: number;
  application_id?: number | null;
  company: string;
  role: string;
  content: string;
  format: string;
  style: string;
  version_number: number;
  is_approved: boolean;
  approved_at?: string | null;
  candidate_motivation?: string | null;
  created_at: string;
  updated_at?: string;
}

export default function CoverLettersPage() {
  const [letters, setLetters] = useState<CoverLetter[]>([]);
  const [selectedLetter, setSelectedLetter] = useState<CoverLetter | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [copied, setCopied] = useState(false);

  const fetchLetters = async () => {
    try {
      const data = await apiFetch<CoverLetter[]>("/api/v1/cover_letters/");
      setLetters(data);
      if (selectedLetter) {
        const updated = data.find((l) => l.id === selectedLetter.id);
        if (updated) setSelectedLetter(updated);
      }
    } catch (e: any) {
      if (e.message !== "Unauthorized") {
        toast.error("Failed to load cover letters");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLetters();
  }, []);

  const handleSelect = (letter: CoverLetter) => {
    setSelectedLetter(letter);
    setEditContent(letter.content);
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!selectedLetter) return;
    try {
      await apiPut(`/api/v1/cover_letters/${selectedLetter.id}`, { content: editContent });
      toast.success("Cover letter updated successfully");
      setIsEditing(false);
      fetchLetters();
    } catch (e: any) {
      toast.error(e.message || "Failed to update cover letter");
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this cover letter?")) return;
    try {
      await apiDelete(`/api/v1/cover_letters/${id}`);
      toast.success("Cover letter deleted");
      if (selectedLetter?.id === id) {
        setSelectedLetter(null);
      }
      fetchLetters();
    } catch (e: any) {
      toast.error(e.message || "Failed to delete cover letter");
    }
  };

  const handleCopy = () => {
    if (!selectedLetter) return;
    navigator.clipboard.writeText(selectedLetter.content);
    setCopied(true);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = (id: number, format: "pdf" | "md" | "txt") => {
    window.open(`${API_BASE}/api/v1/cover_letters/download/${id}?format=${format}`, "_blank");
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Cover Letters</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm animate-pulse">
              <div className="h-4 bg-zinc-200 rounded w-3/4 mb-4"></div>
              <div className="h-3 bg-zinc-200 rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-zinc-200 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Cover Letters</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Personalized, truth-preserving cover letters linked to job opportunities.
          </p>
        </div>
        <button
          onClick={fetchLetters}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-zinc-200 hover:bg-zinc-50 rounded-lg text-xs font-medium text-zinc-700 transition"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 items-start">
        {/* List Panel */}
        <div className={`space-y-4 ${selectedLetter ? "lg:col-span-1 hidden lg:block" : "lg:col-span-3"}`}>
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              All Letters ({letters.length})
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-4">
            {letters.map((letter) => (
              <div
                key={letter.id}
                onClick={() => handleSelect(letter)}
                className={`p-4 bg-white border rounded-xl shadow-xs cursor-pointer hover:border-zinc-300 transition-all ${
                  selectedLetter?.id === letter.id ? "ring-2 ring-indigo-500/20 border-indigo-400" : "border-zinc-200"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-indigo-50 border border-indigo-100 rounded-lg flex items-center justify-center text-indigo-600">
                      <Mail size={16} />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <h3 className="text-sm font-semibold text-zinc-900">{letter.company}</h3>
                        <span className="px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600 text-[10px] font-bold">
                          v{letter.version_number || 1}
                        </span>
                        {letter.is_approved && (
                          <span className="px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold">
                            ✓
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 mt-0.5">{letter.role}</p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(letter.id, e)}
                    className="p-1 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                <div className="mt-3 flex items-center justify-between text-[11px] text-zinc-400">
                  <span className="px-2 py-0.5 rounded bg-zinc-100 text-zinc-700 font-semibold uppercase text-[10px]">
                    {letter.style || "concise"}
                  </span>
                  <span>{new Date(letter.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}

            {letters.length === 0 && (
              <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center shadow-xs lg:col-span-3">
                <Mail size={40} className="mx-auto text-zinc-300 mb-4" />
                <p className="text-zinc-500 font-medium">No cover letters generated yet</p>
                <p className="text-sm text-zinc-400 mt-1">
                  Open any job in the Job Feed and generate a tailored cover letter from the Tailoring Room.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* View/Edit Panel */}
        {selectedLetter && (
          <div className="lg:col-span-2 bg-white rounded-xl border border-zinc-200 shadow-sm p-6 flex flex-col min-h-[600px] h-[700px]">
            <div className="flex flex-wrap items-center justify-between border-b border-zinc-150 pb-4 mb-4 gap-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedLetter(null)}
                  className="lg:hidden p-1 text-zinc-400 hover:text-zinc-700 transition-colors"
                >
                  <ArrowLeft size={18} />
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-zinc-900">{selectedLetter.company}</h2>
                    <span className="px-2 py-0.5 rounded bg-zinc-100 text-zinc-700 text-xs font-bold">
                      v{selectedLetter.version_number || 1}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-semibold capitalize">
                      {selectedLetter.style || "concise"} Style
                    </span>
                    {selectedLetter.is_approved && (
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold flex items-center gap-1">
                        <CheckCheck size={12} /> Approved
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500">{selectedLetter.role}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href={`/jobs/${selectedLetter.job_id}`}
                  className="inline-flex items-center gap-1 border border-zinc-200 text-zinc-700 hover:bg-zinc-50 px-2.5 py-1.5 rounded-lg text-xs font-medium transition"
                >
                  <ExternalLink size={12} /> Job Tailoring Room
                </Link>

                <button
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1 border border-zinc-200 text-zinc-700 hover:bg-zinc-50 px-2.5 py-1.5 rounded-lg text-xs font-medium transition"
                >
                  {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>

                {isEditing ? (
                  <>
                    <button
                      onClick={handleSave}
                      className="inline-flex items-center gap-1 bg-zinc-900 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-zinc-800 transition"
                    >
                      <Save size={13} /> Save
                    </button>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="p-1.5 border border-zinc-200 hover:bg-zinc-50 rounded-lg text-zinc-600 transition"
                    >
                      <X size={13} />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="inline-flex items-center gap-1 border border-zinc-200 text-zinc-700 hover:bg-zinc-50 px-2.5 py-1.5 rounded-lg text-xs font-medium transition"
                    >
                      <Edit3 size={12} /> Edit
                    </button>
                    <button
                      onClick={() => handleDownload(selectedLetter.id, "pdf")}
                      className="inline-flex items-center gap-1 bg-indigo-50 border border-indigo-100 text-indigo-700 px-2.5 py-1.5 rounded-lg text-xs font-semibold hover:bg-indigo-100 transition"
                    >
                      <Download size={12} /> PDF
                    </button>
                    <button
                      onClick={() => handleDownload(selectedLetter.id, "md")}
                      className="inline-flex items-center gap-1 border border-zinc-200 text-zinc-700 px-2.5 py-1.5 rounded-lg text-xs font-medium hover:bg-zinc-50 transition"
                    >
                      <Download size={12} /> MD
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0">
              {isEditing ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full h-full p-4 border border-zinc-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-zinc-900 text-xs font-mono leading-relaxed"
                />
              ) : (
                <div className="text-xs text-zinc-700 whitespace-pre-wrap leading-relaxed bg-zinc-50/50 p-6 rounded-xl border border-zinc-150 h-full overflow-y-auto">
                  {selectedLetter.content}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
