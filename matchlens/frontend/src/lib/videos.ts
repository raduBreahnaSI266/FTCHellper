export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";
export const videosUpdatedEvent = "matchlens:videos-updated";

export function notifyVideosUpdated(): void {
  window.dispatchEvent(new Event(videosUpdatedEvent));
}

export type VideoUpload = {
  id: string;
  original_filename: string;
  event_name: string | null;
  season: string | null;
  match_number: number | null;
  alliance: "Red" | "Blue" | null;
  content_type: string;
  size_bytes: number;
  status: string;
  analysis_progress: number;
  analysis_message: string | null;
  duration_seconds: number | null;
  fps: number | null;
  frame_count: number | null;
  width: number | null;
  height: number | null;
  sampled_frames: number | null;
  detector_status: string | null;
  analyzed_at: string | null;
  created_at: string;
};

export function formatBytes(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

export function matchTitle(video: VideoUpload): string {
  return `${video.event_name || "Eveniment nespecificat"} · Meci ${video.match_number ?? "—"}`;
}