"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ChevronDown, Search, Video } from "lucide-react";
import { VideoReview } from "@/components/video-review";
import { apiBase, formatBytes, matchTitle, VideoUpload, videosUpdatedEvent } from "@/lib/videos";

export function MatchesView() {
  const searchParams = useSearchParams();
  const [videos, setVideos] = useState<VideoUpload[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("video"));
  const [query, setQuery] = useState("");
  const [season, setSeason] = useState("all");
  const [alliance, setAlliance] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadVideos() {
    try {
      const response = await fetch(`${apiBase}/api/v1/videos`, { cache: "no-store" });
      if (!response.ok) throw new Error("Nu s-au putut încărca meciurile locale.");
      setVideos(await response.json() as VideoUpload[]);
      setError("");
    } catch {
      setError("API-ul local nu răspunde. Verifică dacă backendul rulează pe 127.0.0.1:8001.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadVideos();
    window.addEventListener(videosUpdatedEvent, loadVideos);
    return () => window.removeEventListener(videosUpdatedEvent, loadVideos);
  }, []);

  const seasons = useMemo(() => Array.from(new Set(videos.map((video) => video.season).filter((value): value is string => Boolean(value)))), [videos]);
  const filteredVideos = useMemo(() => videos.filter((video) => {
    const text = `${video.event_name ?? ""} ${video.match_number ?? ""} ${video.original_filename}`.toLowerCase();
    return text.includes(query.toLowerCase())
      && (season === "all" || video.season === season)
      && (alliance === "all" || video.alliance === alliance);
  }), [videos, query, season, alliance]);
  const selectedVideo = videos.find((video) => video.id === selectedId);

  return (
    <div className="content">
      <section className="heading-row">
        <div>
          <div className="eyebrow">Match library</div>
          <h1>Matches</h1>
          <p className="subhead">Videoclipuri încărcate local și adnotările lor manuale.</p>
        </div>
        <Link className="button" href="/#analysis"><Video aria-hidden="true" /> Încarcă un meci</Link>
      </section>

      <section aria-label="Filtre meciuri">
        <div className="matches-toolbar">
          <label className="match-search"><Search aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Caută eveniment, meci sau fișier" /></label>
          <label className="filter-select"><span>Sezon</span><select value={season} onChange={(event) => setSeason(event.target.value)}><option value="all">Toate sezoanele</option>{seasons.map((value) => <option key={value}>{value}</option>)}</select><ChevronDown aria-hidden="true" /></label>
          <label className="filter-select"><span>Alianță</span><select value={alliance} onChange={(event) => setAlliance(event.target.value)}><option value="all">Toate</option><option>Blue</option><option>Red</option></select><ChevronDown aria-hidden="true" /></label>
          <span className="match-count">{filteredVideos.length} {filteredVideos.length === 1 ? "meci" : "meciuri"}</span>
        </div>
      </section>

      {loading ? <div className="empty-analysis">Se încarcă meciurile locale…</div> : error ? (
        <div className="empty-analysis error-text">{error}</div>
      ) : filteredVideos.length === 0 ? (
        <div className="empty-analysis"><div><div className="empty-icon"><Video aria-hidden="true" /></div><strong>{videos.length ? "Niciun rezultat pentru filtrele alese" : "Niciun meci încărcat"}</strong><span>{videos.length ? "Schimbă căutarea sau filtrele." : "Încarcă un video din Overview ca să apară aici."}</span></div></div>
      ) : (
        <div className="matches-layout">
          <div className="matches-table-wrap">
            <div className="matches-table-head"><span>Eveniment / video</span><span>Sezon</span><span>Alianță</span><span>Status</span></div>
            {filteredVideos.map((video) => (
              <button className={`matches-table-row ${selectedId === video.id ? "selected" : ""}`} type="button" key={video.id} onClick={() => setSelectedId(selectedId === video.id ? null : video.id)}>
                <span className="matches-main-cell"><strong>{matchTitle(video)}</strong><small>{video.original_filename} · {formatBytes(video.size_bytes)}</small></span>
                <span>{video.season ?? "—"}</span>
                <span>{video.alliance ?? "—"}</span>
                <span className={`analysis-state ${video.status}`}>{video.status === "needs_review" ? "Review" : video.status === "processing" ? "Processing" : video.status === "failed" ? "Failed" : "Uploaded"}</span>
              </button>
            ))}
          </div>

          {selectedVideo && (
            <article className="match-detail">
              <div className="match-detail-heading"><div><span className="eyebrow">Manual review</span><h2>{matchTitle(selectedVideo)}</h2><p>{selectedVideo.season} · {selectedVideo.alliance} alliance · {selectedVideo.original_filename}</p></div><button className="close-detail" type="button" onClick={() => setSelectedId(null)} aria-label="Închide player">×</button></div>
              <VideoReview videoId={selectedVideo.id} videoUrl={`${apiBase}/api/v1/videos/${selectedVideo.id}/file`} />
            </article>
          )}
        </div>
      )}
    </div>
  );
}