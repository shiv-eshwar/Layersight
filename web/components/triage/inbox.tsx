"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CloudUpload, GitCompare, Play, Shield } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { Button } from "@/components/ui/button";
import { ApiError, api, selectionHref } from "@/lib/api";
import { formatScore, vectorLabel } from "@/lib/format";
import type { TriageResponse, Verdict } from "@/lib/types";
import { VerdictText } from "@/components/layersight/marks";

export function TriageInbox() {
  const params = useSearchParams();
  const router = useRouter();
  const dataset = params.get("dataset");
  const baseline = params.get("baseline");
  const comparison = params.get("comparison");
  const [tab, setTab] = useState<"all" | Verdict>("all");
  const urlQuery = params.get("q") ?? "";
  const [query, setQuery] = useState(urlQuery);
  useEffect(() => setQuery(urlQuery), [urlQuery]);
  const [sort, setSort] = useState("-risk");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<TriageResponse | null>(null);
  const [loadedFor, setLoadedFor] = useState("");

  const requestKey = `${dataset ?? ""}|${tab}|${query}|${sort}`;
  useEffect(() => {
    if (!dataset || requestKey === loadedFor) return;
    let cancelled = false;
    setBusy(true);
    const search = new URLSearchParams({ prediction: tab, sort });
    if (query.trim()) search.set("q", query.trim());
    void api<TriageResponse>(`/api/v1/datasets/${dataset}/emails?${search.toString()}`)
      .then((body) => {
        if (cancelled) return;
        setRows(body);
        setError(null);
        setLoadedFor(requestKey);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setRows(null);
        setError(reason instanceof ApiError ? reason.message : "The dataset could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [dataset, requestKey, loadedFor, query, sort, tab]);

  async function upload(fileList: FileList | null, labels: File | null) {
    if (!fileList || fileList.length === 0) return;
    const body = new FormData();
    for (const file of fileList) body.append("files", file);
    if (labels) body.append("labels", labels);
    body.append("name", "Upload");
    setBusy(true);
    setError(null);
    try {
      const created = await api<{ id: string }>("/api/v1/datasets", { method: "POST", body });
      router.push(selectionHref("/triage", { dataset: created.id, baseline, comparison }));
      setLoadedFor("");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "The upload did not complete.");
    } finally {
      setBusy(false);
    }
  }

  async function loadPracticeSet() {
    setBusy(true);
    setError(null);
    try {
      const created = await api<{ id: string }>("/api/v1/demo/reset", { method: "POST" });
      router.push(selectionHref("/triage", { dataset: created.id, baseline, comparison }));
      setLoadedFor("");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "The practice set could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="flex min-w-0 flex-col gap-4">
        <Dropzone disabled={busy} onFiles={upload} onPractice={() => void loadPracticeSet()} />
        {error ? (
          <p className="rounded-2xl border border-threat/40 bg-card px-4 py-3 text-sm text-threat" role="alert">
            {error}
          </p>
        ) : null}
        {!dataset ? (
          <EmptyState title="Nothing to triage yet">
            Drop the practice set, or load the 20 labeled emails. Classification starts when the files
            reach the engine. Attachment contents are never opened.
          </EmptyState>
        ) : busy && !rows ? (
          <p className="text-sm text-muted-foreground">Classifying…</p>
        ) : rows ? (
          <Results
            rows={rows}
            tab={tab}
            query={query}
            sort={sort}
            onTab={setTab}
            onQuery={setQuery}
            onSort={setSort}
            hrefFor={(id) => selectionHref(`/triage/${id}`, { dataset, baseline, comparison })}
          />
        ) : null}
      </div>
      <TriageRail
        rows={rows}
        dataset={dataset}
        baseline={baseline}
        comparison={comparison}
      />
    </div>
  );
}

function Dropzone({
  disabled,
  onFiles,
  onPractice,
}: {
  disabled: boolean;
  onFiles: (files: FileList | null, labels: File | null) => void;
  onPractice: () => void;
}) {
  const [labels, setLabels] = useState<File | null>(null);
  return (
    <div className="flex flex-col gap-3">
      <label
        data-testid="triage-dropzone"
        className="relative block cursor-pointer overflow-hidden rounded-3xl border border-dashed border-white/15 bg-[#0c0d14] px-6 py-12 text-center focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          onFiles(event.dataTransfer.files, labels);
        }}
      >
        <span className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(124,92,255,0.22),transparent_62%),radial-gradient(ellipse_at_80%_0%,rgba(255,122,48,0.2),transparent_46%)]" />
        <input
          type="file"
          multiple
          disabled={disabled}
          accept=".eml,.txt,.zip,message/rfc822,text/plain"
          className="sr-only"
          onChange={(event) => onFiles(event.target.files, labels)}
        />
        <span className="relative mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-[#d7dbff]">
          <CloudUpload className="size-6" />
        </span>
        <span className="relative block text-lg font-semibold tracking-[-0.03em]">Upload email files</span>
        <span className="relative mt-1 block text-sm text-[#949aab]">
          Drag and drop .eml, .msg, or .txt files (max 50)
        </span>
        <span className="relative mt-5 inline-flex h-9 items-center rounded-full bg-white px-4 text-sm font-medium text-[#101218]">
          Choose Files
        </span>
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="outline" disabled={disabled} onClick={onPractice}>
          Load the 20-email test set
        </Button>
        <label className="inline-flex h-9 cursor-pointer items-center rounded-full border border-white/10 px-3 text-sm text-[#c8cdd8] hover:bg-white/5">
          {labels ? labels.name : "Add labels CSV"}
          <input
            type="file"
            accept=".csv,text/csv"
            className="sr-only"
            onChange={(event) => setLabels(event.target.files?.[0] ?? null)}
          />
        </label>
      </div>
    </div>
  );
}

function Results({
  rows,
  tab,
  query,
  sort,
  onTab,
  onQuery,
  onSort,
  hrefFor,
}: {
  rows: TriageResponse;
  tab: "all" | Verdict;
  query: string;
  sort: string;
  onTab: (tab: "all" | Verdict) => void;
  onQuery: (value: string) => void;
  onSort: (value: string) => void;
  hrefFor: (id: string) => string;
}) {
  const tabs: { id: "all" | Verdict; label: string; count: number }[] = [
    { id: "all", label: "All", count: rows.counts.all },
    { id: "phishing", label: "Phishing", count: rows.counts.phishing },
    { id: "genuine", label: "Genuine", count: rows.counts.genuine },
  ];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex gap-1 rounded-full border border-white/10 bg-black/25 p-1" role="tablist" aria-label="Prediction">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              data-testid={`triage-tab-${item.id}`}
              aria-selected={tab === item.id}
              className={
                tab === item.id
                  ? "inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-sm text-white"
                  : "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm text-[#949aab]"
              }
              onClick={() => onTab(item.id)}
            >
              <span
                className={
                  item.id === "phishing"
                    ? "size-1.5 rounded-full bg-[#ff5c6c]"
                    : item.id === "genuine"
                      ? "size-1.5 rounded-full bg-[#3ddc97]"
                      : "size-1.5 rounded-full bg-[#c8cdd8]"
                }
              />
              {item.label}
              <span className="font-mono text-xs text-[#c8cdd8]">{item.count}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            value={query}
            aria-label="Search emails"
            placeholder="Search by sender, subject, or ID..."
            className="h-9 min-w-56 rounded-full border border-white/10 bg-black/30 px-4 text-sm"
            onChange={(event) => onQuery(event.target.value)}
          />
          <select
            aria-label="Sort"
            data-testid="sort-risk"
            value={sort}
            className="h-9 rounded-full border border-white/10 bg-black/30 px-3 text-sm"
            onChange={(event) => onSort(event.target.value)}
          >
            <option value="-risk">Highest risk</option>
            <option value="risk">Lowest risk</option>
            <option value="subject">Subject</option>
            <option value="sender">Sender</option>
          </select>
        </div>
      </div>
      {rows.emails.length === 0 ? (
        <EmptyState title="No emails match">Try another search, or switch back to All.</EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-white/8 bg-black/20">
          <table className="w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border">
                <th className="px-4 py-2 font-medium">Subject</th>
                <th className="px-4 py-2 font-medium">Sender</th>
                <th className="px-4 py-2 font-medium">Prediction</th>
                <th className="px-4 py-2 font-medium">Risk</th>
                <th className="px-4 py-2 font-medium">Vector</th>
                <th className="px-4 py-2 font-medium">Top evidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.emails.map((email) => (
                <tr key={email.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      href={hrefFor(email.id)}
                      data-testid="triage-row"
                      data-risk={email.risk_score}
                      className="font-medium underline-offset-2 hover:underline"
                    >
                      {email.subject}
                    </Link>
                    <span className="mt-1 block font-mono text-xs text-muted-foreground">{email.filename}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="block">{email.sender}</span>
                    <span className="font-mono text-xs text-muted-foreground">{email.sender_domain}</span>
                  </td>
                  <td className="px-4 py-3">
                    <VerdictText label={email.prediction} />
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        email.risk_score >= 0.45
                          ? "inline-flex min-w-12 justify-center rounded-full bg-[#ff5c6c] px-2 py-0.5 font-mono text-xs font-semibold text-white"
                          : "inline-flex min-w-12 justify-center rounded-full bg-[#12392c] px-2 py-0.5 font-mono text-xs font-semibold text-[#3ddc97]"
                      }
                    >
                      {formatScore(email.risk_score)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {email.prediction === "genuine" ? "None" : vectorLabel(email.attack_vector)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{email.top_evidence ?? "No warning signs"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TriageRail({
  rows,
  dataset,
  baseline,
  comparison,
}: {
  rows: TriageResponse | null;
  dataset: string | null;
  baseline: string | null;
  comparison: string | null;
}) {
  const total = rows?.counts.all ?? 0;
  const phishing = rows?.counts.phishing ?? 0;
  const genuine = rows?.counts.genuine ?? 0;
  const labeled = rows?.emails.filter((email) => email.ground_truth) ?? [];
  const correct = labeled.filter((email) => email.ground_truth === email.prediction).length;
  const accuracy = labeled.length > 0 ? correct / labeled.length : null;
  const href = (path: string) => selectionHref(path, { dataset, baseline, comparison });
  return (
    <aside className="grid gap-3">
      <section className="ls-panel p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Batch summary</h2>
          <span className="rounded-full bg-[#12392c] px-2 py-0.5 text-[11px] font-medium text-[#3ddc97]">
            {rows ? "Analysis complete" : "Waiting"}
          </span>
        </div>
        <p className="mt-1 text-xs text-[#949aab]">{dataset ? `Current analysis: ${dataset}` : "No dataset loaded"}</p>
        <div className="mt-4 grid grid-cols-3 gap-2">
          <Stat icon="mail" label="Total emails" value={total} />
          <Stat icon="alert" label="Phishing" value={phishing} />
          <Stat icon="shield" label="Genuine" value={genuine} />
        </div>
      </section>
      <section className="ls-panel p-4">
        <h2 className="text-sm font-semibold">Classification results</h2>
        <div className="mt-3 flex items-center gap-4">
          <MiniDonut phishing={phishing} total={total} />
          <div className="grid gap-2 text-xs">
            <p className="flex items-center gap-2 text-[#ff8b96]">
              <span className="size-2 rounded-full bg-[#ff5c6c]" />
              Phishing {phishing} ({share(phishing, total)})
            </p>
            <p className="flex items-center gap-2 text-[#3ddc97]">
              <span className="size-2 rounded-full bg-[#3ddc97]" />
              Genuine {genuine} ({share(genuine, total)})
            </p>
          </div>
        </div>
      </section>
      <section className="ls-panel p-4">
        <h2 className="text-sm font-semibold">Model performance</h2>
        <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[#3ddc97]">
          {accuracy == null ? "—" : `${(accuracy * 100).toFixed(1)}%`}
        </p>
        <p className="text-xs text-[#949aab]">Classification accuracy</p>
        <p className="mt-3 text-xs text-[#c8cdd8]">
          {labeled.length > 0
            ? `${correct} of ${labeled.length} labeled emails match`
            : "Load a labels file to score accuracy"}
        </p>
      </section>
      <section className="ls-panel p-3">
        <h2 className="px-2 text-sm font-semibold">Quick actions</h2>
        <div className="mt-2 grid">
          <QuickLink href={href("/simulator")} icon={<Play className="size-3.5" />} label="Run layered simulation" />
          <QuickLink href={href("/compare")} icon={<GitCompare className="size-3.5" />} label="Compare configurations" />
          <QuickLink href={href("/reports")} icon={<Shield className="size-3.5" />} label="Open validation report" />
        </div>
      </section>
    </aside>
  );
}

function Stat({ icon, label, value }: { icon: "mail" | "alert" | "shield"; label: string; value: number }) {
  const tone =
    icon === "alert"
      ? "border-[#ff5c6c]/30 bg-[#2a1218] text-[#ff8b96]"
      : icon === "shield"
        ? "border-[#3ddc97]/25 bg-[#10291f] text-[#3ddc97]"
        : "border-white/10 bg-white/5 text-white";
  return (
    <div className={`rounded-2xl border px-2 py-3 text-center ${tone}`}>
      <p className="text-xl font-semibold tracking-[-0.04em]">{value}</p>
      <p className="mt-1 text-[10px] leading-4 text-[#949aab]">{label}</p>
    </div>
  );
}

function MiniDonut({ phishing, total }: { phishing: number; total: number }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const slice = total > 0 ? (phishing / total) * circumference : 0;
  return (
    <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
      <circle cx="42" cy="42" r={radius} fill="none" stroke="#3ddc97" strokeWidth="8" />
      <circle
        cx="42"
        cy="42"
        r={radius}
        fill="none"
        stroke="#ff5c6c"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={`${slice} ${circumference - slice}`}
        transform="rotate(-90 42 42)"
      />
      <text x="42" y="40" textAnchor="middle" fill="#f4f6fb" fontSize="14" fontWeight="700">{total}</text>
      <text x="42" y="52" textAnchor="middle" fill="#949aab" fontSize="8">Emails</text>
    </svg>
  );
}

function share(part: number, total: number) {
  if (total <= 0) return "0%";
  return `${Math.round((part / total) * 100)}%`;
}

function QuickLink({ href, icon, label }: { href: string; icon: ReactNode; label: string }) {
  return (
    <Link href={href} className="flex items-center justify-between rounded-xl px-2 py-2 text-sm text-[#d5d8e2] hover:bg-white/5">
      <span className="inline-flex items-center gap-2">{icon}{label}</span>
      <span aria-hidden="true">→</span>
    </Link>
  );
}
