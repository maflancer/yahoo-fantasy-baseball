import { useData } from "./data";
import Draft from "./pages/Draft";
import Scoreboard from "./pages/Scoreboard";
import Standings from "./pages/Standings";
import Stats from "./pages/Stats";
import { type Page, useRoute } from "./route";
import type { SeasonSummary } from "./types";

const PAGES: { id: Page; label: string }[] = [
  { id: "standings", label: "Standings" },
  { id: "scoreboard", label: "Scoreboard" },
  { id: "stats", label: "Stats" },
  { id: "draft", label: "Draft" },
];

// Required by the Yahoo Fantasy API terms on every page showing Yahoo data:
// the exact phrase, a link to Yahoo Fantasy, and the unmodified official logo.
// https://sports.yahoo.com/developer/
const YAHOO_FANTASY_URL = "https://sports.yahoo.com/fantasy/";
// The official SVG is a 293x293 square with the wordmark in a thin band; the
// #svgView fragment frames just that band without altering the logo itself.
const YAHOO_FANTASY_LOGO =
  "https://763445962456-brand-assets.s3.us-west-2.amazonaws.com/brandwebsite/s3fs-public/Yahoo_Fantasy.svg#svgView(viewBox(58,131,177,31))";

function YahooAttribution() {
  return (
    <a className="attribution" href={YAHOO_FANTASY_URL} target="_blank" rel="noopener noreferrer">
      <img src={YAHOO_FANTASY_LOGO} alt="Yahoo Fantasy" width={103} height={18} />
      Fantasy data provided by Yahoo Fantasy
    </a>
  );
}

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
        {route.page === "standings" && <Standings season={season} />}
        {route.page === "scoreboard" && (
          <Scoreboard
            season={season}
            week={Number(route.params.get("week")) || undefined}
            onWeekChange={(week) => navigate("scoreboard", { season: season.year, week }, true)}
          />
        )}
        {route.page === "draft" && (
          <Draft
            season={season}
            params={route.params}
            onParamsChange={(updates) =>
              navigate(
                "draft",
                { ...Object.fromEntries(route.params), season: season.year, ...updates },
                true,
              )
            }
          />
        )}
        {route.page === "stats" && (
          <Stats
            season={season}
            params={route.params}
            onParamsChange={(updates) =>
              navigate(
                "stats",
                { ...Object.fromEntries(route.params), season: season.year, ...updates },
                true,
              )
            }
          />
        )}
      </main>

      <footer className="footer">
        <YahooAttribution />
        <span>Updated {new Date(season.updated_at).toLocaleDateString()}</span>
      </footer>
    </div>
  );
}
