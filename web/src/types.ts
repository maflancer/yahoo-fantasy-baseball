// Shapes of the JSON files written by the Python pipeline (pipeline/src/fantasy_pipeline/build.py).

export interface SeasonSummary {
  year: number;
  name: string;
  league_key: string;
  num_teams: number | null;
  playoff_start_week: number | null;
  is_finished: boolean;
  has_draft?: boolean;
  has_moves?: boolean;
  updated_at: string;
}

export interface Team {
  team_key: string;
  name: string;
}

export interface StandingsRow {
  team_key: string;
  rank: number | null;
  playoff_seed: number | null;
  wins: number;
  losses: number;
  ties: number;
  percentage: string;
  games_back: string;
}

export interface StandingsFile {
  teams: Team[];
  standings: StandingsRow[];
}

export interface StatCategory {
  id: string;
  abbr: string;
  name: string;
  higher_is_better: boolean;
  position_type: "B" | "P" | string;
}

export interface CategoryLeader {
  stat: string;
  value: string;
  team_keys: string[];
}

export interface MatchupTeam {
  team_key: string;
  points: number;
  stats: Record<string, string>;
}

export interface Matchup {
  winner_key: string | null;
  is_playoffs: boolean;
  is_consolation: boolean;
  teams: MatchupTeam[];
  /** Category abbr -> winning team key, or null when tied. */
  stat_winners: Record<string, string | null>;
  /** Playoff round, e.g. "Semifinal" or "5th place game". Absent in the regular season. */
  round?: string;
  /** True while the winner can still finish first. */
  for_title?: boolean;
}

export interface ScoreboardWeek {
  week: number;
  start: string;
  end: string;
  is_playoffs: boolean;
  matchups: Matchup[];
  leaders: CategoryLeader[];
}

export interface ScoreboardFile {
  teams: Team[];
  categories: StatCategory[];
  weeks: ScoreboardWeek[];
}

export type Aggregation =
  | { type: "sum" }
  | { type: "innings" }
  | { type: "ratio"; num: string; den: string; scale: number; decimals: number }
  | { type: "weighted"; weight: string; decimals: number; approximate: true };

export interface StatsCategory extends StatCategory {
  agg: Aggregation;
}

export interface StatsRow {
  week: number;
  team_key: string;
  opponent_key: string | null;
  result: "W" | "L" | "T";
  /** [categories won, categories the opponent won] */
  score: [number, number];
  is_playoffs: boolean;
  round?: string;
  /** Numeric weekly values; innings are stored as outs. */
  values: Record<string, number | null>;
  /** Components for totalling rate stats: H, AB, outs, ER, WH. */
  parts: Record<string, number>;
}

export interface StatsFile {
  teams: Team[];
  categories: StatsCategory[];
  rows: StatsRow[];
}

export interface Tenure {
  /** Share of the season the drafting team had the player (0-1). */
  kept_share: number;
  /** How the drafting team let him go, or null if they kept him. */
  left: "drop" | "trade" | null;
  left_date: string | null;
  /** The next team to roster him after the drafting team. */
  next_team_key: string | null;
}

export interface DraftPick {
  pick: number;
  round: number;
  team_key: string;
  player_key: string;
  name: string;
  mlb_team: string;
  position: string;
  /** Yahoo season rank; null if unavailable. */
  rank: number | null;
  tenure: Tenure;
}

export interface DraftFile {
  teams: Team[];
  num_picks: number;
  picks: DraftPick[];
  /** Pick numbers to highlight. */
  steals: number[];
  busts: number[];
}

export interface Move {
  player_key: string;
  action: "draft" | "add" | "drop" | "trade";
  from_team_key?: string;
  to_team_key?: string;
  /** "freeagents" or "waivers" */
  via?: string;
}

export interface MoveEntry {
  id: string;
  date: string;
  type: "draft" | "add" | "drop" | "add/drop" | "trade" | "commish";
  pick?: number;
  round?: number;
  moves: Move[];
}

export interface MovePlayer {
  name: string;
  position: string;
  mlb_team: string;
  rank: number | null;
}

export interface Stint {
  team_key: string;
  start: string;
  end: string | null;
  acquired: "draft" | "add" | "trade";
  left: "drop" | "trade" | null;
}

export interface MovesFile {
  teams: Team[];
  /** Newest first, with draft picks at the end. */
  transactions: MoveEntry[];
  players: Record<string, MovePlayer>;
  top_pickups: { player_key: string; stints: Stint[] }[];
}
