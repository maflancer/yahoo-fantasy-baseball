import { useData } from "./data";
import Leaders from "./pages/Leaders";
import Standings from "./pages/Standings";
import { type Page, useRoute } from "./route";
import type { SeasonSummary } from "./types";

const PAGES: { id: Page; label: string }[] = [
  { id: "standings", label: "Standings" },
  { id: "leaders", label: "Weekly Leaders" },
];

export default function App() {
  const { route, navigate } = useRoute();
  const seasons = useData<SeasonSummary[]>("seasons.json");

  if (seasons.status !== "ready") {
    return (
      <div className="shell">
        <p className="status">
          {seasons.status === "error" ? `Couldn't load seasons: ${seasons.error}` : "Loading…"}
        </p>
      </div>
    );
  }

  const list = seasons.data;
  const requested = Number(route.params.get("season"));
  const season = list.find((s) => s.year === requested) ?? list[0];

  return (
    <div className="shell">
      <header className="header">
        <div className="title">
          <span className="logo" aria-hidden>
            ⚾
          </span>
          <h1>{season.name}</h1>
        </div>
        <select
          className="season-select"
          aria-label="Season"
          value={season.year}
          onChange={(e) => navigate(route.page, { season: e.target.value })}
        >
          {list.map((s) => (
            <option key={s.year} value={s.year}>
              {s.year} · {s.name}
            </option>
          ))}
        </select>
      </header>

      <nav className="tabs">
        {PAGES.map((p) => (
          <a
            key={p.id}
            href={`#/${p.id}?season=${season.year}`}
            className={p.id === route.page ? "tab active" : "tab"}
            aria-current={p.id === route.page ? "page" : undefined}
          >
            {p.label}
          </a>
        ))}
      </nav>

      <main>
        {route.page === "standings" ? (
          <Standings season={season} />
        ) : (
          <Leaders
            season={season}
            week={Number(route.params.get("week")) || undefined}
            onWeekChange={(week) =>
              navigate("leaders", { season: season.year, week }, true)
            }
          />
        )}
      </main>

      <footer className="footer">
        Data from Yahoo Fantasy · updated {new Date(season.updated_at).toLocaleDateString()}
      </footer>
    </div>
  );
}
