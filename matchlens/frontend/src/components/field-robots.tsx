"use client";

import { useEffect, useState } from "react";
import { LoaderCircle, Plus, Search, Trash2, Users } from "lucide-react";
import { apiBase } from "@/lib/videos";

type Alliance = "Blue" | "Red";
type Team = {
  number: number;
  name: string;
};
type FieldRobot = {
  team_number: number;
  team_name: string;
  id: string;
  video_id: string;
  alliance: Alliance;
};

export function FieldRobots({ videoId }: { videoId: string }) {
  const [robots, setRobots] = useState<FieldRobot[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Team[]>([]);
  const [alliance, setAlliance] = useState<Alliance>("Blue");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function loadRobots() {
      try {
        const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/field-robots`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Nu s-au putut încărca echipele meciului.");
        setRobots(await response.json() as FieldRobot[]);
        setError("");
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(loadError instanceof Error ? loadError.message : "Nu s-au putut încărca echipele meciului.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void loadRobots();
    return () => controller.abort();
  }, [videoId]);

  useEffect(() => {
    const search = query.trim();
    if (!search) {
      setResults([]);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const params = new URLSearchParams({ search });
        const response = await fetch(`${apiBase}/api/v1/teams/directory?${params}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) {
          const body = await response.json().catch(() => null) as { detail?: string } | null;
          throw new Error(body?.detail ?? "Căutarea echipelor FTCScout a eșuat.");
        }
        setResults((await response.json() as Team[]).slice(0, 20));
        setError("");
      } catch (searchError) {
        if (!controller.signal.aborted) {
          setResults([]);
          setError(searchError instanceof Error ? searchError.message : "Căutarea echipelor FTCScout a eșuat.");
        }
      }
    }, 250);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  async function saveRoster(nextRobots: Array<Pick<FieldRobot, "team_number" | "team_name" | "alliance">>) {
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/api/v1/videos/${videoId}/field-robots`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ robots: nextRobots }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Echipele de pe teren nu au putut fi salvate.");
      }
      setRobots(await response.json() as FieldRobot[]);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Echipele de pe teren nu au putut fi salvate.");
    } finally {
      setSaving(false);
    }
  }

  function addRobot(team: Team) {
    if (saving || robots.length >= 6 || robots.some((robot) => robot.team_number === team.number)) return;
    if (robots.filter((robot) => robot.alliance === alliance).length >= 3) {
      setError(`Alianța ${alliance === "Blue" ? "albastră" : "roșie"} are deja trei echipe.`);
      return;
    }
    setQuery("");
    setResults([]);
    void saveRoster([...robots.map(({ team_number, team_name, alliance: teamAlliance }) => ({
      team_number,
      team_name,
      alliance: teamAlliance,
    })), { team_number: team.number, team_name: team.name, alliance }]);
  }

  function removeRobot(robot: FieldRobot) {
    if (saving) return;
    void saveRoster(robots
      .filter((item) => item.team_number !== robot.team_number)
      .map(({ team_number, team_name, alliance: teamAlliance }) => ({
        team_number,
        team_name,
        alliance: teamAlliance,
      })));
  }

  const blueRobots = robots.filter((robot) => robot.alliance === "Blue");
  const redRobots = robots.filter((robot) => robot.alliance === "Red");

  return (
    <section className="field-robots" aria-labelledby={`field-robots-title-${videoId}`}>
      <div className="timeline-head">
        <h3 id={`field-robots-title-${videoId}`}><Users aria-hidden="true" /> Echipele de pe teren</h3>
        <span>{robots.length} din 6 · selecție manuală</span>
      </div>

      <div className="field-robot-alliances">
        {(["Blue", "Red"] as const).map((side) => {
          const sideRobots = side === "Blue" ? blueRobots : redRobots;
          return (
            <div className={`field-robot-alliance ${side.toLowerCase()}`} key={side}>
              <h4>{side === "Blue" ? "Alianța albastră" : "Alianța roșie"} <span>{sideRobots.length}/3</span></h4>
              {sideRobots.length === 0 ? <p className="field-robot-empty">Adaugă echipele care au apărut în video.</p> : (
                <ul className="field-robot-list">
                  {sideRobots.map((robot) => (
                    <li key={robot.team_number}>
                      <span className="field-robot-number">{robot.team_number}</span>
                      <span className="field-robot-name">{robot.team_name}</span>
                      <button
                        className="icon-button"
                        type="button"
                        disabled={saving}
                        onClick={() => removeRobot(robot)}
                        aria-label={`Elimină echipa ${robot.team_number}`}
                      >
                        <Trash2 aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      <div className="field-robot-editor">
        <label className="field-robot-alliance-select">
          Alianță
          <select value={alliance} onChange={(event) => setAlliance(event.target.value as Alliance)}>
            <option value="Blue">Albastră</option>
            <option value="Red">Roșie</option>
          </select>
        </label>
        <label className="field-robot-search">
          <Search aria-hidden="true" />
          <input
            type="search"
            aria-label="Caută robot după număr sau nume"
            placeholder="Caută echipă după număr sau nume"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={loading || saving || robots.length >= 6}
          />
          {saving && <LoaderCircle className="spin" aria-label="Se salvează" />}
        </label>
      </div>

      {query.trim() && results.length > 0 && (
        <ul className="field-robot-results" aria-label="Rezultate FTCScout">
          {results
            .filter((team) => !robots.some((robot) => robot.team_number === team.number))
            .map((team) => (
              <li key={team.number}>
                <span><strong>{team.number}</strong> · {team.name}</span>
                <button className="subtle-button" type="button" onClick={() => addRobot(team)} disabled={saving || robots.filter((robot) => robot.alliance === alliance).length >= 3}>
                  <Plus aria-hidden="true" /> Adaugă
                </button>
              </li>
            ))}
        </ul>
      )}

      {query.trim() && !loading && results.length === 0 && !error && (
        <p className="field-robot-empty">Nu am găsit echipe pentru „{query}”.</p>
      )}
      {loading && <p className="field-robot-empty">Se încarcă echipele salvate…</p>}
      {robots.length >= 6 && <p className="field-robot-empty">Sunt completate toate cele șase poziții.</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  );
}
