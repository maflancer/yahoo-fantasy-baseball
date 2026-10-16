// Shapes of the JSON files written by the Python pipeline (pipeline/src/fantasy_pipeline/build.py).

export interface SeasonSummary {
  year: number;
  name: string;
  league_key: string;
  num_teams: number | null;
  playoff_start_week: number | null;
  is_finished: boolean;
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

export interface LeaderWeek {
  week: number;
  start: string;
  end: string;
  is_playoffs: boolean;
  leaders: CategoryLeader[];
}

export interface LeadersFile {
  teams: Team[];
  categories: StatCategory[];
  weeks: LeaderWeek[];
}
