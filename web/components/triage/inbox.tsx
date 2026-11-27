"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

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
  const [query, setQuery] = useState("");
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
    <div className="flex flex-col gap-6">
      <Dropzone disabled={busy} onFiles={upload} onPractice={() => void loadPracticeSet()} />
      {error ? (
        <p className="border border-threat/40 bg-card px-4 py-3 text-sm text-threat" role="alert">
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
        className="block cursor-pointer border border-dashed border-border bg-card px-6 py-8 text-center focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          onFiles(event.dataTransfer.files, labels);
        }}
      >
        <input
          type="file"
          multiple
          disabled={disabled}
          accept=".eml,.txt,.zip,message/rfc822,text/plain"
          className="sr-only"
          onChange={(event) => onFiles(event.target.files, labels)}
        />
        <span className="block text-sm font-medium">Drop .eml or .txt files, or a .zip</span>
        <span className="mt-1 block text-sm text-muted-foreground">
          Add a labels file if you want Reports to score accuracy.
        </span>
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-muted-foreground">
          Labels CSV
          <input
            type="file"
            accept=".csv,text/csv"
            className="ml-2 text-foreground"
            onChange={(event) => setLabels(event.target.files?.[0] ?? null)}
          />
        </label>
        <Button type="button" variant="outline" disabled={disabled} onClick={onPractice}>
          Load the 20-email test set
        </Button>
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
        <div className="flex gap-1" role="tablist" aria-label="Prediction">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              className={
                tab === item.id
                  ? "border-b-2 border-intelligence px-3 py-2 text-sm"
                  : "border-b-2 border-transparent px-3 py-2 text-sm text-muted-foreground"
              }
              onClick={() => onTab(item.id)}
            >
              {item.label} <span className="font-mono">{item.count}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            value={query}
            aria-label="Search emails"
            placeholder="Sender, subject, or domain"
            className="h-8 border border-border bg-background px-3 text-sm"
            onChange={(event) => onQuery(event.target.value)}
          />
          <select
            aria-label="Sort"
            value={sort}
            className="h-8 border border-border bg-background px-2 text-sm"
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
        <div className="overflow-x-auto border border-border">
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
                    <Link href={hrefFor(email.id)} className="font-medium underline-offset-2 hover:underline">
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
                  <td className="px-4 py-3 font-mono tabular-nums">{formatScore(email.risk_score)}</td>
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
