"use client";

// The product shell: skip link, sticky header with the primary navigation
// (active state from the current path), and a theme toggle. Client-only so it
// can read the pathname; all data fetching stays in Server Components.
import { ThemeToggle } from "@crucible/ui";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const NAV = [
  { href: "/dashboard", label: "Reliability" },
  { href: "/datasets", label: "Datasets" },
  { href: "/runs", label: "Runs" },
  { href: "/reviews", label: "Reviews" },
  { href: "/evaluations", label: "Evaluations" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "";
  return (
    <>
      <a className="cru-skip" href="#main">
        Skip to content
      </a>
      <header className="cru-header">
        <div className="cru-header-inner">
          <Link className="cru-brand" href="/">
            ⬡ Crucible
          </Link>
          <nav className="cru-nav" aria-label="Primary">
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <ThemeToggle />
        </div>
      </header>
      <main id="main" className="cru-main">
        {children}
      </main>
    </>
  );
}
