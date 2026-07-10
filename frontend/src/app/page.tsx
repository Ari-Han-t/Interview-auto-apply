"use client";

import { useEffect, useState } from "react";

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    // Simulate API fetch from /api/v1/analytics/overview
    setTimeout(() => {
      setAnalytics({
        total_applications: 42,
        response_rate: 24.5,
        interview_rate: 12.0,
        ab_testing: [
          { keyword: "FastAPI", usage_count: 12, success_rate: 85 },
          { keyword: "React", usage_count: 24, success_rate: 60 },
          { keyword: "Docker", usage_count: 8, success_rate: 90 },
          { keyword: "Kubernetes", usage_count: 5, success_rate: 40 },
        ]
      });
    }, 500);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard & Analytics</h1>
      
      {!analytics ? (
        <div className="text-gray-500">Loading analytics...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-gray-500 text-sm font-medium">Total Applications</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">{analytics.total_applications}</p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-gray-500 text-sm font-medium">Response Rate</h3>
              <p className="text-3xl font-bold text-green-600 mt-2">{analytics.response_rate}%</p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-gray-500 text-sm font-medium">Interview Conversion</h3>
              <p className="text-3xl font-bold text-blue-600 mt-2">{analytics.interview_rate}%</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold border-b pb-2 mb-4">A/B Testing: Keyword Performance</h2>
            <p className="text-sm text-gray-500 mb-6">Tracking which LLM-generated keywords result in the highest interview rates.</p>
            
            <div className="space-y-4">
              {analytics.ab_testing.map((item: any, index: number) => (
                <div key={index}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{item.keyword} (Used {item.usage_count} times)</span>
                    <span className="font-semibold text-gray-900">{item.success_rate}% Success</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div 
                      className={`h-2.5 rounded-full ${item.success_rate > 70 ? 'bg-green-600' : item.success_rate > 50 ? 'bg-blue-600' : 'bg-red-500'}`} 
                      style={{ width: `${item.success_rate}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
