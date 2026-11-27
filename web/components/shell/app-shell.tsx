"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bell,
  ChartColumn,
  CircleQuestionMark,
  Crosshair,
  GitCompare,
  Globe,
  GraduationCap,
  LayoutDashboard,
  Mail,
  Search,
  Settings,
  Shield,
  ShieldExclamationPoint,
  Zap,
} from "lucide-react";

import { AssumptionsSheet } from "@/components/shell/assumptions-sheet";
import { WorkspaceControls } from "@/components/shell/workspace";
import { isActive } from "@/lib/navigation";

const topNav = [
  { href: "/", label: "Dashboard" },
  { href: "/triage", label: "Triage" },
  { href: "/simulator", label: "Simulator" },
  { href: "/defense", label: "Defense" },
  { href: "/academy", label: "Training" },
  { href: "/reports", label: "Reports" },
] as const;

const sideNav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/triage", label: "Email Triage", icon: Mail },
  { href: "/investigate", label: "Threat Investigation", icon: ShieldExclamationPoint },
  { href: "/intelligence", label: "URL Intelligence", icon: Globe },
  { href: "/simulator", label: "Simulator", icon: Crosshair },
  { href: "/defense", label: "Defense Config", icon: Shield },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/academy", label: "Training Academy", icon: GraduationCap },
  { href: "/reports", label: "Reports", icon: ChartColumn },
] as const;

function withSelection(href: string, selection: string) {
  const path = href === "/investigate" ? "/triage" : href;
  if (!selection) return path;
  return `${path}?${selection}`;
}

function sideActive(pathname: string, href: string) {
  if (href === "/triage") return pathname === "/triage";
  if (href === "/investigate") return pathname.startsWith("/triage/") && pathname !== "/triage";
  return isActive(pathname, href);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  useEffect(() => setMounted(true), []);
  const selection = mounted ? params.toString() : "";

  function onSearch(event: React.FormEvent) {
    event.preventDefault();
    const query = new URLSearchParams(mounted ? params.toString() : "");
    const text = search.trim();
    if (text) query.set("q", text);
    else query.delete("q");
    const next = query.toString();
    router.push(next ? `/triage?${next}` : "/triage");
  }

  return (
    <div className="relative min-h-screen">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-full focus:bg-card focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-white/8 bg-[#07080c]/75 px-4 backdrop-blur-xl">
        <Link href={withSelection("/", selection)} className="flex shrink-0 items-center gap-2.5 rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          <BrandMark />
          <span className="text-[15px] font-semibold tracking-[-0.03em]">LayerSight</span>
        </Link>
        <nav className="mx-auto hidden items-center gap-0.5 rounded-full border border-white/10 bg-white/[0.04] p-1 md:flex" aria-label="Primary">
          {topNav.map((item) => {
            const active = item.href === "/triage" ? pathname === "/triage" || pathname.startsWith("/triage/") : isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={withSelection(item.href, selection)}
                data-testid={item.href === "/triage" ? "nav-triage" : undefined}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "rounded-full bg-[#6d4dff] px-3.5 py-1.5 text-sm font-medium text-white shadow-[0_6px_18px_rgba(109,77,255,0.45)]"
                    : "rounded-full px-3.5 py-1.5 text-sm text-[#c8cdd8] hover:bg-white/5 hover:text-white"
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <form onSubmit={onSearch} className="ml-auto flex items-center gap-2 md:ml-0">
          <label className="relative hidden sm:block">
            <span className="sr-only">Search LayerSight</span>
            <Search className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-[#8d93a3]" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search LayerSight..."
              className="h-9 w-44 rounded-full border border-white/10 bg-black/35 pr-3 pl-8 text-sm text-foreground placeholder:text-[#7d8494] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8b7cff] lg:w-56"
            />
          </label>
          <button type="button" aria-label="Notifications" className="flex size-9 items-center justify-center rounded-full border border-white/10 text-[#c8cdd8] hover:bg-white/5 hover:text-white">
            <Bell className="size-4" />
          </button>
          <span className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-[#7c5cff] to-[#c084fc] text-sm font-semibold text-white" aria-hidden="true">
            S
          </span>
        </form>
      </header>
      <div className="flex min-h-[calc(100vh-4rem)]">
        <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] w-60 shrink-0 flex-col overflow-hidden border-r border-white/8 bg-[#0b0c12]/80 px-3 py-4 backdrop-blur-xl lg:flex">
          <div className="min-h-0 flex-1 overflow-y-auto">
          <nav className="flex flex-col gap-1" aria-label="Sections">
            {sideNav.map((item) => {
              const active = sideActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={withSelection(item.href, selection)}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "flex items-center gap-2.5 rounded-xl bg-[#6d4dff] px-3 py-2 text-sm font-medium text-white shadow-[0_8px_22px_rgba(109,77,255,0.35)]"
                      : "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-[#b7bdca] hover:bg-white/5 hover:text-white"
                  }
                >
                  <Icon className="size-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-4 border-t border-white/8 pt-3">
            <button
              type="button"
              className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-[#b7bdca] hover:bg-white/5 hover:text-white"
              onClick={() => document.getElementById("workspace")?.querySelector("select")?.focus()}
            >
              <Settings className="size-4" />
              Settings
            </button>
            <AssumptionsSheet nav />
          </div>
          </div>
          <div id="workspace" className="mt-3 shrink-0 rounded-2xl border border-white/8 bg-black/25 p-3">
            <WorkspaceControls stacked />
          </div>
          <div className="mt-3 shrink-0 rounded-2xl border border-violet-400/25 bg-gradient-to-br from-[#3a2a78]/80 via-[#14121c] to-[#ff7a30]/15 p-3">
            <span className="mb-3 flex size-8 items-center justify-center rounded-xl bg-violet-500/25 text-violet-200">
              <Zap className="size-4" />
            </span>
            <p className="text-sm font-semibold">Upgrade to Pro</p>
            <p className="mt-1 text-xs leading-4 text-[#b7bdca]">Run larger simulations and compare defenses.</p>
            <Link href={withSelection("/simulator", selection)} className="mt-2 inline-flex h-8 w-full items-center justify-center rounded-full bg-white text-sm font-medium text-[#101218]">
              Upgrade
            </Link>
          </div>
        </aside>
        <div className="min-w-0 flex-1">
          <div className="flex gap-2 overflow-x-auto border-b border-white/8 px-3 py-2 lg:hidden">
            {topNav.map((item) => (
              <Link
                key={item.href}
                href={withSelection(item.href, selection)}
                className="shrink-0 rounded-full border border-white/10 px-3 py-1 text-xs text-[#c8cdd8]"
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div id="content">{children}</div>
        </div>
      </div>
    </div>
  );
}

function BrandMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="ls-a" x1="4" y1="2" x2="28" y2="30">
          <stop offset="0" stopColor="#ff8a3d" />
          <stop offset="0.48" stopColor="#e24ad4" />
          <stop offset="1" stopColor="#6d4dff" />
        </linearGradient>
        <linearGradient id="ls-b" x1="28" y1="4" x2="4" y2="28">
          <stop offset="0" stopColor="#49d6ff" />
          <stop offset="1" stopColor="#7c5cff" />
        </linearGradient>
      </defs>
      <path d="M16 2c2.4 4.6 4.2 7.2 8.2 8.8C20.2 12.2 18.4 14 16 16c-2.4-2-4.2-3.8-8.2-5.2C11.8 9.2 13.6 6.6 16 2Z" fill="url(#ls-a)" />
      <path d="M16 16c2.4 2 4.2 3.8 8.2 5.2C20.2 22.8 18.4 25.4 16 30c-2.4-4.6-4.2-7.2-8.2-8.8C11.8 19.8 13.6 18 16 16Z" fill="url(#ls-b)" />
      <path d="M2 16c4.6-2.4 7.2-4.2 8.8-8.2C12.2 11.8 14 13.6 16 16c-2 2.4-3.8 4.2-5.2 8.2C9.2 20.2 6.6 18.4 2 16Z" fill="#ff6a3d" opacity="0.9" />
      <path d="M16 16c2 2.4 3.8 4.2 5.2 8.2 1.4-4 4-5.8 8.8-8.2-4.8-2.4-7.4-4.2-8.8-8.2C19.8 11.8 18 13.6 16 16Z" fill="#49c4ff" opacity="0.85" />
    </svg>
  );
}
