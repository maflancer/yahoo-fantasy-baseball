# Yahoo Fantasy Baseball

A small dashboard for a Yahoo Fantasy Baseball league: **[maflancer.github.io/yahoo-fantasy-baseball](https://maflancer.github.io/yahoo-fantasy-baseball/)**

- **Standings**: sortable league standings for each season
- **Scoreboard**: every week's matchups with category-by-category results, plus that week's category leaders
- **Stats**: season totals for every team (or any range of weeks, or per-week averages), and a sortable week-by-week log

## How it works

```
Yahoo Fantasy API ──▶ pipeline/ (Python) ──▶ web/public/data/*.json ──▶ web/ (React) ──▶ GitHub Pages
```

1. **`pipeline/`** fetches each season with [yahoo-fantasy-api](https://yahoo-fantasy-api.readthedocs.io/), then writes JSON files. League name, teams, scoring categories (and whether lower is better), and playoff weeks all come from Yahoo, so nothing league-specific is hardcoded.
2. **`update-data.yml`** runs the pipeline every Monday, commits any changed data to `main`, and redeploys.
3. **`web/`** is a static React + TypeScript app with no UI libraries. It reads the JSON files and is deployed to GitHub Pages on every push to `main`.

Only manager nicknames are published, never Yahoo team names.

Fantasy data provided by [Yahoo Fantasy](https://sports.yahoo.com/fantasy/).

## Configuration

[`config.toml`](config.toml) lists the seasons to track. Add an entry each year:

```toml
[[seasons]]
year = 2027
league_id = "..."   # optional; defaults to your first league that year
```

GitHub secrets:

| Secret | Required | Description |
| --- | --- | --- |
| `YAHOO_OAUTH_FULL` | yes | Contents of `oauth2.json` (see below) |
| `TEAM_NAME_MAP` | no | JSON mapping manager nickname to display name, e.g. `{"nathan": "Nate"}` |

## Running locally

Requires [uv](https://docs.astral.sh/uv/) and Node 22.

```bash
# Yahoo credentials: create an app at https://developer.yahoo.com/apps/,
# then put {"consumer_key": "...", "consumer_secret": "..."} in oauth2.json.
# The first run prints an authorization URL; paste the code back and it saves the tokens.

uv run --project pipeline fantasy-pipeline              # latest season
uv run --project pipeline fantasy-pipeline --season 2024
uv run --project pipeline fantasy-pipeline --all        # every season in config.toml

cd pipeline && uv run pytest                            # tests

cd web && npm install && npm run dev                    # http://localhost:5173/yahoo-fantasy-baseball/
```

Past seasons can also be backfilled from GitHub: **Actions → Update data → Run workflow** and enter a season.

## Data files

| File | Contents |
| --- | --- |
| `seasons.json` | Every season: year, league name, team count, last updated |
| `{year}/standings.json` | Final or current standings |
| `{year}/stats.json` | One row per team per week, with the parts needed to total rate stats (H, AB, outs, ER, H+BB) |
| `{year}/scoreboard.json` | For each completed week: matchups (scores, stats, category winners) and category leaders |
