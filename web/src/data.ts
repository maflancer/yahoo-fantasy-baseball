import { useEffect, useState } from "react";

const cache = new Map<string, Promise<unknown>>();

function fetchJson<T>(path: string): Promise<T> {
  const url = `${import.meta.env.BASE_URL}data/${path}`;
  let request = cache.get(url);
  if (!request) {
    request = fetch(url).then((res) => {
      if (!res.ok) throw new Error(`${res.status} loading ${path}`);
      return res.json();
    });
    // Don't cache failures, so a retry can succeed.
    request.catch(() => cache.delete(url));
    cache.set(url, request);
  }
  return request as Promise<T>;
}

export type Loadable<T> =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "ready"; data: T };

/** Load a JSON file from public/data. Pass null to skip loading. */
export function useData<T>(path: string | null): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ status: "loading" });

  useEffect(() => {
    if (!path) return;
    let active = true;
    setState({ status: "loading" });
    fetchJson<T>(path).then(
      (data) => active && setState({ status: "ready", data }),
      (err: Error) => active && setState({ status: "error", error: err.message }),
    );
    return () => {
      active = false;
    };
  }, [path]);

  return state;
}
