import { useEffect } from "react";
import { useData } from "../data";
import type {
  CategoryLeader,
  Matchup,
  ScoreboardFile,
  SeasonSummary,
  StatCategory,
} from "../types";

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

export default function Scoreboard({ season, week, onWeekChange }: Props) {
  const file = useData<ScoreboardFile>(`${season.year}/scoreboard.json`);

  const weeks = file.status === "ready" ? file.data.weeks : [];
  const current = weeks.find((w) => w.week === week) ?? weeks[weeks.length - 1];

  // Put the resolved week in the URL so the view is shareable.
  useEffect(() => {
    if (current && current.week !== week) onWeekChange(current.week);
  }, [current, week, onWeekChange]);

  if (file.status === "loading") return <p className="status">Loading scoreboard…</p>;
  if (file.status === "error") return <p className="status">Couldn't load scoreboard: {file.error}</p>;
  if (!current) return <p className="status">No completed weeks yet.</p>;

  const names = new Map(file.data.teams.map((t) => [t.team_key, t.name]));
  const nameOf = (key: string) => names.get(key) ?? key;
  const categories = file.data.categories;
  const index = weeks.indexOf(current);
  const prev = weeks[index - 1];
  const next = weeks[index + 1];

  return (
    <>
      <div className="week-bar card">
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

      <section className="section">
        <h2 className="section-title">Matchups</h2>
        <ul className="matchups">
          {current.matchups.map((m) => (
            <MatchupCard
              key={m.teams.map((t) => t.team_key).join("-")}
              matchup={m}
              categories={categories}
              nameOf={nameOf}
            />
          ))}
        </ul>
        <p className="note">Tap a matchup to see each category.</p>
      </section>

      <section className="section">
        <h2 className="section-title">Weekly leaders</h2>
        <Leaders leaders={current.leaders} categories={categories} nameOf={nameOf} />
        {current.is_playoffs && (
          <p className="note">Playoff week: only teams still playing are included.</p>
        )}
      </section>
    </>
  );
}

function roundClass(matchup: Matchup): string {
  if (matchup.round === "Championship") return "round championship";
  return matchup.for_title ? "round title" : "round placement";
}

function MatchupCard({
  matchup,
  categories,
  nameOf,
}: {
  matchup: Matchup;
  categories: StatCategory[];
  nameOf: (key: string) => string;
}) {
  const [a, b] = matchup.teams;
  if (!a || !b) return null;
  const ties = categories.length - a.points - b.points;
  const outcome = (key: string) =>
    matchup.winner_key === null ? "tie" : matchup.winner_key === key ? "won" : "lost";

  return (
    <li className="matchup card">
      <details>
        <summary>
          {matchup.round && (
            <span className={roundClass(matchup)}>
              {matchup.round === "Championship" && <span aria-hidden>🏆 </span>}
              {matchup.round}
            </span>
          )}
          <span className={`side left ${outcome(a.team_key)}`}>{nameOf(a.team_key)}</span>
          <span className="score">
            <span className={outcome(a.team_key)}>{a.points}</span>
            <span className="dash">–</span>
            <span className={outcome(b.team_key)}>{b.points}</span>
            {a.points === b.points && matchup.winner_key ? (
              <span className="ties">won on tiebreaker</span>
            ) : (
              ties > 0 && <span className="ties">{ties} tied</span>
            )}
          </span>
          <span className={`side right ${outcome(b.team_key)}`}>{nameOf(b.team_key)}</span>
        </summary>
        <table className="breakdown">
          <tbody>
            {categories.map((cat) => {
              const winner = matchup.stat_winners[cat.abbr];
              return (
                <tr key={cat.id}>
                  <td className={winner === a.team_key ? "won" : undefined}>
                    {a.stats[cat.abbr] ?? "–"}
                  </td>
                  <th scope="row" title={cat.name}>
                    {cat.abbr}
                  </th>
                  <td className={winner === b.team_key ? "won" : undefined}>
                    {b.stats[cat.abbr] ?? "–"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </details>
    </li>
  );
}

function Leaders({
  leaders,
  categories,
  nameOf,
}: {
  leaders: CategoryLeader[];
  categories: StatCategory[];
  nameOf: (key: string) => string;
}) {
  const byStat = new Map(leaders.map((l) => [l.stat, l]));
  return (
    <>
      {GROUPS.map((group) => {
        const cats = categories.filter((c) => c.position_type === group.type);
        if (!cats.length) return null;
        return (
          <div key={group.type} className="leader-group">
            <h3>{group.label}</h3>
            <ul className="leader-grid">
              {cats.map((cat) => {
                const leader = byStat.get(cat.abbr);
                return (
                  <li key={cat.id} className="leader">
                    <div className="leader-stat">
                      <span className="abbr">{cat.abbr}</span>
                      <span className="stat-name">{cat.name}</span>
                    </div>
                    <div className="leader-value mono">{leader?.value ?? "–"}</div>
                    <div className="leader-teams">
                      {leader ? leader.team_keys.map(nameOf).join(", ") : "No data"}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </>
  );
}
