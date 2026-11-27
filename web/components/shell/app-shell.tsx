"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AssumptionsSheet } from "@/components/shell/assumptions-sheet";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { isActive, navigation } from "@/lib/navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

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
                  href={item.href}
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
          <div className="hidden shrink-0 items-center gap-2 lg:flex">
            <ContextMenu
              label="Illustrative set"
              note="Defense, Simulator, and Compare use five phishing emails, including the malware case where all five layers apply."
            />
            <ContextMenu
              label="Untrained v1 → Trained v2"
              note="Defense edits the baseline. Compare states that pair in one sentence. Unsaved edits are included."
            />
            <AssumptionsSheet />
          </div>
        </div>
      </header>
      <div id="content">{children}</div>
    </div>
  );
}

function ContextMenu({ label, note }: { label: string; note: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>{label}</DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-w-72">
        <DropdownMenuItem disabled className="whitespace-normal opacity-100">
          {note}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
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
