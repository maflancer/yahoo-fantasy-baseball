import { useMemo, useState } from "react";
import { useData } from "../data";
import { bestValue, formatStat, totalsByTeam } from "../stats";
import type { SeasonSummary, StatsCategory, StatsFile, StatsRow } from "../types";

type View = "totals" | "log";
type Period = "all" | "regular" | "playoffs" | "range";
type Group = "all" | "B" | "P";

interface Props {
  season: SeasonSummary;
  params: URLSearchParams;
  onParamsChange: (updates: Record<string, string | undefined>) => void;
}

interface Column {
  key: string;
  label: string;
  title?: string;
  numeric: boolean;
  /** Direction for the first click: best values first. */
  startAscending: boolean;
  /** Stat category, for formatting and best-value highlighting. */
  cat?: StatsCategory;
}

/** A table row: either a team's totals or a single team-week. */
interface TableRow {
  id: string;
  cells: Record<string, string | number | null>;
}

const PERIODS: { id: Period; label: string }[] = [
  { id: "all", label: "Full season" },
  { id: "regular", label: "Regular season" },
  { id: "playoffs", label: "Playoffs" },
  { id: "range", label: "Custom weeks" },
];

const GROUPS: { id: Group; label: string }[] = [
  { id: "all", label: "All stats" },
  { id: "B", label: "Batting" },
  { id: "P", label: "Pitching" },
];

function oneOf<T extends string>(value: string | null, options: readonly T[], fallback: T): T {
  return options.includes(value as T) ? (value as T) : fallback;
}

export default function Stats({ season, params, onParamsChange }: Props) {
  const file = useData<StatsFile>(`${season.year}/stats.json`);

  const view = oneOf<View>(params.get("view"), ["totals", "log"], "totals");
  const period = oneOf<Period>(params.get("period"), ["all", "regular", "playoffs", "range"], "all");
  const group = oneOf<Group>(params.get("group"), ["all", "B", "P"], "all");
  const perWeek = params.get("per") === "week";
  const team = params.get("team") ?? "";

  const [sort, setSort] = useState<{ key: string; asc: boolean } | null>(null);

  const weeks = useMemo(
    () =>
      file.status === "ready" ? [...new Set(file.data.rows.map((r) => r.week))].sort((a, b) => a - b) : [],
    [file],
  );
  const from = Number(params.get("from")) || weeks[0];
  const to = Number(params.get("to")) || weeks[weeks.length - 1];

  const table = useMemo(() => {
    if (file.status !== "ready") return null;
    const { teams, categories, rows } = file.data;
    const names = new Map(teams.map((t) => [t.team_key, t.name]));
    const cats = categories.filter((c) => group === "all" || c.position_type === group);

    const inPeriod = (r: StatsRow) =>
      period === "regular"
        ? !r.is_playoffs
        : period === "playoffs"
          ? r.is_playoffs
          : period === "range"
            ? r.week >= Math.min(from, to) && r.week <= Math.max(from, to)
            : true;
    const selected = rows.filter(inPeriod);

    const statColumns: Column[] = cats.map((cat) => ({
      key: cat.abbr,
      label: cat.abbr,
      title: cat.name,
      numeric: true,
      startAscending: !cat.higher_is_better,
      cat,
    }));

    let columns: Column[];
    let tableRows: TableRow[];
    if (view === "totals") {
      columns = [
        { key: "team", label: "Team", numeric: false, startAscending: true },
        { key: "weeks", label: "Wks", title: "Weeks played", numeric: true, startAscending: false },
        ...statColumns,
      ];
      tableRows = totalsByTeam(selected, cats, perWeek).map((t) => ({
        id: t.team_key,
        cells: { team: names.get(t.team_key) ?? t.team_key, weeks: t.weeks, ...t.values },
      }));
    } else {
      columns = [
        { key: "week", label: "Wk", title: "Week", numeric: true, startAscending: true },
        { key: "team", label: "Team", numeric: false, startAscending: true },
        { key: "opp", label: "Opp", title: "Opponent", numeric: false, startAscending: true },
        { key: "result", label: "Result", numeric: false, startAscending: true },
        ...statColumns,
      ];
      tableRows = selected
        .filter((r) => !team || r.team_key === team)
        .map((r) => ({
          id: `${r.week}-${r.team_key}`,
          cells: {
            week: r.week,
            team: names.get(r.team_key) ?? r.team_key,
            opp: r.opponent_key ? (names.get(r.opponent_key) ?? r.opponent_key) : "–",
            result: `${r.result} ${r.score[0]}–${r.score[1]}`,
            ...r.values,
          },
        }));
    }

    const best = new Map(
      statColumns.map((c) => [
        c.key,
        bestValue(
          tableRows.map((r) => r.cells[c.key] as number | null),
          c.cat!.higher_is_better,
        ),
      ]),
    );
    const approximate = cats.some((c) => c.agg.type === "weighted") && view === "totals";
    return { columns, tableRows, best, approximate, teams };
  }, [file, view, period, group, perWeek, team, from, to]);

  if (file.status === "loading") return <p className="status">Loading stats…</p>;
  if (file.status === "error") return <p className="status">Couldn't load stats: {file.error}</p>;
  if (!table) return null;

  const { columns, tableRows, best, approximate, teams } = table;
  const activeSort =
    sort && columns.some((c) => c.key === sort.key)
      ? sort
      : view === "totals"
        ? { key: columns[2]?.key ?? "team", asc: columns[2]?.startAscending ?? true }
        : { key: "week", asc: true };

  const sorted = [...tableRows].sort((a, b) => {
    const x = a.cells[activeSort.key];
    const y = b.cells[activeSort.key];
    // Missing values always sink to the bottom.
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    const cmp =
      typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
    return activeSort.asc ? cmp : -cmp;
  });

  const onSort = (col: Column) =>
    setSort({
      key: col.key,
      asc: activeSort.key === col.key ? !activeSort.asc : col.startAscending,
    });

  const set = (updates: Record<string, string | undefined>) => onParamsChange(updates);

  return (
    <section className="card">
      <div className="segmented" role="tablist" aria-label="View">
        {(
          [
            ["totals", "Season totals"],
            ["log", "Weekly log"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={view === id}
            className={view === id ? "active" : undefined}
            onClick={() => {
              setSort(null);
              set({ view: id === "totals" ? undefined : id });
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="filters">
        <label>
          <span>Weeks</span>
          <select
            value={period}
            onChange={(e) => set({ period: e.target.value === "all" ? undefined : e.target.value })}
          >
            {PERIODS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>

        {period === "range" && (
          <>
            <label>
              <span>From</span>
              <select value={from} onChange={(e) => set({ from: e.target.value })}>
                {weeks.map((w) => (
                  <option key={w} value={w}>
                    Week {w}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>To</span>
              <select value={to} onChange={(e) => set({ to: e.target.value })}>
                {weeks.map((w) => (
                  <option key={w} value={w}>
                    Week {w}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}

        <label>
          <span>Stats</span>
          <select
            value={group}
            onChange={(e) => set({ group: e.target.value === "all" ? undefined : e.target.value })}
          >
            {GROUPS.map((g) => (
              <option key={g.id} value={g.id}>
                {g.label}
              </option>
            ))}
          </select>
        </label>

        {view === "totals" ? (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={perWeek}
              onChange={(e) => set({ per: e.target.checked ? "week" : undefined })}
            />
            <span>Per-week average</span>
          </label>
        ) : (
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
        )}
      </div>

      {sorted.length === 0 ? (
        <p className="status">No games in this range.</p>
      ) : (
        <div className="table-wrap">
          <table className="table stats-table">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th
                    key={c.key}
                    title={c.title}
                    className={c.numeric ? "num" : undefined}
                    aria-sort={
                      activeSort.key === c.key
                        ? activeSort.asc
                          ? "ascending"
                          : "descending"
                        : undefined
                    }
                  >
                    <button type="button" onClick={() => onSort(c)}>
                      {c.label}
                      <span className="sort-indicator" aria-hidden>
                        {activeSort.key === c.key ? (activeSort.asc ? "▲" : "▼") : ""}
                      </span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.id}>
                  {columns.map((c) => {
                    const value = row.cells[c.key];
                    if (!c.cat) {
                      return (
                        <td key={c.key} className={c.numeric ? "num" : c.key === "team" ? "team" : undefined}>
                          {value ?? "–"}
                        </td>
                      );
                    }
                    const isBest = value !== null && value === best.get(c.key);
                    return (
                      <td key={c.key} className={isBest ? "num best" : "num"}>
                        {formatStat(c.cat, value as number | null, view === "totals" && perWeek)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="note">
        {view === "totals"
          ? "Highlighted values lead each column. Tap a column to sort."
          : "Every team's line for every week. Sort a column to find single-week records."}
        {approximate &&
          " Rate stats are rebuilt from weekly numbers; OBP is estimated from at-bats, so it can differ from Yahoo by about .001."}
      </p>
    </section>
  );
}
