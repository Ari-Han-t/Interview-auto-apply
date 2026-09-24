"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiPost } from "@/lib/api";
import { toast } from "react-hot-toast";
import { Search, MapPin, Briefcase, RefreshCw, SlidersHorizontal, Sparkles, X, Check, Globe } from "lucide-react";

interface JobData {
  id: number;
  title: string;
  company: string;
  url: string | null;
  location: string | null;
  status: string;
  salary_range: string | null;
  is_remote: boolean;
  tech_stack_json: string[] | null;
  company_logo_url: string | null;
  source: string | null;
  eligible?: boolean;
  rejection_reason?: string | null;
  requirements_json: {
    match_percentage?: number;
    strengths?: string[];
    weaknesses?: string[];
    missing_skills?: string[];
    reasoning?: string;
  } | null;
  created_at: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobData[]>([]);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showOnlyEligible, setShowOnlyEligible] = useState(true);
  const [showScraperModal, setShowScraperModal] = useState(false);

  // Scraper Form State
  const [keywords, setKeywords] = useState("Software Engineer Intern");
  const [location, setLocation] = useState("Remote");
  const [jobType, setJobType] = useState("internship"); // internship, fulltime, both
  const [source, setSource] = useState("all");
  const [onlySuited, setOnlySuited] = useState(true);
  const [isAutoFilling, setIsAutoFilling] = useState(false);

  const router = useRouter();

  const fetchJobs = async () => {
    try {
      const data = await apiFetch<JobData[]>("/api/v1/jobs/");
      setJobs(data);
    } catch (err: any) {
      if (err.message !== "Unauthorized") {
        toast.error("Failed to load jobs");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleAutoFillFromResume = async () => {
    setIsAutoFilling(true);
    try {
      const profile = await apiFetch<any>("/api/v1/profile/");
      if (profile) {
        const userProf = profile.user_profile || {};
        const userPref = profile.preferences || {};
        const skills = (profile.skills || []).map((s: any) => s.skill?.name || s.name).filter(Boolean);
        
        let derivedKeywords = "";
        if (userPref.preferred_roles && userPref.preferred_roles.length > 0) {
          derivedKeywords = userPref.preferred_roles.join(", ");
        } else if (skills.length > 0) {
          derivedKeywords = `${skills.slice(0, 3).join(" ") } Developer`;
        } else {
          derivedKeywords = "Software Engineer Intern";
        }

        let derivedLocation = userProf.current_location || "Remote";
        if (userProf.preferred_locations && userProf.preferred_locations.length > 0) {
          derivedLocation = userProf.preferred_locations[0];
        }

        let derivedJobType = "internship";
        if (userPref.preferred_internship && !userPref.preferred_fulltime) {
          derivedJobType = "internship";
        } else if (userPref.preferred_fulltime && !userPref.preferred_internship) {
          derivedJobType = "fulltime";
        } else {
          derivedJobType = "both";
        }

        setKeywords(derivedKeywords);
        setLocation(derivedLocation);
        setJobType(derivedJobType);
        toast.success("Scraper form auto-filled from your resume & profile!");
      }
    } catch (err: any) {
      toast.error("Could not fetch profile to auto-fill.");
    } finally {
      setIsAutoFilling(false);
    }
  };

  const handleDiscover = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsDiscovering(true);
    setShowScraperModal(false);
    const toastId = toast.loading(`Scraping suited jobs (${jobType.toUpperCase()}) from ${source.toUpperCase()}...`);
    try {
      await apiPost("/api/v1/jobs/discover", {
        source,
        keywords,
        location,
        job_type: jobType,
        only_suited: onlySuited
      });
      toast.success("Resume-suited job discovery started! Checking match criteria...", { id: toastId });
      setTimeout(() => fetchJobs(), 6000);
    } catch (err: any) {
      toast.error(err.message || "Discovery failed", { id: toastId });
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleAnalyzeAndApply = async (id: number) => {
    try {
      const data = await apiPost<{ application_id: number; status: string }>(`/api/v1/applications/initialize/${id}`);
      router.push(`/jobs/${id}?application_id=${data.application_id}&analyze=true`);
    } catch (err: any) {
      toast.error(err.message || "Initialization failed");
    }
  };

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (job.location || "").toLowerCase().includes(searchTerm.toLowerCase());
    
    if (showOnlyEligible) {
      return matchesSearch && job.eligible !== false;
    }
    return matchesSearch;
  });

  const getSourceStyle = (source: string) => {
    switch (source?.toLowerCase()) {
      case "yc":
        return "bg-orange-50 text-orange-700 border-orange-200";
      case "linkedin":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "internshala":
        return "bg-cyan-50 text-cyan-700 border-cyan-200";
      case "greenhouse":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "lever":
        return "bg-purple-50 text-purple-700 border-purple-200";
      default:
        return "bg-zinc-50 text-zinc-700 border-zinc-200";
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Job Feed</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-zinc-200 p-5 shadow-sm animate-pulse space-y-4">
              <div className="h-4 bg-zinc-200 rounded w-3/4"></div>
              <div className="h-3 bg-zinc-100 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 tracking-tight">Job & Internship Feed</h1>
          <p className="text-sm text-zinc-500 mt-1">{jobs.length} jobs & internships scraped</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchJobs}
            className="p-2.5 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors border border-zinc-200 bg-white"
            title="Refresh feed"
          >
            <RefreshCw size={16} />
          </button>
          
          <button
            onClick={() => setShowScraperModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm flex items-center gap-2"
          >
            <SlidersHorizontal size={16} />
            Configure & Scrape
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
        <input
          type="text"
          placeholder="Search jobs by title, company, or location..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 border border-zinc-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white shadow-sm"
        />
      </div>

      {/* Eligibility Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-zinc-50 border border-zinc-200/60 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2.5">
          <input
            type="checkbox"
            id="showOnlyEligible"
            checked={showOnlyEligible}
            onChange={(e) => setShowOnlyEligible(e.target.checked)}
            className="w-4 h-4 text-indigo-600 border-zinc-300 rounded focus:ring-indigo-500 cursor-pointer"
          />
          <label htmlFor="showOnlyEligible" className="text-sm font-semibold text-zinc-700 select-none cursor-pointer">
            Show Only Resume-Suited Opportunities
          </label>
        </div>
        <span className="text-xs text-zinc-500 font-medium">
          Showing {filteredJobs.length} of {jobs.length} roles
        </span>
      </div>

      {/* Job Cards Grid */}
      {filteredJobs.length === 0 ? (
        <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center shadow-sm">
          <Briefcase size={40} className="mx-auto text-zinc-300 mb-4" />
          <p className="text-zinc-900 font-semibold text-base">No suited opportunities found</p>
          <p className="text-sm text-zinc-500 mt-1">Configure your scraper preferences or auto-fill criteria from your resume to start scraping tailored internships.</p>
          <button
            onClick={() => setShowScraperModal(true)}
            className="mt-4 inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            <Sparkles size={16} />
            Configure Web Scraper
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredJobs.map((job) => {
            const matchScore = job.requirements_json?.match_percentage;

            return (
              <div
                key={job.id}
                className="bg-white rounded-xl border border-zinc-200 p-5 shadow-sm hover:shadow-md transition-all hover:border-zinc-300 flex flex-col justify-between min-h-[260px] relative overflow-hidden"
              >
                {/* Source Badge top right */}
                <div className="absolute top-4 right-4 flex items-center gap-1.5">
                  {job.eligible === false && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200">
                      Not Suited
                    </span>
                  )}
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase tracking-wider ${getSourceStyle(job.source || "")}`}>
                    {job.source || "Web"}
                  </span>
                </div>

                <div className="space-y-3">
                  <div className="flex items-start gap-3 pr-24">
                    <div className="w-10 h-10 rounded-lg bg-zinc-50 border border-zinc-200 flex items-center justify-center font-bold text-zinc-600 text-sm flex-shrink-0">
                      {job.company_logo_url ? (
                        <img src={job.company_logo_url} alt={job.company} className="w-full h-full object-contain rounded-lg" />
                      ) : (
                        job.company.substring(0, 2).toUpperCase()
                      )}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-zinc-900 line-clamp-1">{job.title}</h3>
                      <p className="text-xs text-zinc-500 mt-0.5 font-medium">{job.company}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 text-[11px] text-zinc-500">
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin size={12} className="text-zinc-400" />
                        {job.location}
                      </span>
                    )}
                  </div>

                  {job.tech_stack_json && job.tech_stack_json.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {job.tech_stack_json.slice(0, 4).map((tech, idx) => (
                        <span key={idx} className="bg-zinc-100 text-zinc-600 text-[10px] font-medium px-2 py-0.5 rounded">
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Bottom Actions */}
                <div className="pt-4 border-t border-zinc-100 flex items-center justify-between mt-4">
                  {matchScore !== undefined ? (
                    <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
                      {matchScore}% Match
                    </span>
                  ) : (
                    <span className="text-xs text-zinc-400 font-medium">Not analyzed</span>
                  )}

                  <button
                    onClick={() => handleAnalyzeAndApply(job.id)}
                    className="text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
                  >
                    View & Apply
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Scraper Configuration Form Modal */}
      {showScraperModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-zinc-200 max-w-lg w-full p-6 shadow-xl space-y-5 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="text-indigo-600" size={20} />
                <h2 className="text-lg font-bold text-zinc-900">Web Scraper Configuration</h2>
              </div>
              <button
                onClick={() => setShowScraperModal(false)}
                className="text-zinc-400 hover:text-zinc-600 p-1 rounded-lg hover:bg-zinc-100 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Auto fill trigger */}
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-3.5 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-indigo-900">Resume-Powered Setup</p>
                <p className="text-[11px] text-indigo-700 mt-0.5">Auto-populate search parameters directly from your parsed resume & skills.</p>
              </div>
              <button
                type="button"
                onClick={handleAutoFillFromResume}
                disabled={isAutoFilling}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm flex-shrink-0"
              >
                <Sparkles size={12} />
                {isAutoFilling ? "Reading..." : "Auto-fill"}
              </button>
            </div>

            <form onSubmit={handleDiscover} className="space-y-4 text-left">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Target Roles / Keywords</label>
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="e.g. Software Engineer Intern, Frontend, Python"
                  className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Location Preference</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Remote, India, San Francisco"
                  className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Opportunity Type</label>
                  <select
                    value={jobType}
                    onChange={(e) => setJobType(e.target.value)}
                    className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white"
                  >
                    <option value="internship">Internships Only</option>
                    <option value="fulltime">Full-time Only</option>
                    <option value="both">Both (Internship & Full-time)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Scraper Source</label>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    className="w-full px-3 py-2 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 bg-white"
                  >
                    <option value="all">All Supported Platforms</option>
                    <option value="internshala">Internshala</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="yc">YC Startups</option>
                    <option value="greenhouse">Greenhouse Boards</option>
                    <option value="lever">Lever Boards</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 border-t border-zinc-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="onlySuitedToggle"
                    checked={onlySuited}
                    onChange={(e) => setOnlySuited(e.target.checked)}
                    className="w-4 h-4 text-indigo-600 border-zinc-300 rounded focus:ring-indigo-500 cursor-pointer"
                  />
                  <label htmlFor="onlySuitedToggle" className="text-xs font-semibold text-zinc-700 select-none cursor-pointer">
                    Only Scrape & Store Suited Opportunities
                  </label>
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowScraperModal(false)}
                  className="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-lg text-xs font-semibold hover:bg-zinc-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDiscovering}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <Globe size={14} />
                  {isDiscovering ? "Scraping..." : "Start Suited Scraper"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
