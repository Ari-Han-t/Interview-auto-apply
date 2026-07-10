"use client";

import { useState } from "react";

// Mock data for Milestone 4
const MOCK_APPS = [
  { id: 1, company: "Stripe", role: "Software Engineering Intern", status: "generated", next_action: "Ready to Apply" },
  { id: 2, company: "OpenAI", role: "AI Research Intern", status: "intervention_required", next_action: "Solve CAPTCHA", screenshot: "https://placehold.co/600x400/png?text=CAPTCHA+Screenshot" },
  { id: 3, company: "Vercel", role: "Full Stack Intern", status: "applied", next_action: "Wait for response" },
];

export default function ApplicationsPage() {
  const [apps, setApps] = useState(MOCK_APPS);
  const [selectedApp, setSelectedApp] = useState<any>(null);

  const handleSubmit = (id: number) => {
    setApps(apps.map(app => app.id === id ? { ...app, status: "applying", next_action: "Running automation..." } : app));
    // Simulate finding a Captcha
    setTimeout(() => {
      setApps(apps.map(app => app.id === id ? { ...app, status: "intervention_required", next_action: "Solve CAPTCHA", screenshot: "https://placehold.co/600x400/png?text=CAPTCHA+Screenshot" } : app));
    }, 2000);
  };

  const handleResume = (id: number) => {
    setApps(apps.map(app => app.id === id ? { ...app, status: "applying", next_action: "Resuming automation..." } : app));
    setSelectedApp(null);
    setTimeout(() => {
      setApps(apps.map(app => app.id === id ? { ...app, status: "applied", next_action: "Wait for response" } : app));
    }, 2000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Application Tracker</h1>
      
      {selectedApp && selectedApp.status === "intervention_required" && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-lg font-bold text-red-700 mb-2">User Intervention Required!</h2>
          <p className="text-red-600 mb-4">The automation bot encountered a CAPTCHA while applying to <strong>{selectedApp.company}</strong>. Please solve it below.</p>
          
          <div className="bg-white p-4 border rounded mb-4">
            {/* Real app would use an iframe to the browser session via websockets/VNC */}
            <img src={selectedApp.screenshot} alt="CAPTCHA" className="mx-auto rounded border" />
          </div>

          <div className="flex gap-4">
            <button 
              onClick={() => handleResume(selectedApp.id)}
              className="bg-green-600 text-white px-4 py-2 rounded font-medium hover:bg-green-700"
            >
              I solved it, Resume Automation
            </button>
            <button 
              onClick={() => setSelectedApp(null)}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded font-medium hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 text-gray-700 text-xs uppercase">
            <tr>
              <th className="px-6 py-3">Company</th>
              <th className="px-6 py-3">Role</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Next Action</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {apps.map((app) => (
              <tr key={app.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 font-medium text-gray-900">{app.company}</td>
                <td className="px-6 py-4">{app.role}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    app.status === "intervention_required" ? "bg-red-100 text-red-800" :
                    app.status === "applied" ? "bg-green-100 text-green-800" :
                    app.status === "applying" ? "bg-yellow-100 text-yellow-800" :
                    "bg-blue-100 text-blue-800"
                  }`}>
                    {app.status}
                  </span>
                </td>
                <td className="px-6 py-4 font-medium text-gray-800">{app.next_action}</td>
                <td className="px-6 py-4 text-right">
                  {app.status === "generated" && (
                    <button 
                      onClick={() => handleSubmit(app.id)}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Submit Application
                    </button>
                  )}
                  {app.status === "intervention_required" && (
                    <button 
                      onClick={() => setSelectedApp(app)}
                      className="text-red-600 hover:text-red-800 font-medium underline"
                    >
                      Solve Issue
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
