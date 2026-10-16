import { useCallback, useEffect, useState } from "react";

// Hash routing (#/scoreboard?season=2026&week=5) works on GitHub Pages without a
// 404 fallback and keeps every view linkable.

export type Page = "standings" | "scoreboard";

export interface Route {
  page: Page;
  params: URLSearchParams;
}

function parseHash(): Route {
  const [path, query = ""] = window.location.hash.replace(/^#\/?/, "").split("?");
  // "leaders" was the old name of the scoreboard page; keep those links working.
  const page: Page = path === "scoreboard" || path === "leaders" ? "scoreboard" : "standings";
  return { page, params: new URLSearchParams(query) };
}

export function useRoute() {
  const [route, setRoute] = useState<Route>(parseHash);

  useEffect(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback(
    (page: Page, params: Record<string, string | number | undefined>, replace = false) => {
      const query = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== "") query.set(key, String(value));
      }
      const qs = query.toString();
      const hash = `#/${page}${qs ? `?${qs}` : ""}`;
      if (replace) {
        window.history.replaceState(null, "", hash);
        setRoute(parseHash());
      } else {
        window.location.hash = hash;
      }
    },
    [],
  );

  return { route, navigate };
}
