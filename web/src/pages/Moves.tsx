import { useMemo, useState } from "react";
import SortTable, { type SortColumn } from "../components/SortTable";
import { useData } from "../data";
import { formatDate } from "../format";
import type { Move, MoveEntry, MovesFile, SeasonSummary, Stint } from "../types";

type View = "log" | "teams" | "pickups";
type Action = "" | Move["action"];

interface Props {
  season: SeasonSummary;
  params: URLSearchParams;
  onParamsChange: (updates: Record<string, string | undefined>) => void;
}

interface TeamActivity {
  team_key: string;
  name: string;
  adds: number;
  drops: number;
  trades: number;
}

const PAGE_SIZE = 100;
const MOST_ADDED = 5;
const PITCHER_POSITIONS = new Set(["SP", "RP", "P"]);

interface AddCount {
  player_key: string;
  adds: number;
  teams: number;
}

/** Pitchers are players eligible only at pitching positions (two-way players count as batters). */
function isPitcher(position: string): boolean {
  const positions = position.split(",").filter(Boolean);
  return positions.length > 0 && positions.every((p) => PITCHER_POSITIONS.has(p));
}

const ACTIONS: { id: Action; label: string }[] = [
  { id: "", label: "All moves" },
  { id: "add", label: "Adds" },
  { id: "drop", label: "Drops" },
  { id: "trade", label: "Trades" },
  { id: "draft", label: "Draft picks" },
];

function days(stint: Stint, seasonEnd: string): number {
  const end = new Date(stint.end ?? seasonEnd).getTime();
  return (end - new Date(stint.start).getTime()) / 86_400_000;
}

export default function Moves({ season, params, onParamsChange }: Props) {
  const file = useData<MovesFile>(season.has_moves ? `${season.year}/moves.json` : null);
  const [shown, setShown] = useState(PAGE_SIZE);

  const view = (["log", "teams", "pickups"] as const).includes(params.get("view") as View)
    ? (params.get("view") as View)
    : "log";
  const team = params.get("team") ?? "";
  const action = (params.get("type") ?? "") as Action;
  const search = params.get("q") ?? "";

  const data = useMemo(() => {
    if (file.status !== "ready") return null;
    const { teams, transactions } = file.data;
    const names = new Map(teams.map((t) => [t.team_key, t.name]));
    const activity = new Map<string, TeamActivity>(
      teams.map((t) => [t.team_key, { team_key: t.team_key, name: t.name, adds: 0, drops: 0, trades: 0 }]),
    );
    const addedBy = new Map<string, string[]>();
    for (const entry of transactions) {
      const traders = new Set<string>();
      for (const m of entry.moves) {
        if (m.action === "add" && m.to_team_key) {
          activity.get(m.to_team_key)!.adds++;
          addedBy.set(m.player_key, [...(addedBy.get(m.player_key) ?? []), m.to_team_key]);
        }
        if (m.action === "drop" && m.from_team_key) activity.get(m.from_team_key)!.drops++;
        if (m.action === "trade") {
          if (m.from_team_key) traders.add(m.from_team_key);
          if (m.to_team_key) traders.add(m.to_team_key);
        }
      }
      for (const key of traders) activity.get(key)!.trades++;
    }
    // The last date anyone moved, standing in for "end of season" in stint lengths.
    const lastDate = transactions.find((e) => e.type !== "draft")?.date ?? "";
    // Most-added players, split into batters and pitchers; ties go to the better season rank.
    const counts: AddCount[] = [...addedBy].map(([player_key, teamKeys]) => ({
      player_key,
      adds: teamKeys.length,
      teams: new Set(teamKeys).size,
    }));
    const rankOf = (c: AddCount) => file.data.players[c.player_key]?.rank ?? Infinity;
    counts.sort((a, b) => b.adds - a.adds || rankOf(a) - rankOf(b));
    const pitcher = (c: AddCount) => isPitcher(file.data.players[c.player_key]?.position ?? "");
    const mostAdded = {
      batters: counts.filter((c) => !pitcher(c)).slice(0, MOST_ADDED),
      pitchers: counts.filter(pitcher).slice(0, MOST_ADDED),
    };
    return { names, activity: [...activity.values()], lastDate, mostAdded };
  }, [file]);

  if (!season.has_moves) return <p className="status">No moves for {season.year}.</p>;
  if (file.status === "loading") return <p className="status">Loading moves…</p>;
  if (file.status === "error") return <p className="status">Couldn't load moves: {file.error}</p>;
  if (!data) return null;

  const { teams, transactions, players, top_pickups } = file.data;
  const nameOf = (key: string | undefined) => (key ? (data.names.get(key) ?? key) : "");
  const set = (updates: Record<string, string | undefined>) => {
    setShown(PAGE_SIZE);
    onParamsChange(updates);
  };

  const query = search.trim().toLowerCase();
  const matches = (m: Move) =>
    (!team || m.from_team_key === team || m.to_team_key === team) &&
    (!action || m.action === action) &&
    (!query || players[m.player_key]?.name.toLowerCase().includes(query));
  const filtered = transactions.filter((e) => e.moves.some(matches));

  const describe = (entry: MoveEntry, m: Move) => {
    const p = players[m.player_key];
    const who = (
      <span className="move-player">
        {p?.name ?? m.player_key}
        <span className="player-meta">
          {" "}
          {p?.position}
          {p?.rank ? ` · #${p.rank}` : ""}
        </span>
      </span>
    );
    switch (m.action) {
      case "draft":
        return (
          <>
            <b>{nameOf(m.to_team_key)}</b> drafted {who}, round {entry.round} pick {entry.pick}
          </>
        );
      case "add":
        return (
          <>
            <b>{nameOf(m.to_team_key)}</b> added {who}
            {m.via === "waivers" ? " off waivers" : ""}
          </>
        );
      case "drop":
        return (
          <>
            <b>{nameOf(m.from_team_key)}</b> dropped {who}
          </>
        );
      case "trade":
        return (
          <>
            <b>{nameOf(m.from_team_key)}</b> traded {who} to <b>{nameOf(m.to_team_key)}</b>
          </>
        );
    }
  };

  const stintText = (s: Stint) => {
    const how = s.acquired === "draft" ? "drafted" : s.acquired === "trade" ? "traded for" : "added";
    const until = s.end ? `${formatDate(s.end)}` : "end";
    return `${nameOf(s.team_key)} (${how} ${formatDate(s.start)}–${until})`;
  };

  // Credit each pickup to the team that held him longest after adding him.
  const keeper = (stints: Stint[]) =>
    [...stints]
      .filter((s) => s.acquired !== "draft")
      .sort((a, b) => days(b, data.lastDate) - days(a, data.lastDate))[0];

  const teamColumns: SortColumn<TeamActivity>[] = [
    { key: "team", label: "Team", value: (t) => t.name, className: "team" },
    { key: "adds", label: "Adds", numeric: true, value: (t) => t.adds },
    { key: "drops", label: "Drops", numeric: true, value: (t) => t.drops },
    { key: "trades", label: "Trades", numeric: true, value: (t) => t.trades },
  ];

  const pickupColumns: SortColumn<(typeof top_pickups)[number]>[] = [
    {
      key: "rank",
      label: "Rank",
      title: "Season rank",
      numeric: true,
      startAscending: true,
      value: (p) => players[p.player_key]?.rank,
    },
    {
      key: "player",
      label: "Player",
      value: (p) => players[p.player_key]?.name,
      render: (p) => (
        <span className="player">
          {players[p.player_key]?.name}
          <span className="player-meta">
            {players[p.player_key]?.position}
            {players[p.player_key]?.mlb_team && ` · ${players[p.player_key].mlb_team}`}
          </span>
        </span>
      ),
      className: "team",
    },
    {
      key: "teams",
      label: "Rostered by",
      value: (p) => p.stints.length,
      render: (p) => {
        const credited = keeper(p.stints);
        return (
          <span className="stints">
            {p.stints.map((s, i) =>
              s === credited ? <b key={i}>{stintText(s)}</b> : <span key={i}>{stintText(s)}</span>,
            )}
          </span>
        );
      },
    },
  ];

  const mostAddedCard = (title: string, list: AddCount[]) => (
    <section className="card highlight">
      <h2 className="section-title">{title}</h2>
      {list.length === 0 ? (
        <p className="note">No adds this season.</p>
      ) : (
        <ol>
          {list.map((c) => {
            const p = players[c.player_key];
            return (
              <li key={c.player_key}>
                <span className="player">
                  {p?.name ?? c.player_key}
                  <span className="player-meta">
                    {p?.position}
                    {p?.rank ? ` · #${p.rank}` : ""}
                  </span>
                </span>
                <span className="add-count">
                  {c.adds}×
                  <span className="player-meta">
                    {c.teams} {c.teams === 1 ? "team" : "teams"}
                  </span>
                </span>
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
        {mostAddedCard("Most added batters", data.mostAdded.batters)}
        {mostAddedCard("Most added pitchers", data.mostAdded.pitchers)}
      </div>

      <section className="card">
        <div className="segmented" role="tablist" aria-label="View">
          {(
            [
              ["log", "All moves"],
              ["teams", "By team"],
              ["pickups", "Top pickups"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={view === id}
              className={view === id ? "active" : undefined}
              onClick={() => set({ view: id === "log" ? undefined : id })}
            >
              {label}
            </button>
          ))}
        </div>

        {view === "log" && (
          <>
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
                <span>Type</span>
                <select value={action} onChange={(e) => set({ type: e.target.value || undefined })}>
                  {ACTIONS.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="search">
                <span>Player</span>
                <input
                  type="search"
                  placeholder="Search players"
                  value={search}
                  onChange={(e) => set({ q: e.target.value || undefined })}
                />
              </label>
            </div>

            {filtered.length === 0 ? (
              <p className="status">No moves match.</p>
            ) : (
              <ol className="move-log">
                {filtered.slice(0, shown).map((entry, i, list) => (
                  <li key={entry.id}>
                    {(i === 0 || list[i - 1].date !== entry.date) && (
                      <h3 className="move-date">
                        {formatDate(entry.date)}
                        {entry.type === "draft" && " · Draft"}
                      </h3>
                    )}
                    <div className={`move move-${entry.type.replace("/", "-")}`}>
                      {entry.moves.filter(matches).map((m) => (
                        <p key={m.player_key + m.action}>
                          <span className={`move-badge ${m.action}`}>{m.action}</span>
                          <span>{describe(entry, m)}</span>
                        </p>
                      ))}
                    </div>
                  </li>
                ))}
              </ol>
            )}
            {filtered.length > shown && (
              <button type="button" className="more" onClick={() => setShown((n) => n + PAGE_SIZE)}>
                Show more ({filtered.length - shown} left)
              </button>
            )}
          </>
        )}

        {view === "teams" && (
          <SortTable
            columns={teamColumns}
            rows={data.activity}
            rowKey={(t) => t.team_key}
            initialSort={{ key: "adds", asc: false }}
          />
        )}

        {view === "pickups" && (
          <SortTable
            className="draft-table"
            columns={pickupColumns}
            rows={top_pickups}
            rowKey={(p) => p.player_key}
            initialSort={{ key: "rank", asc: true }}
          />
        )}
        {view === "pickups" && (
          <p className="note">
            The best-ranked players added during the season. Bold marks the team credited with the
            pickup: whoever held him longest after adding him.
          </p>
        )}
      </section>
    </>
  );
}
