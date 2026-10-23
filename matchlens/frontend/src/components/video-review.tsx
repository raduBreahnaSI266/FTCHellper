"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Check, Pencil, Play, Plus, RotateCcw, Trash2, X } from "lucide-react";
import { FieldRobots } from "@/components/field-robots";
import { apiBase } from "@/lib/videos";

const eventOptions = [
  ["autonomous", "Autonomous"],
  ["teleop", "Teleoperated"],
  ["candidate_score", "Scoring candidate"],
  ["confirmed_score", "Confirmed scoring"],
  ["intake_attempt", "Collection / intake"],
  ["placement_attempt", "Placement attempt"],
  ["contact", "Contact / collision"],
  ["suspected_delay", "Suspected delay"],
  ["inactivity", "Inactivity interval"],
  ["endgame", "Endgame action"],
  ["unknown", "Unknown event"],
] as const;

type EventType = (typeof eventOptions)[number][0];
type Annotation = {
  id: string;
  video_id: string;
  event_type: EventType;
  timestamp_seconds: number;
  end_timestamp_seconds: number | null;
  robot_label: string | null;
  note: string | null;
  detection_source: "manual";
  verification_status: "unreviewed" | "confirmed" | "rejected";
};
type TrajectoryPoint = {
  timestamp_seconds: number;
  x_normalized: number;
  y_normalized: number;
  confidence: number;
};
type RobotTrack = {
  id: string;
  source_track_id: string;
  class_name: string;
  detection_source: "model" | "seeded_tracker";
  model_name: string;
  model_version: string;
  confidence_threshold: number;
  points: TrajectoryPoint[];
};
type TracksResponse = {
  detector_status: string;
  detector_message: string | null;
  tracks: RobotTrack[];
};
type RobotLabel = {
  id: string;
  video_id: string;
  timestamp_seconds: number;
  class_name: string;
  x1_normalized: number;
  y1_normalized: number;
  x2_normalized: number;
  y2_normalized: number;
};
type RobotBox = Omit<RobotLabel, "id" | "video_id" | "timestamp_seconds">;
const trackColors = ["#69b8d2", "#c3da74", "#e39a76", "#9b9fe0", "#e6d16f", "#78c9a2"];

function formatTime(seconds: number): string {
  const wholeSeconds = Math.floor(seconds);
  const minutes = Math.floor(wholeSeconds / 60);
  const remaining = wholeSeconds % 60;
  const tenths = Math.floor((seconds - wholeSeconds) * 10);
  return `${minutes}:${String(remaining).padStart(2, "0")}.${tenths}`;
}

function eventLabel(type: EventType): string {
  return eventOptions.find(([value]) => value === type)?.[1] ?? type;
}

export function VideoReview({ videoId, videoUrl, videoWidth, videoHeight }: { videoId: string; videoUrl: string; videoWidth?: number | null; videoHeight?: number | null }) {
  const player = useRef<HTMLVideoElement>(null);
  const labelCanvas = useRef<HTMLCanvasElement>(null);
  const drawStart = useRef<{ x: number; y: number } | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [tracks, setTracks] = useState<RobotTrack[]>([]);
  const [robotLabels, setRobotLabels] = useState<RobotLabel[]>([]);
  const [draftBoxes, setDraftBoxes] = useState<RobotBox[]>([]);
  const [labelMessage, setLabelMessage] = useState("");
  const [labelBusy, setLabelBusy] = useState(false);
  const [trackingIndex, setTrackingIndex] = useState<number | null>(null);
  const [labelMode, setLabelMode] = useState(false);
  const [detectorMessage, setDetectorMessage] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [eventType, setEventType] = useState<EventType>("unknown");
  const [timestamp, setTimestamp] = useState("0");
  const [endTimestamp, setEndTimestamp] = useState("");
  const [robotLabel, setRobotLabel] = useState("");
  const [note, setNote] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const labelTimestamp = Math.max(0, Math.round(currentTime * 10) / 10);
  const savedBoxes = robotLabels.filter((label) => label.timestamp_seconds === labelTimestamp);

  useEffect(() => {
    let active = true;
    fetch(`${apiBase}/api/v1/videos/${videoId}/robot-labels`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Etichetele nu au putut fi încărcate.");
        return await response.json() as RobotLabel[];
      })
      .then((labels) => { if (active) setRobotLabels(labels); })
      .catch(() => { if (active) setLabelMessage("Etichetele locale nu au putut fi încărcate."); });
    return () => { active = false; };
  }, [videoId]);

  useEffect(() => {
    const canvas = labelCanvas.current;
    if (!canvas) return;
    const bounds = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(bounds.width * ratio);
    canvas.height = Math.round(bounds.height * ratio);
    const context = canvas.getContext("2d");
    if (!context) return;
    context.scale(ratio, ratio);
    context.clearRect(0, 0, bounds.width, bounds.height);
    for (const [index, box] of [...savedBoxes, ...draftBoxes].entries()) {
      const x = box.x1_normalized * bounds.width;
      const y = box.y1_normalized * bounds.height;
      const width = (box.x2_normalized - box.x1_normalized) * bounds.width;
      const height = (box.y2_normalized - box.y1_normalized) * bounds.height;
      context.strokeStyle = trackColors[index % trackColors.length];
      context.lineWidth = 2;
      context.strokeRect(x, y, width, height);
      context.fillStyle = trackColors[index % trackColors.length];
      context.font = "12px sans-serif";
      context.fillText(`robot ${index + 1}`, x + 3, Math.max(12, y - 4));
    }
  }, [savedBoxes, draftBoxes, currentTime]);

  function normalizedPointer(event: React.PointerEvent<HTMLCanvasElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.min(Math.max((event.clientX - bounds.left) / bounds.width, 0), 1),
      y: Math.min(Math.max((event.clientY - bounds.top) / bounds.height, 0), 1),
    };
  }

  function startBox(event: React.PointerEvent<HTMLCanvasElement>) {
    const point = normalizedPointer(event);
    drawStart.current = point;
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function finishBox(event: React.PointerEvent<HTMLCanvasElement>) {
    const start = drawStart.current;
    drawStart.current = null;
    if (!start) return;
    const end = normalizedPointer(event);
    const box = {
      class_name: "robot",
      x1_normalized: Math.min(start.x, end.x),
      y1_normalized: Math.min(start.y, end.y),
      x2_normalized: Math.max(start.x, end.x),
      y2_normalized: Math.max(start.y, end.y),
    };
    if (box.x2_normalized - box.x1_normalized > 0.005 && box.y2_normalized - box.y1_normalized > 0.005) {
      setDraftBoxes((current) => [...current, box]);
    }
  }

  async function saveFrameLabels(boxesToSave = [...savedBoxes, ...draftBoxes]) {
    setLabelBusy(true);
    setLabelMessage("");
    try {
      const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/robot-labels/${labelTimestamp}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ boxes: boxesToSave.map(({ class_name, x1_normalized, y1_normalized, x2_normalized, y2_normalized }) => ({ class_name, x1_normalized, y1_normalized, x2_normalized, y2_normalized })) }),
      });
      const result = await response.json() as RobotLabel[] | { detail?: string };
      if (!response.ok || !Array.isArray(result)) {
        throw new Error(!Array.isArray(result) ? result.detail : "Etichetele nu au putut fi salvate.");
      }
      setRobotLabels((current) => [...current.filter((label) => label.timestamp_seconds !== labelTimestamp), ...result]);
      setDraftBoxes([]);
      setLabelMessage("Etichete salvate local.");
    } catch (saveError) {
      setLabelMessage(saveError instanceof Error ? saveError.message : "Etichetele nu au putut fi salvate.");
    } finally {
      setLabelBusy(false);
    }
  }

  async function trackRobot(box: RobotBox, index: number) {
    setTrackingIndex(index);
    setLabelMessage("");
    try {
      const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/robot-labels/${labelTimestamp}/track`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(box),
      });
      const result = await response.json() as RobotTrack | { detail?: string };
      if (!response.ok || !("points" in result)) {
        throw new Error("detail" in result ? result.detail : "Robotul nu a putut fi urmărit.");
      }
      setTracks((current) => [...current, result]);
      setLabelMessage(`Urmărire locală terminată: ${result.points.length} poziții estimate. Verifică traseul.`);
    } catch (trackingError) {
      setLabelMessage(trackingError instanceof Error ? trackingError.message : "Robotul nu a putut fi urmărit.");
    } finally {
      setTrackingIndex(null);
    }
  }

  async function refreshAnnotations() {
    try {
      const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/annotations`, { cache: "no-store" });
      if (!response.ok) throw new Error("Could not load annotations.");
      setAnnotations(await response.json() as Annotation[]);
      setError("");
    } catch {
      setError("Nu s-au putut încărca adnotările de la API-ul local.");
    }
  }

  useEffect(() => {
    let active = true;
    async function loadAnnotations() {
      try {
        const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/annotations`, { cache: "no-store" });
        if (!response.ok) throw new Error("Could not load annotations.");
        const data = await response.json() as Annotation[];
        if (active) {
          setAnnotations(data);
          setError("");
        }
      } catch {
        if (active) setError("Nu s-au putut încărca adnotările de la API-ul local.");
      }
    }
    void loadAnnotations();
    return () => {
      active = false;
    };
  }, [videoId]);

  useEffect(() => {
    let active = true;
    async function loadTracks() {
      try {
        const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/tracks`, { cache: "no-store" });
        if (!response.ok) throw new Error("Could not load robot tracks.");
        const result = await response.json() as TracksResponse;
        if (active) {
          setTracks(result.tracks);
          setDetectorMessage(result.detector_message ?? "");
        }
      } catch {
        if (active) setDetectorMessage("Nu s-au putut încărca track-urile de la API-ul local.");
      }
    }
    void loadTracks();
    return () => { active = false; };
  }, [videoId]);

  function resetForm() {
    setEditingId(null);
    setEventType("unknown");
    setTimestamp(currentTime.toFixed(1));
    setEndTimestamp("");
    setRobotLabel("");
    setNote("");
  }

  async function saveAnnotation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      event_type: eventType,
      timestamp_seconds: Number(timestamp),
      end_timestamp_seconds: endTimestamp ? Number(endTimestamp) : null,
      robot_label: robotLabel.trim() || null,
      note: note.trim() || null,
    };
    try {
      const response = await fetch(
        `${apiBase}/api/v1/videos/${videoId}/annotations${editingId ? `/${editingId}` : ""}`,
        {
          method: editingId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) {
        const result = await response.json() as { detail?: string };
        throw new Error(result.detail ?? "Adnotarea nu a putut fi salvată.");
      }
      resetForm();
      await refreshAnnotations();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Adnotarea nu a putut fi salvată.");
    } finally {
      setSaving(false);
    }
  }

  function beginEdit(annotation: Annotation) {
    setEditingId(annotation.id);
    setEventType(annotation.event_type);
    setTimestamp(annotation.timestamp_seconds.toFixed(1));
    setEndTimestamp(annotation.end_timestamp_seconds?.toFixed(1) ?? "");
    setRobotLabel(annotation.robot_label ?? "");
    setNote(annotation.note ?? "");
  }

  async function setVerification(annotation: Annotation, status: Annotation["verification_status"]) {
    const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/annotations/${annotation.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verification_status: status }),
    });
    if (response.ok) await refreshAnnotations();
    else setError("Starea adnotării nu a putut fi schimbată.");
  }

  async function removeAnnotation(annotationId: string) {
    const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/annotations/${annotationId}`, { method: "DELETE" });
    if (response.ok) await refreshAnnotations();
    else setError("Adnotarea nu a putut fi ștearsă.");
  }

  function seekTo(seconds: number) {
    if (player.current) {
      player.current.currentTime = seconds;
      setCurrentTime(seconds);
    }
  }

  return (
    <div className="video-review">
      <div className="label-player-wrap">
        <video
          ref={player}
          className="local-player"
          controls
          preload="metadata"
          src={videoUrl}
          onTimeUpdate={(event) => {
            const time = event.currentTarget.currentTime;
            if (Math.round(time * 10) !== Math.round(currentTime * 10)) setDraftBoxes([]);
            setCurrentTime(time);
          }}
          onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
        >
          Browserul tău nu poate reda acest videoclip.
        </video>
      </div>
      <div className="label-frame-wrap">
        <Image
          className="label-frame-image"
          src={`${apiBase}/api/v1/videos/${videoId}/frame/${labelTimestamp}?frame=${labelTimestamp}`}
          alt={`Cadru extras la ${formatTime(labelTimestamp)}`}
          width={videoWidth || 16}
          height={videoHeight || 9}
          unoptimized
        />
        <canvas
          ref={labelCanvas}
          className={`robot-label-canvas${labelMode ? " active" : ""}`}
          aria-label="Desenează dreptunghiuri peste roboți pentru etichetare"
          onPointerDown={startBox}
          onPointerUp={finishBox}
          onPointerCancel={() => { drawStart.current = null; }}
        />
      </div>
      <section className="label-tools" aria-label="Etichetare locală pentru antrenare">
        <div className="label-tools-head"><strong>Etichetează roboții</strong><span>{savedBoxes.length + draftBoxes.length} cutii la {formatTime(labelTimestamp)}</span></div>
        <label className="label-time-control">Cadru la {formatTime(labelTimestamp)}
          <input type="range" min="0" max={duration || 1} step="0.5" value={Math.min(labelTimestamp, duration || labelTimestamp)} onChange={(event) => seekTo(Number(event.target.value))} />
        </label>
        <div className="label-tools-actions">
          <button className={`subtle-button${labelMode ? " label-mode-active" : ""}`} type="button" aria-pressed={labelMode} onClick={() => setLabelMode((active) => !active)}>{labelMode ? "Oprește etichetarea" : "Pornește etichetarea"}</button>
          <button className="subtle-button" type="button" onClick={() => seekTo(Math.max(0, currentTime - 1))}>− 1 sec</button>
          <button className="subtle-button" type="button" onClick={() => seekTo(Math.min(duration || currentTime + 1, currentTime + 1))}>+ 1 sec</button>
          <button className="subtle-button" type="button" onClick={() => setDraftBoxes([])} disabled={draftBoxes.length === 0}>Șterge desenele noi</button>
          <button className="subtle-button" type="button" onClick={() => void saveFrameLabels([])} disabled={labelBusy || savedBoxes.length === 0}>Șterge etichetele cadrului</button>
          <button className="button" type="button" disabled={labelBusy} onClick={() => void saveFrameLabels()}>{labelBusy ? "Se salvează…" : "Salvează etichetele cadrului"}</button>
        </div>
        {[...savedBoxes, ...draftBoxes].map((box, index) => (
          <button className="subtle-button track-seed-button" key={`${box.x1_normalized}-${box.y1_normalized}-${index}`} type="button" disabled={trackingIndex !== null} onClick={() => void trackRobot(box, index)}>
            {trackingIndex === index ? "Se urmărește…" : `Urmărește robotul ${index + 1} până la final`}
          </button>
        ))}
        <p>{labelMessage || (labelMode ? "Pauzează videoclipul și trage cu mouse-ul peste fiecare robot." : "Etichetele rămân pe acest calculator. Activează modul de etichetare pentru a desena cutii peste roboți.")}</p>
      </section>

      <FieldRobots videoId={videoId} />

      <div className="timeline-head"><h3>Timeline manual</h3><span>{annotations.length} evenimente · timpul playerului {formatTime(currentTime)}</span></div>
      <form className="annotation-form" onSubmit={saveAnnotation}>
        <label>Tip eveniment<select value={eventType} onChange={(event) => setEventType(event.target.value as EventType)}>
          {eventOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label>De la (sec)<input type="number" min="0" max={duration || undefined} step="0.1" required value={timestamp} onChange={(event) => setTimestamp(event.target.value)} /></label>
        <label>Până la (opțional)<input type="number" min={Number(timestamp) || 0} max={duration || undefined} step="0.1" value={endTimestamp} onChange={(event) => setEndTimestamp(event.target.value)} /></label>
        <label>Robot (opțional)<input maxLength={80} value={robotLabel} onChange={(event) => setRobotLabel(event.target.value)} placeholder="Ex. Blue 1" /></label>
        <label className="annotation-note">Notă<input maxLength={1000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Observație bazată pe video" /></label>
        <div className="annotation-form-actions">
          <button className="subtle-button" type="button" onClick={() => setTimestamp(currentTime.toFixed(1))}><Play aria-hidden="true" />Folosește timpul curent</button>
          <div>
            {editingId && <button className="subtle-button" type="button" onClick={resetForm}><X aria-hidden="true" />Anulează</button>}
            <button className="button" type="submit" disabled={saving}>{editingId ? <Pencil aria-hidden="true" /> : <Plus aria-hidden="true" />}{saving ? "Se salvează" : editingId ? "Salvează modificările" : "Adaugă eveniment"}</button>
          </div>
        </div>
      </form>

      {error && <p className="form-error" role="alert">{error}</p>}
      <section className="trajectory-section" aria-labelledby={`trajectory-title-${videoId}`}>
        <div className="timeline-head"><h3 id={`trajectory-title-${videoId}`}>Traiectorii estimate</h3><span>{tracks.length} track-uri · coordonate normalizate ale imaginii</span></div>
        {tracks.length > 0 ? (
          <div className="trajectory-layout">
            <svg className="trajectory-plot" viewBox="0 0 100 100" role="img" aria-label="Trasee estimate ale roboților în coordonate de imagine">
              <rect x="0.5" y="0.5" width="99" height="99" fill="#11191b" stroke="#405053" />
              <path d="M25 1V99 M50 1V99 M75 1V99 M1 25H99 M1 50H99 M1 75H99" stroke="#344346" strokeWidth="0.35" strokeDasharray="1.4 1.8" />
              {tracks.map((track, index) => {
                const color = trackColors[index % trackColors.length];
                const points = track.points.map((point) => `${point.x_normalized * 100},${point.y_normalized * 100}`).join(" ");
                return (
                  <g key={track.id}>
                    {track.points.length > 1 && <polyline points={points} fill="none" stroke={color} strokeWidth="1.1" strokeLinejoin="round" strokeLinecap="round" />}
                    {track.points.map((point, pointIndex) => <circle key={`${point.timestamp_seconds}-${pointIndex}`} cx={point.x_normalized * 100} cy={point.y_normalized * 100} r="1.1" fill={color}><title>{`Track ${track.source_track_id}, ${point.timestamp_seconds.toFixed(1)}s, confidence ${(point.confidence * 100).toFixed(0)}%`}</title></circle>)}
                  </g>
                );
              })}
            </svg>
            <ul className="track-legend">
              {tracks.map((track, index) => (
                <li key={track.id}>
                  <span className="track-swatch" style={{ background: trackColors[index % trackColors.length] }} />
                  <span><strong>{track.class_name} · ID {track.source_track_id}</strong><small>{track.points.length} puncte · {track.detection_source === "seeded_tracker" ? "urmărire OpenCV pornită din cutia selectată" : `model ${track.model_name} · v${track.model_version} · prag ${(track.confidence_threshold * 100).toFixed(0)}%`}</small></span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="detector-empty">{detectorMessage || "Niciun track de model disponibil. Rulează analiza cu un model robot configurat sau continuă cu adnotări manuale."}</div>
        )}
      </section>
      {annotations.length === 0 ? <div className="timeline-empty">Nicio adnotare. Derulează video-ul și marchează un eveniment.</div> : (
        <ol className="annotation-list">
          {annotations.map((annotation) => (
            <li className="annotation-row" key={annotation.id}>
              <button className="timestamp-button" type="button" onClick={() => seekTo(annotation.timestamp_seconds)} title="Sari la momentul din video">
                <span>{formatTime(annotation.timestamp_seconds)}</span><Play aria-hidden="true" />
              </button>
              <div className="annotation-details">
                <strong>{eventLabel(annotation.event_type)}{annotation.robot_label ? ` · ${annotation.robot_label}` : ""}</strong>
                {annotation.end_timestamp_seconds !== null && <span>Interval până la {formatTime(annotation.end_timestamp_seconds)}</span>}
                {annotation.note && <span>{annotation.note}</span>}
                <span className={`verification ${annotation.verification_status}`}>{annotation.detection_source === "manual" ? "Manual" : "Model"} · {annotation.verification_status === "unreviewed" ? "Neverificat" : annotation.verification_status === "confirmed" ? "Confirmat" : "Respins"}</span>
              </div>
              <div className="annotation-actions">
                <button className="icon-button" type="button" title="Editează" aria-label="Editează adnotarea" onClick={() => beginEdit(annotation)}><Pencil aria-hidden="true" /></button>
                {annotation.verification_status !== "confirmed" && <button className="icon-button good" type="button" title="Confirmă" aria-label="Confirmă adnotarea" onClick={() => void setVerification(annotation, "confirmed")}><Check aria-hidden="true" /></button>}
                {annotation.verification_status !== "rejected" && <button className="icon-button" type="button" title="Respinge" aria-label="Respinge adnotarea" onClick={() => void setVerification(annotation, "rejected")}><X aria-hidden="true" /></button>}
                {annotation.verification_status !== "unreviewed" && <button className="icon-button" type="button" title="Marchează neverificat" aria-label="Marchează neverificat" onClick={() => void setVerification(annotation, "unreviewed")}><RotateCcw aria-hidden="true" /></button>}
                <button className="icon-button" type="button" title="Șterge" aria-label="Șterge adnotarea" onClick={() => void removeAnnotation(annotation.id)}><Trash2 aria-hidden="true" /></button>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}