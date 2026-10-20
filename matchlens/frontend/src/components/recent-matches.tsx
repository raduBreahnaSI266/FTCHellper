"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Video } from "lucide-react";
import { apiBase, matchTitle, VideoUpload, videosUpdatedEvent } from "@/lib/videos";

export function RecentMatches() {
  const [videos, setVideos] = useState<VideoUpload[]>([]);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadRecent() {
      try {
        const response = await fetch(`${apiBase}/api/v1/videos`, { cache: "no-store" });
        if (!response.ok) throw new Error("Could not load local matches");
        const data = await response.json() as VideoUpload[];
        if (active) {
          setVideos(data.slice(0, 4));
          setLoadError(false);
        }
      } catch {
        if (active) setLoadError(true);
      }
    }
    void loadRecent();
    window.addEventListener(videosUpdatedEvent, loadRecent);
    return () => {
      active = false;
      window.removeEventListener(videosUpdatedEvent, loadRecent);
    };
  }, []);

  return (
    <section aria-labelledby="matches-title">
      <div className="section-head">
        <h2 id="matches-title">Recent matches</h2>
        <Link className="section-link" href="/matches">All matches <ArrowRight aria-hidden="true" /></Link>
      </div>
      <div className="match-list">
        {videos.map((video) => (
          <article className="match-row" key={video.id}>
            <div><div className="match-name">{matchTitle(video)}</div><div className="match-sub">{video.original_filename}</div></div>
            <div><span className="meta-label">Season</span>{video.season ?? "—"}</div>
            <div><span className="meta-label">Alliance</span>{video.alliance ?? "—"}</div>
            <div><span className="meta-label">Analysis</span><span className={`analysis-state ${video.status}`}>{video.status === "needs_review" ? "Review" : video.status === "processing" ? "Processing" : video.status === "failed" ? "Failed" : "Not analyzed"}</span></div>
            <Link className="row-open" href={`/matches?video=${video.id}`} aria-label={`Open ${matchTitle(video)}`}><Video aria-hidden="true" /></Link>
          </article>
        ))}
        {videos.length === 0 && !loadError && (
          <div className="matches-empty">Niciun meci încărcat. Încarcă un video MP4 mai jos.</div>
        )}
        {loadError && <div className="matches-empty error-text">Nu s-au putut încărca meciurile locale.</div>}
      </div>
    </section>
  );
}