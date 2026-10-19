# Yahoo Fantasy Baseball

A stats site for my Yahoo Fantasy Baseball league with friends: **[maflancer.github.io/yahoo-fantasy-baseball](https://maflancer.github.io/yahoo-fantasy-baseball/)**

It's built so anyone can point it at their own league; see [Use it for your own league](#use-it-for-your-own-league).

- **Standings**: final or current standings for each season
- **Scoreboard**: each week's matchups, category by category, plus the week's category leaders
- **Stats**: season totals for every team, filterable by week range, and a week-by-week log
- **Draft**: every pick with the player's season rank and how long the drafting team kept him, plus the biggest steals and busts
- **Moves**: every add, drop and trade, each team's activity, and the best pickups of the season

## How it works

1. A Python pipeline pulls league data from the Yahoo Fantasy API and writes JSON files to `web/public/data/`.
2. A scheduled GitHub Action runs the pipeline every Monday and commits any changed data (in the offseason there's nothing new, so it commits nothing).
3. New data, or a merged pull request, builds the React + TypeScript site and deploys it to GitHub Pages.

Every pull request runs CI: Python tests (pytest, against saved real Yahoo responses) covering parsing, stat totals, the playoff bracket and draft/transaction history, plus linting and a type-check and build of the site.

Fantasy data provided by [Yahoo Fantasy](https://sports.yahoo.com/fantasy/).

## Use it for your own league

Works with Yahoo head-to-head categories leagues.

### 1. Get Yahoo API access

Create an app at [developer.yahoo.com/apps/create](https://developer.yahoo.com/apps/create/) with **Fantasy Sports (Read)** permission. Yahoo may ask you to describe your use case and accept the [Yahoo Fantasy developer terms](https://sports.yahoo.com/developer/). You'll get a **Client ID** and **Client Secret**.

### 2. Fork and configure

1. Fork this repo and clone it.
2. Delete the existing data: `rm -rf web/public/data`
3. List your seasons in [`config.toml`](config.toml). `league_id` is optional; without it, your first league that year is used.
   ```toml
   [[seasons]]
   year = 2026
   ```
4. If you renamed the repo, set `base` in [`web/vite.config.ts`](web/vite.config.ts) to `/<your-repo-name>/`.

### 3. Authorize and fetch data

Requires [uv](https://docs.astral.sh/uv/). Create `oauth2.json` in the repo root (it's gitignored):

```json
{ "consumer_key": "<Client ID>", "consumer_secret": "<Client Secret>" }
```

Then run:

```bash
uv run --project pipeline fantasy-pipeline --all
```

The first run prints a Yahoo URL. Open it, approve access, and paste the code back. The tokens are saved to `oauth2.json`, and the data is written to `web/public/data/`.

### 4. Deploy

1. Commit and push the new data.
2. In your fork's **Settings → Pages**, set **Source** to **GitHub Actions**.
3. In **Settings → Secrets and variables → Actions**, add `YAHOO_OAUTH_FULL` containing the full contents of your `oauth2.json`.
4. Run **Actions → Deploy**, or push to `main`.

From then on, the **Update data** workflow refreshes the data every Monday and redeploys. You can also run it manually to fetch a specific season.

## Development

```bash
uv run --project pipeline fantasy-pipeline            # fetch the latest season in config.toml
cd pipeline && uv run pytest                          # run tests
cd web && npm install && npm run dev                  # run the site locally (Node 22)
```

| Folder | Contents |
| --- | --- |
| `pipeline/` | Python package that fetches league data from Yahoo and writes JSON |
| `web/` | React + TypeScript site that reads the JSON |
| `.github/workflows/` | CI on pull requests, weekly data updates, and GitHub Pages deploys |
