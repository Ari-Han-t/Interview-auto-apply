"use client";

import { useState } from "react";

export default function JobTailoringRoom({ params }: { params: { id: string } }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [resumePreview, setResumePreview] = useState("");
  const [clPreview, setClPreview] = useState("");

  const handleGenerate = () => {
    setIsGenerating(true);
    // Simulate API call to /api/v1/applications/generate/{id}
    setTimeout(() => {
      setResumePreview("# Arihant Gupta\n\n**Target Role**: Software Engineering Intern\n\n## Experience\n- Engineered backend systems perfectly matching JD requirements.\n- Optimized APIs with Python and FastAPI.\n\n## Skills\n- Python, React, Next.js");
      setClPreview("Dear Hiring Manager,\n\nI am writing to express my interest in this position.\nI bring relevant technical skills including Python and React.\n\nSincerely,\nArihant");
      setGenerated(true);
      setIsGenerating(false);
    }, 2000);
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tailoring Room</h1>
          <p className="text-gray-500">Job ID: {params.id}</p>
        </div>
        <button 
          onClick={handleGenerate}
          disabled={isGenerating || generated}
          className="bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isGenerating ? "Generating..." : generated ? "Materials Generated" : "Generate Tailored Application"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
        {/* Job Description Panel */}
        <div className="bg-white rounded-lg shadow-sm border p-6 flex flex-col h-[600px] overflow-y-auto">
          <h2 className="text-lg font-semibold border-b pb-2 mb-4">Job Description</h2>
          <div className="prose text-sm text-gray-700">
            <p><strong>Role:</strong> Software Engineering Intern</p>
            <p><strong>Company:</strong> Tech Corp</p>
            <p className="mt-4">We are looking for a backend intern to help scale our infrastructure.</p>
            <h4 className="mt-4 font-semibold">Requirements:</h4>
            <ul className="list-disc pl-5 mt-2">
              <li className="bg-yellow-100">Strong experience in Python and FastAPI (Matched!)</li>
              <li>Experience with React or Next.js</li>
              <li className="bg-red-100">Familiarity with Kubernetes (Missing)</li>
            </ul>
          </div>
        </div>

        {/* Generated Artifacts Panel */}
        <div className="bg-white rounded-lg shadow-sm border p-6 flex flex-col h-[600px]">
          <h2 className="text-lg font-semibold border-b pb-2 mb-4">Generated Artifacts</h2>
          
          {!generated ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <p>Click "Generate Tailored Application" to create your materials.</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                   <h3 className="font-semibold text-gray-900">Tailored Resume</h3>
                   <button className="text-blue-600 text-sm hover:underline">Download PDF</button>
                </div>
                <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto border">
                  {resumePreview}
                </pre>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                   <h3 className="font-semibold text-gray-900">Cover Letter</h3>
                   <button className="text-blue-600 text-sm hover:underline">Download PDF</button>
                </div>
                <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto border whitespace-pre-wrap">
                  {clPreview}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
