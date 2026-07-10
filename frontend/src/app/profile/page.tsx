"use client";

import { useState, useEffect } from "react";
import { UploadCloud, FileText, MoreVertical, Trash2, Copy, Download, RefreshCw, Sparkles } from "lucide-react";

export default function ResumeManager() {
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);

  const [resumes, setResumes] = useState<any[]>([]);
  
  useEffect(() => {
    fetchResumes();
  }, []);

  const fetchResumes = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/resume/versions", {
        credentials: "include"
      });
      if (res.ok) {
        const data = await res.json();
        const mapped = data.map((r: any) => ({
          id: r.id,
          name: r.name,
          type: r.file_type,
          date: new Date(r.created_at).toLocaleDateString(),
          size: "Uploaded",
          tags: ["Master"]
        }));
        setResumes(mapped);
      } else if (res.status === 401) {
        window.location.href = "/login";
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    if (!file.name.endsWith('.tex') && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      setUploadStatus("Unsupported file type.");
      return;
    }

    setUploadStatus("Uploading...");
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/v1/resume/upload", {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      
      if (res.ok) {
        setUploadStatus("Resume uploaded securely.");
        setResumes([{ id: Date.now(), name: file.name, type: file.name.split('.').pop() || 'unknown', date: "Just now", size: (file.size/1024).toFixed(1) + " KB", tags: ["Master"] }, ...resumes]);
      } else {
        setUploadStatus("Failed to upload.");
      }
    } catch (e) {
      setUploadStatus("Network error.");
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
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Resume Manager</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage, tailor, and version your master resumes.</p>
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
        <h3 className="text-sm font-medium text-zinc-900">Upload new resume</h3>
        <p className="text-xs text-zinc-500 mt-1 mb-4">Drag and drop PDF, DOCX, or LaTeX files</p>
        
        <input 
          type="file" 
          id="resume-upload"
          className="hidden" 
          accept=".pdf,.docx,.tex"
          onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])}
        />
        <label 
          htmlFor="resume-upload" 
          className="cursor-pointer px-4 py-2 bg-white border border-zinc-200 rounded-md text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 transition-colors"
        >
          Select File
        </label>
        {uploadStatus && (
          <p className="absolute bottom-4 text-xs font-medium text-indigo-600">{uploadStatus}</p>
        )}
      </div>

      {/* Resume List */}
      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
          <h3 className="text-sm font-semibold text-zinc-900">Your Resumes</h3>
          <span className="text-xs font-medium px-2 py-1 bg-zinc-100 text-zinc-600 rounded-md">{resumes.length} versions</span>
        </div>
        
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
                    {resume.type === 'latex' && <span className="text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 uppercase">LaTeX</span>}
                  </h4>
                  <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
                    <span>{resume.date}</span>
                    <span>&bull;</span>
                    <span>{resume.size}</span>
                    <span>&bull;</span>
                    <div className="flex gap-1">
                      {resume.tags.map(tag => (
                        <span key={tag} className="px-1.5 py-0.5 bg-zinc-100 rounded text-zinc-600">{tag}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors" title="Tailor">
                  <Sparkles size={16} />
                </button>
                <button className="p-1.5 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded-md transition-colors" title="Download">
                  <Download size={16} />
                </button>
                <button className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors" title="Delete">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
