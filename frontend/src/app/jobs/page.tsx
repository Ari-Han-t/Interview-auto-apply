"use client";

import { useState } from "react";

// Mock data for Milestone 2
const MOCK_JOBS = [
  { id: 1, company: "Stripe", role: "Software Engineering Intern", match: 92, status: "Analyzed", deadline: "2026-11-01", location: "San Francisco, CA" },
  { id: 2, company: "OpenAI", role: "AI Research Intern", match: 85, status: "Analyzed", deadline: "2026-10-15", location: "San Francisco, CA" },
  { id: 3, company: "Vercel", role: "Full Stack Intern", match: 45, status: "Discovered", deadline: "2026-12-01", location: "Remote" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState(MOCK_JOBS);
  const [isDiscovering, setIsDiscovering] = useState(false);

  const handleDiscover = () => {
    setIsDiscovering(true);
    // Simulate API call
    setTimeout(() => {
      setIsDiscovering(false);
      alert("Job Discovery triggered via background Celery task!");
    }, 1500);
  };

  const handleAnalyze = (id: number) => {
    setJobs(jobs.map(job => 
      job.id === id ? { ...job, match: Math.floor(Math.random() * (95 - 60 + 1)) + 60, status: "Analyzed" } : job
    ));
    alert(`Triggered AI Analysis for Job #${id}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Job Discovery</h1>
        <button 
          onClick={handleDiscover}
          disabled={isDiscovering}
          className="bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isDiscovering ? "Discovering..." : "Run Job Discovery (YC)"}
        </button>
      </div>
      
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 text-gray-700 text-xs uppercase">
            <tr>
              <th className="px-6 py-3">Company</th>
              <th className="px-6 py-3">Role</th>
              <th className="px-6 py-3">Location</th>
              <th className="px-6 py-3">Match %</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {jobs.map((job) => (
              <tr key={job.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 font-medium text-gray-900">{job.company}</td>
                <td className="px-6 py-4">{job.role}</td>
                <td className="px-6 py-4">{job.location}</td>
                <td className="px-6 py-4">
                  {job.status === "Analyzed" ? (
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${job.match > 80 ? 'bg-green-500' : job.match > 60 ? 'bg-yellow-500' : 'bg-red-500'}`} 
                          style={{ width: `${job.match}%` }}
                        ></div>
                      </div>
                      <span className="font-semibold text-gray-900">{job.match}%</span>
                    </div>
                  ) : (
                    <span className="text-gray-400 italic">Pending</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    job.status === "Analyzed" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"
                  }`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button 
                    onClick={() => handleAnalyze(job.id)}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Analyze
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
