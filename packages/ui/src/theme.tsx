"use client";

/*
 * Theme toggle. Persists the choice in localStorage and stamps `data-theme` on
 * <html>, which the token stylesheet honours over the OS `prefers-color-scheme`
 * in both directions. React-only — no Next dependency — so it lives in the
 * design system and works anywhere.
 */
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function systemTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem("cru-theme") as Theme | null;
    setTheme(stored ?? systemTheme());
  }, []);

  useEffect(() => {
    if (theme === null) return;
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("cru-theme", theme);
  }, [theme]);

  const next = theme === "light" ? "dark" : "light";
  return (
    <button
      type="button"
      className="cru-btn"
      aria-label={`Switch to ${next} theme`}
      onClick={() => setTheme(next)}
    >
      {theme === "light" ? "☾" : "☀"}
      <span style={{ fontSize: "0.85rem" }}>{theme === "light" ? "Dark" : "Light"}</span>
    </button>
  );
}
