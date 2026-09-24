"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
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
      if (isRegister) {
        // Register first
        const regRes = await fetch(`${API_BASE}/api/v1/auth/register`, {
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

      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
        credentials: "include",
      });

      if (res.ok) {
        window.location.href = "/";
      } else {
        const errorData = await res.json();
        setStatus(errorData.detail || "Login failed");
      }
    } catch (err) {
      setStatus("Network error — is the backend running?");
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
      </div>
    </div>
  );
}
