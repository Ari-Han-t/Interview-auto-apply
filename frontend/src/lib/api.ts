export function resolveApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    // When running on Render domain (*.onrender.com)
    if (host.includes("onrender.com")) {
      return "https://interview-autoapply-backend.onrender.com";
    }
    // When running on any other remote non-localhost domain
    if (host !== "localhost" && host !== "127.0.0.1") {
      const envUrl = process.env.NEXT_PUBLIC_API_URL;
      if (envUrl && !envUrl.includes("localhost")) {
        return envUrl;
      }
      return "https://interview-autoapply-backend.onrender.com";
    }
  }
  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL;
  return (rawApiUrl && !rawApiUrl.includes("8001")) ? rawApiUrl : "http://localhost:8000";
}

const API_BASE = resolveApiBase();

export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const base = resolveApiBase();
  const url = `${base}${path}`;
  const res = await fetch(url, {
    credentials: "include",
    ...options,
    headers: {
      ...options.headers,
    },
  });

  if (res.status === 401) {
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

export async function apiPost<T = any>(
  path: string,
  body?: any,
  options: RequestInit = {}
): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    headers: body instanceof FormData ? {} : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    ...options,
  });
}

export async function apiDelete<T = any>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" });
}

export async function apiPut<T = any>(path: string, body: any): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export { API_BASE };
