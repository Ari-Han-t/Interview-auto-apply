"use client";

import { useState } from "react";

export default function Login() {
  const [email, setEmail] = useState("test@example.com");
  const [password, setPassword] = useState("password");
  const [status, setStatus] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    setStatus("Logging in...");
    
    try {
      const res = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
        credentials: "include", // Essential to receive the HttpOnly Set-Cookie
      });

      if (res.ok) {
        setStatus("Login successful! Redirecting...");
        window.location.href = "/profile";
      } else {
        const errorData = await res.json();
        setStatus(`Error: ${errorData.detail}`);
      }
    } catch (err) {
      setStatus("Network error");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50">
      <div className="bg-white p-8 rounded-xl border border-zinc-200 shadow-sm w-96">
        <h1 className="text-xl font-bold mb-4">Login</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-200 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-200 rounded-md"
            />
          </div>
          <button type="submit" className="w-full bg-black text-white rounded-md py-2 font-medium hover:bg-zinc-800 transition-colors">
            Sign In
          </button>
        </form>
        {status && <p className="mt-4 text-sm text-center text-zinc-600">{status}</p>}
      </div>
    </div>
  );
}
