// Totalling and formatting for stats.json (see pipeline/src/fantasy_pipeline/stats.py).

import type { StatsCategory, StatsRow } from "./types";

export interface TeamTotals {
  team_key: string;
  weeks: number;
  values: Record<string, number | null>;
}

/** Combine team-week rows into one row per team, following each category's aggregation rule. */
export function totalsByTeam(
  rows: StatsRow[],
  categories: StatsCategory[],
  perWeek: boolean,
): TeamTotals[] {
  const groups = new Map<string, StatsRow[]>();
  for (const row of rows) {
    const list = groups.get(row.team_key) ?? [];
    list.push(row);
    groups.set(row.team_key, list);
  }

  return [...groups].map(([team_key, teamRows]) => {
    const values: Record<string, number | null> = {};
    for (const cat of categories) {
      values[cat.abbr] = combine(teamRows, cat, perWeek);
    }
    return { team_key, weeks: teamRows.length, values };
  });
}

function sumOf(rows: StatsRow[], get: (row: StatsRow) => number | null | undefined): number {
  return rows.reduce((total, row) => total + (get(row) ?? 0), 0);
}

function combine(rows: StatsRow[], cat: StatsCategory, perWeek: boolean): number | null {
  const agg = cat.agg;
  switch (agg.type) {
    case "sum":
    case "innings": {
      const total = sumOf(rows, (r) => r.values[cat.abbr]);
      return perWeek ? total / rows.length : total;
    }
    case "ratio": {
      const den = sumOf(rows, (r) => r.parts[agg.den]);
      return den ? (agg.scale * sumOf(rows, (r) => r.parts[agg.num])) / den : null;
    }
    case "weighted": {
      const usable = rows.filter((r) => r.values[cat.abbr] != null);
      const weight = sumOf(usable, (r) => r.parts[agg.weight]);
      if (!weight) return null;
      return sumOf(usable, (r) => (r.values[cat.abbr] ?? 0) * (r.parts[agg.weight] ?? 0)) / weight;
    }
  }
}

/** Display a value the way Yahoo does: ".248" for averages, "1551.2" for innings. */
export function formatStat(cat: StatsCategory, value: number | null, perWeek = false): string {
  if (value === null || Number.isNaN(value)) return "–";
  const agg = cat.agg;
  switch (agg.type) {
    case "sum":
      return perWeek ? value.toFixed(1) : String(Math.round(value));
    case "innings": {
      const outs = Math.round(value);
      return `${Math.floor(outs / 3)}.${outs % 3}`;
    }
    case "ratio":
    case "weighted": {
      const text = value.toFixed(agg.decimals);
      // Batting-style averages drop the leading zero (.248).
      return agg.decimals >= 3 && value < 1 ? text.replace(/^0/, "") : text;
    }
  }
}

/** The best value in a column, respecting whether lower is better. */
export function bestValue(values: (number | null)[], higherIsBetter: boolean): number | null {
  const present = values.filter((v): v is number => v !== null);
  if (!present.length) return null;
  return higherIsBetter ? Math.max(...present) : Math.min(...present);
}
