import { useMemo } from "react";
import SortTable, { type SortColumn } from "../components/SortTable";
import { useData } from "../data";
import type { DraftFile, DraftPick, SeasonSummary, UndraftedPlayer } from "../types";

type View = "picks" | "teams" | "undrafted";

interface Props {
  season: SeasonSummary;
  params: URLSearchParams;
  onParamsChange: (updates: Record<string, string | undefined>) => void;
}

interface TeamSummary {
  team_key: string;
  name: string;
  picks: number;
  avgValue: number | null;
  best: DraftPick | null;
  worst: DraftPick | null;
}

const HIGHLIGHTS = 5;

function formatValue(value: number | null): string {
  if (value === null) return "–";
  return value > 0 ? `+${value}` : String(value);
}

function valueClass(value: number | null): string | undefined {
  if (value === null || value === 0) return undefined;
  return value > 0 ? "good" : "bad";
}

function Value({ value }: { value: number | null }) {
  return <span className={`value ${valueClass(value) ?? ""}`}>{formatValue(value)}</span>;
}

function summarizeTeams(picks: DraftPick[], names: Map<string, string>): TeamSummary[] {
  const byTeam = new Map<string, DraftPick[]>();
  for (const pick of picks) {
    byTeam.set(pick.team_key, [...(byTeam.get(pick.team_key) ?? []), pick]);
  }
  return [...byTeam].map(([team_key, teamPicks]) => {
    const valued = teamPicks.filter((p) => p.value !== null);
    const byValue = [...valued].sort((a, b) => b.value! - a.value!);
    return {
      team_key,
      name: names.get(team_key) ?? team_key,
      picks: teamPicks.length,
      avgValue: valued.length
        ? valued.reduce((sum, p) => sum + p.value!, 0) / valued.length
        : null,
      best: byValue[0] ?? null,
      worst: byValue[byValue.length - 1] ?? null,
    };
  });
}

export default function Draft({ season, params, onParamsChange }: Props) {
  const file = useData<DraftFile>(season.has_draft ? `${season.year}/draft.json` : null);

  const view = (["picks", "teams", "undrafted"] as const).includes(params.get("view") as View)
    ? (params.get("view") as View)
    : "picks";
  const team = params.get("team") ?? "";
  const round = params.get("round") ?? "";
  const position = params.get("pos") ?? "";

  const data = useMemo(() => {
    if (file.status !== "ready") return null;
    const { picks, teams } = file.data;
    const names = new Map(teams.map((t) => [t.team_key, t.name]));
    const valued = picks.filter((p) => p.value !== null);
    const byValue = [...valued].sort((a, b) => b.value! - a.value!);
    const positions = [...new Set(picks.flatMap((p) => p.position.split(",")))]
      .filter(Boolean)
      .sort();
    const rounds = [...new Set(picks.map((p) => p.round))].sort((a, b) => a - b);
    return {
      names,
      steals: byValue.slice(0, HIGHLIGHTS),
      busts: byValue.slice(-HIGHLIGHTS).reverse(),
      teams: summarizeTeams(picks, names),
      positions,
      rounds,
    };
  }, [file]);

  if (!season.has_draft) return <p className="status">No draft results for {season.year}.</p>;
  if (file.status === "loading") return <p className="status">Loading draft…</p>;
  if (file.status === "error") return <p className="status">Couldn't load draft: {file.error}</p>;
  if (!data) return null;

  const { picks, undrafted, num_picks } = file.data;
  const nameOf = (key: string) => data.names.get(key) ?? key;

  const filteredPicks = picks.filter(
    (p) =>
      (!team || p.team_key === team) &&
      (!round || p.round === Number(round)) &&
      (!position || p.position.split(",").includes(position)),
  );

  const pickColumns: SortColumn<DraftPick>[] = [
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
      key: "value",
      label: "Value",
      title: "Pick minus season rank",
      numeric: true,
      startAscending: false,
      value: (p) => p.value,
      render: (p) => <Value value={p.value} />,
    },
    { key: "team", label: "Team", value: (p) => nameOf(p.team_key) },
    { key: "round", label: "Rd", title: "Round", numeric: true, startAscending: true, value: (p) => p.round },
  ];

  const pickLabel = (p: DraftPick | null) =>
    p ? (
      <span className="player">
        {p.name} <Value value={p.value} />
        <span className="player-meta">
          Pick {p.pick} → rank {p.rank ?? "–"}
        </span>
      </span>
    ) : (
      "–"
    );

  const teamColumns: SortColumn<TeamSummary>[] = [
    { key: "team", label: "Team", value: (t) => t.name, className: "team" },
    {
      key: "avg",
      label: "Avg value",
      title: "Average value per pick",
      numeric: true,
      startAscending: false,
      value: (t) => t.avgValue,
      render: (t) => (
        <span className={`value ${valueClass(t.avgValue === null ? null : Math.round(t.avgValue)) ?? ""}`}>
          {t.avgValue === null ? "–" : `${t.avgValue > 0 ? "+" : ""}${t.avgValue.toFixed(1)}`}
        </span>
      ),
    },
    { key: "best", label: "Best pick", value: (t) => t.best?.value, render: (t) => pickLabel(t.best) },
    {
      key: "worst",
      label: "Worst pick",
      startAscending: true,
      value: (t) => t.worst?.value,
      render: (t) => pickLabel(t.worst),
    },
  ];

  const undraftedColumns: SortColumn<UndraftedPlayer>[] = [
    { key: "rank", label: "Rank", title: "Season rank", numeric: true, startAscending: true, value: (p) => p.rank },
    { key: "player", label: "Player", value: (p) => p.name, className: "team" },
    { key: "pos", label: "Pos", title: "Position", value: (p) => p.position },
    { key: "mlb", label: "MLB", title: "MLB team", value: (p) => p.mlb_team },
  ];

  const set = (updates: Record<string, string | undefined>) => onParamsChange(updates);

  return (
    <>
      <div className="highlights">
        {(
          [
            ["Steals", data.steals],
            ["Busts", data.busts],
          ] as const
        ).map(([title, list]) => (
          <section key={title} className="card highlight">
            <h2 className="section-title">{title}</h2>
            <ol>
              {list.map((p) => (
                <li key={p.player_key}>
                  <span className="player">
                    {p.name}
                    <span className="player-meta">
                      {nameOf(p.team_key)} · pick {p.pick} → rank {p.rank}
                    </span>
                  </span>
                  <Value value={p.value} />
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <section className="card">
        <div className="segmented" role="tablist" aria-label="View">
          {(
            [
              ["picks", "All picks"],
              ["teams", "By team"],
              ["undrafted", "Undrafted"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={view === id}
              className={view === id ? "active" : undefined}
              onClick={() => set({ view: id === "picks" ? undefined : id })}
            >
              {label}
            </button>
          ))}
        </div>

        {view === "picks" && (
          <>
            <div className="filters">
              <label>
                <span>Team</span>
                <select value={team} onChange={(e) => set({ team: e.target.value || undefined })}>
                  <option value="">All teams</option>
                  {[...file.data.teams]
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
                  {data.rounds.map((r) => (
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
                  {data.positions.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <SortTable
              className="draft-table"
              columns={pickColumns}
              rows={filteredPicks}
              rowKey={(p) => String(p.pick)}
              initialSort={{ key: "pick", asc: true }}
            />
          </>
        )}

        {view === "teams" && (
          <SortTable
            className="draft-table"
            columns={teamColumns}
            rows={data.teams}
            rowKey={(t) => t.team_key}
            initialSort={{ key: "avg", asc: false }}
          />
        )}

        {view === "undrafted" && (
          <SortTable
            className="draft-table"
            columns={undraftedColumns}
            rows={undrafted}
            rowKey={(p) => p.player_key}
            initialSort={{ key: "rank", asc: true }}
          />
        )}

        <p className="note">
          {view === "undrafted"
            ? "The best-ranked players nobody drafted."
            : `Value is draft pick minus season rank: positive means the player outperformed the pick. Ranks past ${num_picks} count as ${num_picks + 1}.`}{" "}
          Season rank is Yahoo's ranking for this league.
        </p>
      </section>
    </>
  );
}
