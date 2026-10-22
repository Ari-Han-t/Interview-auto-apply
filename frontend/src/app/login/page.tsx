"use client";

import { useState } from "react";
import { API_BASE, resolveApiBase } from "@/lib/api";
import { Sparkles } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setStatus("");

    try {
      const apiEndpoint = resolveApiBase();
      if (isRegister) {
        // Register first
        const regRes = await fetch(`${apiEndpoint}/api/v1/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        if (!regRes.ok) {
          const err = await regRes.json();
          setStatus(err.detail || "Registration failed");
          setIsLoading(false);
          return;
        }
      }

      // Login
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await fetch(`${apiEndpoint}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
        credentials: "include",
      });

      if (res.ok) {
        window.location.href = "/";
      } else {
        const errorData = await res.json().catch(() => ({ detail: "Login failed" }));
        setStatus(errorData.detail || "Login failed");
      }
    } catch (err: any) {
      console.error("Login request failed:", err);
      setStatus(err?.message ? `Network error (${err.message}) — check backend connectivity` : "Network error — is the backend running?");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-50 to-zinc-100">
      <div className="bg-white p-8 rounded-2xl border border-zinc-200 shadow-lg w-[400px]">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 flex items-center justify-center text-white">
            <Sparkles size={16} />
          </div>
          <span className="font-semibold text-lg tracking-tight text-zinc-900">AutoApply</span>
        </div>

        <h1 className="text-xl font-semibold text-zinc-900 mb-1">
          {isRegister ? "Create Account" : "Welcome Back"}
        </h1>
        <p className="text-sm text-zinc-500 mb-6">
          {isRegister ? "Sign up to start auto-applying." : "Sign in to your dashboard."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1.5">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-zinc-900 text-white rounded-lg py-2.5 font-medium hover:bg-zinc-800 transition-colors shadow-sm disabled:opacity-50"
          >
            {isLoading ? "Please wait..." : isRegister ? "Create Account" : "Sign In"}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={() => { setIsRegister(!isRegister); setStatus(""); }}
            className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            {isRegister ? "Already have an account? Sign in" : "Don't have an account? Register"}
          </button>
        </div>

        {status && (
          <p className="mt-4 text-sm text-center text-red-600 bg-red-50 px-3 py-2 rounded-lg">
            {status}
          </p>
        )}

        {/* Example Demo User */}
        <div className="mt-6 pt-5 border-t border-zinc-100">
          <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-3.5 text-left">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                Example Demo Account
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-200/70 text-zinc-700 font-semibold">
                ID: 34
              </span>
            </div>
            <div className="text-xs font-semibold text-zinc-900">Maya Patel</div>
            <div className="text-[11px] text-zinc-500 mb-2.5">
              Senior Full-Stack & AI Systems Engineer
            </div>
            <button
              type="button"
              onClick={() => {
                setEmail("maya.patel@autoapply.dev");
                setPassword("AutoApply@2026!");
                setStatus("");
                setIsRegister(false);
              }}
              className="w-full py-1.5 px-3 bg-white hover:bg-zinc-100 border border-zinc-200 text-zinc-700 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-2xs cursor-pointer"
            >
              <Sparkles size={13} className="text-indigo-600" />
              Fill Example User Credentials
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
