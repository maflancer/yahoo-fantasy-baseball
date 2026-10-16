import { type ReactNode, useState } from "react";

export interface SortColumn<T> {
  key: string;
  label: string;
  title?: string;
  numeric?: boolean;
  /** Direction for the first click; use true when lower values are better. */
  startAscending?: boolean;
  /** Value used for sorting. Null/undefined always sorts last. */
  value: (row: T) => string | number | null | undefined;
  /** Cell contents; defaults to the sort value. */
  render?: (row: T) => ReactNode;
  className?: string | ((row: T) => string | undefined);
}

interface Props<T> {
  columns: SortColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  initialSort: { key: string; asc: boolean };
  className?: string;
}

export default function SortTable<T>({ columns, rows, rowKey, initialSort, className }: Props<T>) {
  const [sort, setSort] = useState(initialSort);
  const column = columns.find((c) => c.key === sort.key) ?? columns[0];

  const sorted = [...rows].sort((a, b) => {
    const x = column.value(a);
    const y = column.value(b);
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    const cmp =
      typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
    return sort.asc ? cmp : -cmp;
  });

  const onSort = (col: SortColumn<T>) =>
    setSort((s) => ({
      key: col.key,
      asc: s.key === col.key ? !s.asc : (col.startAscending ?? !col.numeric),
    }));

  return (
    <div className="table-wrap">
      <table className={`table ${className ?? ""}`}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                title={c.title}
                className={c.numeric ? "num" : undefined}
                aria-sort={sort.key === c.key ? (sort.asc ? "ascending" : "descending") : undefined}
              >
                <button type="button" onClick={() => onSort(c)}>
                  {c.label}
                  <span className="sort-indicator" aria-hidden>
                    {sort.key === c.key ? (sort.asc ? "▲" : "▼") : ""}
                  </span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => {
                const extra = typeof c.className === "function" ? c.className(row) : c.className;
                const classes = [c.numeric ? "num" : undefined, extra].filter(Boolean).join(" ");
                return (
                  <td key={c.key} className={classes || undefined}>
                    {c.render ? c.render(row) : (c.value(row) ?? "–")}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
