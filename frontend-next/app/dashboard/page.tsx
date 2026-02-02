"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import {
  apiJobsList,
  apiJobGet,
  apiJobUpload,
  apiJobPreview,
  apiJobReport,
  apiJobDownload,
  apiJobRetry,
  clearToken,
} from "@/lib/api";

export default function DashboardPage() {
  const { token, isReady, setToken } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState<Array<{ id: string; status: string; filename_original: string; created_at: string; error_message?: string }>>([]);
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState("");
  const [polling, setPolling] = useState(false);

  const loadJobs = useCallback(async () => {
    try {
      const data = await apiJobsList({ limit: 20 });
      setJobs(data.jobs);
    } catch {
      setJobs([]);
    }
  }, []);

  useEffect(() => {
    if (!isReady) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    loadJobs();
  }, [isReady, token, router, loadJobs]);

  useEffect(() => {
    if (!currentJobId || !polling) return;
    const t = setInterval(async () => {
      try {
        const job = await apiJobGet(currentJobId);
        setCurrentStatus(job.status);
        if (job.status === "done" || job.status === "failed") {
          setPolling(false);
          setCurrentJobId(null);
          loadJobs();
        }
      } catch {
        setPolling(false);
        setCurrentJobId(null);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [currentJobId, polling, loadJobs]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError("");
    setUploading(true);
    try {
      const data = await apiJobUpload(file);
      setCurrentJobId(data.id);
      setCurrentStatus(data.status);
      setPolling(true);
      loadJobs();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Erro no upload");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  function handleLogout() {
    clearToken();
    setToken(null);
    router.replace("/login");
  }

  function statusClass(s: string) {
    if (s === "queued") return "statusBadge statusQueued";
    if (s === "processing") return "statusBadge statusProcessing";
    if (s === "done") return "statusBadge statusDone";
    if (s === "failed") return "statusBadge statusFailed";
    return "statusBadge statusQueued";
  }

  if (!isReady || !token) {
    return (
      <div className="container">
        <p>Carregando...</p>
      </div>
    );
  }

  return (
    <div className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1 style={{ margin: 0 }}>FlowBase</h1>
        <button type="button" className="btn btnSecondary" onClick={handleLogout}>
          Sair
        </button>
      </div>
      <p style={{ color: "#8b949e", marginBottom: "1.5rem" }}>
        Envie uma planilha XLSX ou CSV para converter ao formato GoHighLevel.
      </p>

      <div className="card">
        <div
          className="uploadZone"
          onClick={() => document.getElementById("fileInput")?.click()}
        >
          <input
            id="fileInput"
            type="file"
            accept=".xlsx,.csv"
            onChange={handleUpload}
            style={{ display: "none" }}
            disabled={uploading}
          />
          <p style={{ margin: 0 }}>
            <strong>Clique aqui</strong> ou arraste um arquivo (.xlsx ou .csv, máx. 10 MB)
          </p>
        </div>
        {uploadError && <p className="error">{uploadError}</p>}
        {currentJobId && polling && (
          <p style={{ marginTop: "1rem", color: "#8b949e" }}>
            Job em andamento: {currentStatus}
          </p>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Seus jobs</h3>
        {jobs.length === 0 ? (
          <p style={{ color: "#8b949e" }}>Nenhum job ainda.</p>
        ) : (
          jobs.map((j) => (
            <div key={j.id} className="jobItem">
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {j.filename_original}
                </div>
                <div style={{ fontSize: "0.85rem", color: "#8b949e" }}>
                  {new Date(j.created_at).toLocaleString("pt-BR")}
                </div>
              </div>
              <span className={statusClass(j.status)}>{j.status}</span>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                {j.status === "done" && (
                  <>
                    <button
                      type="button"
                      className="btn btnSecondary"
                      onClick={async () => {
                        try {
                          const data = await apiJobPreview(j.id);
                          alert(JSON.stringify(data, null, 2));
                        } catch (e) {
                          alert(String(e));
                        }
                      }}
                    >
                      Preview
                    </button>
                    <button
                      type="button"
                      className="btn btnSecondary"
                      onClick={async () => {
                        try {
                          const data = await apiJobReport(j.id);
                          alert(JSON.stringify(data, null, 2));
                        } catch (e) {
                          alert(String(e));
                        }
                      }}
                    >
                      Report
                    </button>
                    <button
                      type="button"
                      className="btn btnSecondary"
                      onClick={() => apiJobDownload(j.id)}
                    >
                      Baixar CSV
                    </button>
                  </>
                )}
                {j.status === "failed" && (
                  <button
                    type="button"
                    className="btn btnSecondary"
                    onClick={async () => {
                      try {
                        await apiJobRetry(j.id);
                        loadJobs();
                      } catch (e) {
                        alert(String(e));
                      }
                    }}
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
