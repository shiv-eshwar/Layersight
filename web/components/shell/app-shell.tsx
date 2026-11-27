"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AssumptionsSheet } from "@/components/shell/assumptions-sheet";
import { WorkspaceControls } from "@/components/shell/workspace";
import { isActive, navigation } from "@/lib/navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const selection = mounted ? params.toString() : "";

  return (
    <div className="min-h-screen">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-card focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-border bg-background">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
          <Link href="/" className="flex shrink-0 items-center gap-2 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            <LayersMark />
            <span className="leading-tight">
              <span className="block text-sm font-semibold tracking-tight">LayerSight</span>
              <span className="block text-[11px] text-muted-foreground">Phishing resilience</span>
            </span>
          </Link>
          <nav className="flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto" aria-label="Primary">
            {navigation.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={selection ? `${item.href}?${selection}` : item.href}
                  data-testid={item.href === "/triage" ? "nav-triage" : undefined}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "shrink-0 border-b-2 border-intelligence px-2 py-4 text-sm text-foreground"
                      : "shrink-0 border-b-2 border-transparent px-2 py-4 text-sm text-muted-foreground hover:text-foreground"
                  }
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <AssumptionsSheet />
        </div>
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 border-t border-border px-4 py-2">
          <WorkspaceControls />
        </div>
      </header>
      <div id="content">{children}</div>
    </div>
  );
}

function LayersMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
      <rect x="3" y="4" width="16" height="3" rx="1" fill="#38bdf8" />
      <rect x="5" y="9.5" width="12" height="3" rx="1" fill="#10b981" />
      <rect x="7" y="15" width="8" height="3" rx="1" fill="#f59e0b" />
    </svg>
  );
}
