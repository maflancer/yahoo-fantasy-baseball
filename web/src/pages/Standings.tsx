import { useMemo, useState } from "react";
import { useData } from "../data";
import type { SeasonSummary, StandingsFile, StandingsRow } from "../types";

type SortKey = "rank" | "name" | "wins" | "losses" | "ties" | "percentage" | "games_back" | "playoff_seed";

const COLUMNS: { key: SortKey; label: string; title?: string; numeric?: boolean }[] = [
  { key: "rank", label: "#", title: "Rank", numeric: true },
  { key: "name", label: "Team" },
  { key: "wins", label: "W", title: "Wins", numeric: true },
  { key: "losses", label: "L", title: "Losses", numeric: true },
  { key: "ties", label: "T", title: "Ties", numeric: true },
  { key: "percentage", label: "Pct", title: "Win percentage", numeric: true },
  { key: "games_back", label: "GB", title: "Games back", numeric: true },
  { key: "playoff_seed", label: "Seed", title: "Playoff seed", numeric: true },
];

const ASCENDING_FIRST = new Set<SortKey>(["rank", "name", "losses", "games_back", "playoff_seed"]);

type Row = StandingsRow & { name: string };

function sortValue(row: Row, key: SortKey): number | string {
  const value = row[key];
  if (key === "name") return String(value).toLowerCase();
  if (value === null || value === "-" || value === "") return key === "games_back" ? 0 : Infinity;
  return Number(value);
}

export default function Standings({ season }: { season: SeasonSummary }) {
  const file = useData<StandingsFile>(`${season.year}/standings.json`);
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: "rank", asc: true });

  const rows = useMemo(() => {
    if (file.status !== "ready") return [];
    const names = new Map(file.data.teams.map((t) => [t.team_key, t.name]));
    const withNames: Row[] = file.data.standings.map((r) => ({
      ...r,
      name: names.get(r.team_key) ?? r.team_key,
    }));
    return withNames.sort((a, b) => {
      const x = sortValue(a, sort.key);
      const y = sortValue(b, sort.key);
      const cmp = x < y ? -1 : x > y ? 1 : 0;
      return sort.asc ? cmp : -cmp;
    });
  }, [file, sort]);

  if (file.status === "loading") return <p className="status">Loading standings…</p>;
  if (file.status === "error") return <p className="status">Couldn't load standings: {file.error}</p>;

  // First click sorts "best first": ascending for rank-like columns, descending for wins/pct.
  const onSort = (key: SortKey) =>
    setSort((s) => ({ key, asc: s.key === key ? !s.asc : ASCENDING_FIRST.has(key) }));

  return (
    <section className="card">
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  title={c.title}
                  className={c.numeric ? "num" : undefined}
                  aria-sort={sort.key === c.key ? (sort.asc ? "ascending" : "descending") : undefined}
                >
                  <button type="button" onClick={() => onSort(c.key)}>
                    {c.label}
                    <span className="sort-indicator" aria-hidden>
                      {sort.key === c.key ? (sort.asc ? "▲" : "▼") : ""}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.team_key}>
                <td className="num rank">{r.rank ?? "–"}</td>
                <td className="team">{r.name}</td>
                <td className="num">{r.wins}</td>
                <td className="num">{r.losses}</td>
                <td className="num">{r.ties}</td>
                <td className="num mono">{r.percentage}</td>
                <td className="num">{r.games_back}</td>
                <td className="num">{r.playoff_seed ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {season.is_finished && (
        <p className="note">Final standings, including playoff results.</p>
      )}
    </section>
  );
}
