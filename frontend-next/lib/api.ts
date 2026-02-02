/**
 * Cliente para chamar o backend via proxy Next.js (/api/proxy/...).
 * Inclui Authorization: Bearer <token> quando o token existe.
 */

const PROXY = "/api/proxy";

function getAuthHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("flowbase_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

export async function apiRegister(email: string, password: string) {
  const res = await fetch(`${PROXY}/auth/register`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return data as { access_token: string; token_type: string; user_id: string };
}

export async function apiLogin(email: string, password: string) {
  const res = await fetch(`${PROXY}/auth/login`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return data as { access_token: string; token_type: string; user_id: string };
}

export async function apiJobsList(params?: { limit?: number; offset?: number; status?: string }) {
  const q = new URLSearchParams();
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.offset) q.set("offset", String(params.offset));
  if (params?.status) q.set("status", params.status);
  const query = q.toString();
  const url = query ? `${PROXY}/jobs?${query}` : `${PROXY}/jobs`;
  const res = await fetch(url, { headers: getAuthHeaders(), cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return data as { total: number; jobs: Array<{ id: string; status: string; filename_original: string; created_at: string; error_message?: string }> };
}

export async function apiJobGet(id: string) {
  const res = await fetch(`${PROXY}/jobs/${id}`, { headers: getAuthHeaders(), cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return data;
}

export async function apiJobUpload(file: File) {
  const form = new FormData();
  form.append("file", file);
  const headers: Record<string, string> = {};
  const token = typeof window !== "undefined" ? localStorage.getItem("flowbase_token") : null;
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${PROXY}/jobs`, {
    method: "POST",
    headers,
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return data as { id: string; status: string; filename_original: string; created_at: string };
}

export async function apiJobPreview(id: string) {
  const res = await fetch(`${PROXY}/jobs/${id}/preview`, { headers: getAuthHeaders(), cache: "no-store" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return res.json();
}

export async function apiJobReport(id: string) {
  const res = await fetch(`${PROXY}/jobs/${id}/report`, { headers: getAuthHeaders(), cache: "no-store" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return res.json();
}

/** Retorna a URL do proxy para download; use apiJobDownload(id) para disparar o download com auth. */
export function apiJobDownloadUrl(id: string): string {
  return `${PROXY}/jobs/${id}/download`;
}

/** Faz GET no download com Authorization e dispara o download do CSV no navegador. */
export async function apiJobDownload(id: string, filename?: string) {
  const res = await fetch(apiJobDownloadUrl(id), { headers: getAuthHeaders() });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `ghl_import_${id}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function apiJobRetry(id: string) {
  const res = await fetch(`${PROXY}/jobs/${id}/retry`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Erro ${res.status}`);
  }
  return data;
}

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("flowbase_token", token);
  }
}

export function getToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("flowbase_token");
  }
  return null;
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("flowbase_token");
  }
}
