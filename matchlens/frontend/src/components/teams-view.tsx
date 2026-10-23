"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpRight, Search, Users } from "lucide-react";
import { apiBase } from "@/lib/videos";

type Team = {
  number: number;
  name: string;
};

const TEAM_ROW_HEIGHT = 58;
const TEAM_WINDOW_SIZE = 50;
const TEAM_OVERSCAN = 10;

export function TeamsView() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [query, setQuery] = useState("");
  const [firstVisible, setFirstVisible] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  async function loadTeams() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/api/v1/teams/directory`, { cache: "no-store" });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Nu s-a putut încărca directorul FTCScout.");
      }
      setTeams(await response.json() as Team[]);
      setFirstVisible(0);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Nu s-a putut încărca directorul FTCScout.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTeams();
  }, []);

  const filteredTeams = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) return teams;
    return teams.filter((team) => `${team.number} ${team.name}`.toLocaleLowerCase().includes(normalizedQuery));
  }, [teams, query]);
  const visibleTeams = filteredTeams.slice(firstVisible, firstVisible + TEAM_WINDOW_SIZE);

  return (
    <div className="content">
      <section className="heading-row">
        <div>
          <div className="eyebrow">FTCScout directory</div>
          <h1>Teams</h1>
          <p className="subhead">Caută după numărul sau numele echipei în directorul FTCScout.</p>
        </div>
      </section>

      <section aria-label="Directorul echipelor FTCScout">
        <div className="team-directory-toolbar">
          <label className="team-directory-search">
            <Search aria-hidden="true" />
            <input
              aria-label="Caută echipă"
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setFirstVisible(0);
                listRef.current?.scrollTo({ top: 0 });
              }}
              placeholder="Caută echipă după număr sau nume"
            />
          </label>
          <span className="team-directory-count">
            {loading ? "Se încarcă toate echipele…" : `${filteredTeams.length.toLocaleString("ro-RO")} ${filteredTeams.length === 1 ? "echipă" : "echipe"} încărcate`}
          </span>
        </div>

        {loading ? (
          <div className="empty-analysis">Se încarcă directorul complet FTCScout…</div>
        ) : error ? (
          <div className="empty-analysis error-text" role="alert">
            <div>
              <strong>Directorul FTCScout nu este disponibil acum.</strong>
              <p>{error}</p>
              <button className="button team-retry" type="button" onClick={() => void loadTeams()}>Încearcă din nou</button>
            </div>
          </div>
        ) : filteredTeams.length === 0 ? (
          <div className="empty-analysis">
            <div>
              <div className="empty-icon"><Users aria-hidden="true" /></div>
              <strong>Nicio echipă găsită</strong>
              <span>Încearcă alt număr sau alt termen de căutare.</span>
            </div>
          </div>
        ) : (
          <>
            <div
              className="team-grid"
              ref={listRef}
              role="list"
              aria-label="Echipe FTCScout"
              onScroll={(event) => {
                const topIndex = Math.max(0, Math.floor(event.currentTarget.scrollTop / TEAM_ROW_HEIGHT) - TEAM_OVERSCAN);
                setFirstVisible((current) => current === topIndex ? current : topIndex);
              }}
            >
              <div className="team-virtual-canvas" style={{ height: filteredTeams.length * TEAM_ROW_HEIGHT }}>
                {visibleTeams.map((team, index) => (
                  <article
                    className="team-card"
                    key={team.number}
                    role="listitem"
                    aria-posinset={firstVisible + index + 1}
                    aria-setsize={filteredTeams.length}
                    style={{ top: (firstVisible + index) * TEAM_ROW_HEIGHT }}
                  >
                    <div className="team-number">{team.number}</div>
                    <div className="team-card-title"><h2>{team.name}</h2><span>FTC team</span></div>
                    <a
                      className="team-open"
                      href={`https://ftcscout.org/teams/${team.number}`}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`Deschide echipa ${team.number} pe FTCScout`}
                    >
                      <ArrowUpRight aria-hidden="true" />
                    </a>
                  </article>
                ))}
              </div>
            </div>
            <p className="team-attribution">Director furnizat de <a href="https://ftcscout.org/teams" target="_blank" rel="noreferrer">FTCScout</a>.</p>
          </>
        )}
      </section>
    </div>
  );
}
