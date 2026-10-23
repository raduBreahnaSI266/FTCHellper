"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Download, FileVideo2, LoaderCircle, Play, RotateCw, Trash2, Upload, Video } from "lucide-react";
import { VideoReview } from "@/components/video-review";
import { apiBase, formatBytes, notifyVideosUpdated, VideoUpload } from "@/lib/videos";

const maxUploadBytes = 500 * 1024 * 1024;

export function UploadWorkspace() {
  const [videos, setVideos] = useState<VideoUpload[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [eventName, setEventName] = useState("");
  const [season, setSeason] = useState("2025-2026");
  const [matchNumber, setMatchNumber] = useState("1");
  const [alliance, setAlliance] = useState<"Red" | "Blue">("Blue");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [datasetBusy, setDatasetBusy] = useState(false);
  const [datasetMessage, setDatasetMessage] = useState("");

  async function refreshVideos() {
    try {
      const response = await fetch(`${apiBase}/api/v1/videos`, { cache: "no-store" });
      if (!response.ok) throw new Error("Nu s-a putut contacta API-ul local.");
      setVideos(await response.json() as VideoUpload[]);
      setError("");
    } catch {
      setError("API-ul local nu răspunde. Pornește backendul pe 127.0.0.1:8001.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshVideos();
  }, []);

  useEffect(() => {
    if (!videos.some((video) => video.status === "queued" || video.status === "processing")) return;
    const timer = window.setInterval(() => void refreshVideos(), 1200);
    return () => window.clearInterval(timer);
  }, [videos]);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setError("");
    setFile(null);
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith(".mp4")) {
      setError("Alege un fișier cu extensia .mp4.");
      event.target.value = "";
      return;
    }
    if (selected.size > maxUploadBytes) {
      setError("Fișierul depășește limita de 500 MB.");
      event.target.value = "";
      return;
    }
    setFile(selected);
  }

  function uploadWithProgress(body: FormData): Promise<VideoUpload> {
    return new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", `${apiBase}/api/v1/videos`);
      request.upload.onprogress = (event) => {
        if (event.lengthComputable) setProgress(Math.round((event.loaded / event.total) * 100));
      };
      request.onload = () => {
        if (request.status >= 200 && request.status < 300) resolve(JSON.parse(request.responseText) as VideoUpload);
        else {
          const response = JSON.parse(request.responseText) as { detail?: string };
          reject(new Error(response.detail ?? "Încărcarea a eșuat."));
        }
      };
      request.onerror = () => reject(new Error("Nu s-a putut contacta API-ul local."));
      request.send(body);
    });
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Selectează un videoclip MP4 înainte de încărcare.");
      return;
    }
    setBusy(true);
    setProgress(0);
    setError("");
    const body = new FormData();
    body.append("file", file);
    body.append("event_name", eventName);
    body.append("season", season);
    body.append("match_number", matchNumber);
    body.append("alliance", alliance);
    try {
      await uploadWithProgress(body);
      setFile(null);
      setEventName("");
      setMatchNumber("1");
      const input = document.getElementById("video-file") as HTMLInputElement | null;
      if (input) input.value = "";
      await refreshVideos();
      notifyVideosUpdated();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Încărcarea a eșuat.");
    } finally {
      setBusy(false);
    }
  }

  async function removeVideo(videoId: string) {
    const response = await fetch(`${apiBase}/api/v1/videos/${videoId}`, { method: "DELETE" });
    if (response.ok) {
      await refreshVideos();
      notifyVideosUpdated();
    }
    else setError("Videoclipul nu a putut fi șters.");
  }

  async function analyzeVideo(videoId: string) {
    setError("");
    try {
      const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/analyze`, { method: "POST" });
      if (!response.ok) {
        const result = await response.json() as { detail?: string };
        throw new Error(result.detail ?? "Analiza nu a putut fi pornită.");
      }
      await refreshVideos();
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : "Analiza nu a putut fi pornită.");
    }
  }

  async function exportDataset() {
    setDatasetBusy(true);
    setDatasetMessage("");
    try {
      const response = await fetch(`${apiBase}/api/v1/training/dataset.zip`);
      if (!response.ok) {
        const result = await response.json() as { detail?: string };
        throw new Error(result.detail ?? "Datasetul nu a putut fi exportat.");
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = "matchlens-robot-dataset.zip";
      link.click();
      URL.revokeObjectURL(url);
      setDatasetMessage("Dataset YOLO descărcat. Rulează comanda locală de training din docs/video-processing.md.");
    } catch (exportError) {
      setDatasetMessage(exportError instanceof Error ? exportError.message : "Datasetul nu a putut fi exportat.");
    } finally {
      setDatasetBusy(false);
    }
  }

  return (
    <section id="analysis" aria-labelledby="analysis-title">
      <div className="section-head">
        <h2 id="analysis-title">Videoclipuri locale</h2>
        <div className="section-tools"><span className="section-note">{videos.length} încărcate · pe acest calculator</span><button className="subtle-button" type="button" disabled={datasetBusy} onClick={() => void exportDataset()}>{datasetBusy ? <LoaderCircle className="spin" aria-hidden="true" /> : <Download aria-hidden="true" />}{datasetBusy ? "Se exportă" : "Exportă dataset YOLO"}</button></div>
      </div>
      {datasetMessage && <p className="analysis-message">{datasetMessage}</p>}

      <form className="upload-form" onSubmit={submitUpload}>
        <div className="upload-form-title"><FileVideo2 aria-hidden="true" /><div><strong>Încarcă un meci</strong><span>MP4 · maxim 500 MB · stocat local</span></div></div>
        <div className="form-grid">
          <label>Eveniment<input required maxLength={160} value={eventName} onChange={(event) => setEventName(event.target.value)} placeholder="Numele competiției" /></label>
          <label>Sezon<input required maxLength={24} value={season} onChange={(event) => setSeason(event.target.value)} /></label>
          <label>Meci<input required type="number" min="1" max="9999" value={matchNumber} onChange={(event) => setMatchNumber(event.target.value)} /></label>
          <label>Alianță<select value={alliance} onChange={(event) => setAlliance(event.target.value as "Red" | "Blue")}><option>Blue</option><option>Red</option></select></label>
        </div>
        <div className="upload-actions">
          <label className="file-picker" htmlFor="video-file"><Video aria-hidden="true" />{file ? file.name : "Alege fișier MP4"}</label>
          <input id="video-file" className="visually-hidden" type="file" accept=".mp4,video/mp4" onChange={selectFile} />
          <button className="button" type="submit" disabled={busy || !file}>
            {busy ? <LoaderCircle className="spin" aria-hidden="true" /> : <Upload aria-hidden="true" />}
            {busy ? `Se încarcă ${progress}%` : "Încarcă video"}
          </button>
        </div>
        {busy && <progress className="upload-progress" max="100" value={progress} aria-label="Progres încărcare" />}
        {error && <p className="form-error" role="alert">{error}</p>}
      </form>

      {loading ? <div className="empty-analysis">Se verifică videoclipurile locale…</div> : videos.length === 0 ? (
        <div className="empty-analysis"><div><div className="empty-icon"><Video aria-hidden="true" /></div><strong>Niciun videoclip încărcat</strong><span>Alege un MP4 de pe calculator ca să-l adaugi aici.</span></div></div>
      ) : (
        <div className="video-list">
          {videos.map((video) => (
            <article className="video-item" key={video.id}>
              <div className="video-meta">
                <div><strong>{video.event_name || "Eveniment nespecificat"} · Meci {video.match_number ?? "—"}</strong><span>{video.season ?? "Sezon nespecificat"} · {video.alliance ?? "Alianță nespecificată"} · {video.original_filename} · {formatBytes(video.size_bytes)}</span></div>
                <div className="video-item-actions">
                  <span className={`analysis-state ${video.status}`}>{video.status === "uploaded" ? "Neanalizat" : video.status === "queued" ? "În coadă" : video.status === "processing" ? "Se analizează" : video.status === "needs_review" ? "Necesită revizuire" : "Analiza a eșuat"}</span>
                  <button className="button analysis-button" type="button" disabled={video.status === "queued" || video.status === "processing"} onClick={() => void analyzeVideo(video.id)}>
                    {video.status === "queued" || video.status === "processing" ? <LoaderCircle className="spin" aria-hidden="true" /> : video.status === "failed" ? <RotateCw aria-hidden="true" /> : <Play aria-hidden="true" />}
                    {video.status === "failed" ? "Reîncearcă" : video.status === "needs_review" ? "Analizează din nou" : "Analizează video"}
                  </button>
                  <button className="icon-button" type="button" title="Șterge videoclipul" aria-label={`Șterge ${video.original_filename}`} onClick={() => void removeVideo(video.id)}><Trash2 aria-hidden="true" /></button>
                </div>
              </div>
              {(video.status === "queued" || video.status === "processing") && <progress className="upload-progress" max="100" value={video.analysis_progress} aria-label={`Progres analiză ${video.analysis_progress}%`} />}
              {video.analysis_message && <p className={`analysis-message ${video.status}`}>{video.analysis_message}</p>}
              {video.status === "needs_review" && video.duration_seconds !== null && (
                <dl className="video-metrics">
                  <div><dt>Durată măsurată</dt><dd>{Math.floor(video.duration_seconds / 60)}:{String(Math.floor(video.duration_seconds % 60)).padStart(2, "0")}</dd></div>
                  <div><dt>Rezoluție</dt><dd>{video.width} × {video.height}</dd></div>
                  <div><dt>FPS</dt><dd>{video.fps?.toFixed(2)}</dd></div>
                  <div><dt>Cadre decodate</dt><dd>{video.frame_count?.toLocaleString("ro-RO")}</dd></div>
                  <div><dt>Cadre eșantionate</dt><dd>{video.sampled_frames?.toLocaleString("ro-RO")}</dd></div>
                  <div><dt>Detector roboți</dt><dd>Indisponibil</dd></div>
                </dl>
              )}
              <VideoReview videoId={video.id} videoUrl={`${apiBase}/api/v1/videos/${video.id}/file`} videoWidth={video.width} videoHeight={video.height} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}