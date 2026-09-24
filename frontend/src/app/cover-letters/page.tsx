"use client";

import { useEffect, useState } from "react";
import { apiFetch, apiPut, apiDelete, API_BASE } from "@/lib/api";
import { toast } from "react-hot-toast";
import { FileText, Download, Trash2, Edit3, Save, Eye, Mail, ArrowLeft, RefreshCw, X } from "lucide-react";

interface CoverLetter {
  id: number;
  job_id: number;
  company: string;
  role: string;
  content: string;
  format: string;
  created_at: string;
}

export default function CoverLettersPage() {
  const [letters, setLetters] = useState<CoverLetter[]>([]);
  const [selectedLetter, setSelectedLetter] = useState<CoverLetter | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");

  const fetchLetters = async () => {
    try {
      const data = await apiFetch<CoverLetter[]>("/api/v1/cover_letters/");
      setLetters(data);
      if (selectedLetter) {
        // Refresh the selected letter details if open
        const updated = data.find(l => l.id === selectedLetter.id);
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

  const handleDownload = (id: number, format: "pdf" | "md", company: string) => {
    const safeCompany = company.replace(/[^a-z0-9]/gi, '_').toLowerCase();
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
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Cover Letters</h1>
        <p className="text-sm text-zinc-500 mt-1">Manage, edit, and download your generated cover letters.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 items-start">
        {/* List Panel */}
        <div className={`space-y-4 ${selectedLetter ? "lg:col-span-1 hidden lg:block" : "lg:col-span-3"}`}>
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">All Letters ({letters.length})</h2>
            <button onClick={fetchLetters} className="p-1 text-zinc-400 hover:text-zinc-700 transition-colors">
              <RefreshCw size={14} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-4">
            {letters.map((letter) => (
              <div
                key={letter.id}
                onClick={() => handleSelect(letter)}
                className={`p-5 bg-white border rounded-xl shadow-sm cursor-pointer hover:border-zinc-300 transition-all ${
                  selectedLetter?.id === letter.id ? "ring-2 ring-indigo-500/20 border-indigo-400" : "border-zinc-200"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-indigo-50 border border-indigo-100 rounded-lg flex items-center justify-center text-indigo-600">
                      <Mail size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-900">{letter.company}</h3>
                      <p className="text-xs text-zinc-500 mt-0.5">{letter.role}</p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(letter.id, e)}
                    className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="mt-4 flex items-center justify-between text-xs text-zinc-400">
                  <span>{new Date(letter.created_at).toLocaleDateString()}</span>
                  <span className="flex items-center gap-1 text-indigo-600 font-medium">
                    <Eye size={12} /> View
                  </span>
                </div>
              </div>
            ))}

            {letters.length === 0 && (
              <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center shadow-sm lg:col-span-3">
                <Mail size={40} className="mx-auto text-zinc-300 mb-4" />
                <p className="text-zinc-500 font-medium">No cover letters generated yet</p>
                <p className="text-sm text-zinc-400 mt-1">Generate a cover letter for any job card in the Job Feed.</p>
              </div>
            )}
          </div>
        </div>

        {/* View/Edit Panel */}
        {selectedLetter && (
          <div className="lg:col-span-2 bg-white rounded-xl border border-zinc-200 shadow-sm p-6 flex flex-col h-[650px]">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-4 mb-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSelectedLetter(null)}
                  className="lg:hidden p-1 text-zinc-400 hover:text-zinc-700 transition-colors"
                >
                  <ArrowLeft size={18} />
                </button>
                <div>
                  <h2 className="text-base font-semibold text-zinc-900">{selectedLetter.company}</h2>
                  <p className="text-xs text-zinc-500">{selectedLetter.role}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={handleSave}
                      className="inline-flex items-center gap-1.5 bg-zinc-900 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-zinc-800 transition-colors shadow-sm"
                    >
                      <Save size={14} /> Save
                    </button>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="p-1.5 border border-zinc-200 hover:bg-zinc-50 rounded-lg text-zinc-600 transition-colors"
                    >
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="inline-flex items-center gap-1.5 border border-zinc-200 text-zinc-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-zinc-50 transition-colors shadow-sm"
                    >
                      <Edit3 size={14} /> Edit
                    </button>
                    <button
                      onClick={() => handleDownload(selectedLetter.id, "md", selectedLetter.company)}
                      className="inline-flex items-center gap-1.5 border border-zinc-200 text-zinc-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-zinc-50 transition-colors shadow-sm"
                    >
                      <Download size={14} /> MD
                    </button>
                    <button
                      onClick={() => handleDownload(selectedLetter.id, "pdf", selectedLetter.company)}
                      className="inline-flex items-center gap-1.5 bg-indigo-50 border border-indigo-100 text-indigo-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-indigo-100 transition-colors shadow-sm"
                    >
                      <Download size={14} /> PDF
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
                  className="w-full h-full p-4 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 text-sm font-mono leading-relaxed"
                />
              ) : (
                <div className="prose max-w-none text-sm text-zinc-600 whitespace-pre-wrap leading-relaxed font-sans bg-zinc-50/50 p-6 rounded-lg border border-zinc-100 h-full overflow-y-auto">
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
