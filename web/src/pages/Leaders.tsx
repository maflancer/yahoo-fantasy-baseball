import { useEffect } from "react";
import { useData } from "../data";
import type { LeadersFile, SeasonSummary, StatCategory } from "../types";

interface Props {
  season: SeasonSummary;
  week?: number;
  onWeekChange: (week: number) => void;
}

const GROUPS: { type: string; label: string }[] = [
  { type: "B", label: "Batting" },
  { type: "P", label: "Pitching" },
];

function formatDate(iso: string): string {
  if (!iso) return "";
  // Dates are plain YYYY-MM-DD; parse as local to avoid a timezone shift.
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function Leaders({ season, week, onWeekChange }: Props) {
  const file = useData<LeadersFile>(`${season.year}/leaders.json`);

  const weeks = file.status === "ready" ? file.data.weeks : [];
  const latest = weeks.length ? weeks[weeks.length - 1].week : undefined;
  const current = weeks.find((w) => w.week === week) ?? weeks[weeks.length - 1];

  // Put the resolved week in the URL so the view is shareable.
  useEffect(() => {
    if (current && current.week !== week) onWeekChange(current.week);
  }, [current, week, onWeekChange]);

  if (file.status === "loading") return <p className="status">Loading leaders…</p>;
  if (file.status === "error") return <p className="status">Couldn't load leaders: {file.error}</p>;
  if (!current) return <p className="status">No completed weeks yet.</p>;

  const names = new Map(file.data.teams.map((t) => [t.team_key, t.name]));
  const leaderByStat = new Map(current.leaders.map((l) => [l.stat, l]));
  const index = weeks.indexOf(current);
  const prev = weeks[index - 1];
  const next = weeks[index + 1];

  const renderCategory = (cat: StatCategory) => {
    const leader = leaderByStat.get(cat.abbr);
    return (
      <li key={cat.id} className="leader">
        <div className="leader-stat">
          <span className="abbr">{cat.abbr}</span>
          <span className="stat-name">{cat.name}</span>
        </div>
        <div className="leader-value mono">{leader?.value ?? "–"}</div>
        <div className="leader-teams">
          {leader ? leader.team_keys.map((k) => names.get(k) ?? k).join(", ") : "No data"}
        </div>
      </li>
    );
  };

  return (
    <section className="card">
      <div className="week-bar">
        <button
          type="button"
          className="icon-button"
          onClick={() => prev && onWeekChange(prev.week)}
          disabled={!prev}
          aria-label="Previous week"
        >
          ‹
        </button>
        <div className="week-title">
          <select
            aria-label="Week"
            value={current.week}
            onChange={(e) => onWeekChange(Number(e.target.value))}
          >
            {weeks.map((w) => (
              <option key={w.week} value={w.week}>
                Week {w.week}
                {w.is_playoffs ? " (playoffs)" : ""}
              </option>
            ))}
          </select>
          <span className="week-dates">
            {formatDate(current.start)} – {formatDate(current.end)}
            {current.is_playoffs && <span className="badge">Playoffs</span>}
            {current.week === latest && !season.is_finished && <span className="badge">Latest</span>}
          </span>
        </div>
        <button
          type="button"
          className="icon-button"
          onClick={() => next && onWeekChange(next.week)}
          disabled={!next}
          aria-label="Next week"
        >
          ›
        </button>
      </div>

      {GROUPS.map((group) => {
        const cats = file.data.categories.filter((c) => c.position_type === group.type);
        if (!cats.length) return null;
        return (
          <div key={group.type} className="leader-group">
            <h2>{group.label}</h2>
            <ul className="leader-grid">{cats.map(renderCategory)}</ul>
          </div>
        );
      })}

      {current.is_playoffs && (
        <p className="note">Playoff week: only teams still playing are included.</p>
      )}
    </section>
  );
}
