import { useMemo } from "react";
import SortTable, { type SortColumn } from "../components/SortTable";
import { useData } from "../data";
import { formatDate } from "../format";
import type { DraftFile, DraftPick, SeasonSummary } from "../types";

type Kept = "" | "kept" | "drop" | "trade";

interface Props {
  season: SeasonSummary;
  params: URLSearchParams;
  onParamsChange: (updates: Record<string, string | undefined>) => void;
}

const KEPT_OPTIONS: { id: Kept; label: string }[] = [
  { id: "", label: "Any" },
  { id: "kept", label: "Kept all season" },
  { id: "drop", label: "Dropped" },
  { id: "trade", label: "Traded" },
];

/** "Kept all season", or "Dropped Mar 27 → Zach". */
function tenureText(pick: DraftPick, nameOf: (key: string) => string): string {
  const { left, left_date, next_team_key } = pick.tenure;
  if (!left) return "Kept all season";
  const verb = left === "trade" ? "Traded" : "Dropped";
  const next = next_team_key ? ` → ${nameOf(next_team_key)}` : "";
  return `${verb} ${formatDate(left_date)}${next}`;
}

export default function Draft({ season, params, onParamsChange }: Props) {
  const file = useData<DraftFile>(season.has_draft ? `${season.year}/draft.json` : null);

  const team = params.get("team") ?? "";
  const round = params.get("round") ?? "";
  const position = params.get("pos") ?? "";
  const kept = (params.get("kept") ?? "") as Kept;

  const options = useMemo(() => {
    if (file.status !== "ready") return null;
    const { picks, teams } = file.data;
    return {
      names: new Map(teams.map((t) => [t.team_key, t.name])),
      byPick: new Map(picks.map((p) => [p.pick, p])),
      positions: [...new Set(picks.flatMap((p) => p.position.split(",")))].filter(Boolean).sort(),
      rounds: [...new Set(picks.map((p) => p.round))].sort((a, b) => a - b),
    };
  }, [file]);

  if (!season.has_draft) return <p className="status">No draft results for {season.year}.</p>;
  if (file.status === "loading") return <p className="status">Loading draft…</p>;
  if (file.status === "error") return <p className="status">Couldn't load draft: {file.error}</p>;
  if (!options) return null;

  const { picks, teams, steals, busts } = file.data;
  const nameOf = (key: string) => options.names.get(key) ?? key;

  const filtered = picks.filter(
    (p) =>
      (!team || p.team_key === team) &&
      (!round || p.round === Number(round)) &&
      (!position || p.position.split(",").includes(position)) &&
      (!kept || (kept === "kept" ? p.tenure.left === null : p.tenure.left === kept)),
  );

  const columns: SortColumn<DraftPick>[] = [
    { key: "pick", label: "Pick", numeric: true, startAscending: true, value: (p) => p.pick },
    {
      key: "player",
      label: "Player",
      value: (p) => p.name,
      render: (p) => (
        <span className="player">
          {p.name}
          <span className="player-meta">
            {p.position}
            {p.mlb_team && ` · ${p.mlb_team}`}
          </span>
        </span>
      ),
      className: "team",
    },
    {
      key: "rank",
      label: "Rank",
      title: "Season rank",
      numeric: true,
      startAscending: true,
      value: (p) => p.rank,
    },
    {
      key: "kept",
      label: "Kept",
      title: "How long the drafting team kept him",
      numeric: false,
      startAscending: false,
      value: (p) => p.tenure.kept_share,
      render: (p) => (
        <span className={p.tenure.left ? "tenure moved" : "tenure"}>{tenureText(p, nameOf)}</span>
      ),
    },
    { key: "team", label: "Team", value: (p) => nameOf(p.team_key) },
    { key: "round", label: "Rd", title: "Round", numeric: true, startAscending: true, value: (p) => p.round },
  ];

  const set = (updates: Record<string, string | undefined>) => onParamsChange(updates);

  const highlight = (title: string, subtitle: string, list: number[]) => (
    <section className="card highlight">
      <h2 className="section-title">{title}</h2>
      <p className="note highlight-note">{subtitle}</p>
      {list.length === 0 ? (
        <p className="note">None this season.</p>
      ) : (
        <ol>
          {list.map((n) => {
            const p = options.byPick.get(n)!;
            return (
              <li key={n}>
                <span className="player">
                  {p.name}
                  <span className="player-meta">
                    {nameOf(p.team_key)} · round {p.round}, pick {p.pick}
                  </span>
                </span>
                <span className="rank-badge">#{p.rank ?? "–"}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );

  return (
    <>
      <div className="highlights">
        {highlight("Steals", "Round 10 or later, kept most of the season", steals)}
        {highlight("Busts", "First 5 rounds, finished outside the top 300", busts)}
      </div>

      <section className="card">
        <div className="filters">
          <label>
            <span>Team</span>
            <select value={team} onChange={(e) => set({ team: e.target.value || undefined })}>
              <option value="">All teams</option>
              {[...teams]
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((t) => (
                  <option key={t.team_key} value={t.team_key}>
                    {t.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            <span>Round</span>
            <select value={round} onChange={(e) => set({ round: e.target.value || undefined })}>
              <option value="">All rounds</option>
              {options.rounds.map((r) => (
                <option key={r} value={r}>
                  Round {r}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Position</span>
            <select value={position} onChange={(e) => set({ pos: e.target.value || undefined })}>
              <option value="">All positions</option>
              {options.positions.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Kept</span>
            <select value={kept} onChange={(e) => set({ kept: e.target.value || undefined })}>
              {KEPT_OPTIONS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <SortTable
          className="draft-table"
          columns={columns}
          rows={filtered}
          rowKey={(p) => String(p.pick)}
          initialSort={{ key: "pick", asc: true }}
        />

        <p className="note">
          Rank is the player's Yahoo season rank in this league. Kept shows whether the drafting
          team held on to him; see Moves for every add, drop and trade.
        </p>
      </section>
    </>
  );
}
