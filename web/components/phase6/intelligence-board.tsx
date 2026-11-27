"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shell/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { formatScore } from "@/lib/format";
import { checkDomain, loadDomains, type DomainReport, type SimilarityView } from "@/lib/phase6";

export function IntelligenceBoard() {
  const params = useSearchParams();
  const dataset = params.get("dataset") || "dev";
  const brand = params.get("brand") ?? "";
  const [report, setReport] = useState<DomainReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [candidate, setCandidate] = useState("paypa1.com");
  const [checked, setChecked] = useState<SimilarityView | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setReport(null);
    setError(null);
    void loadDomains(dataset)
      .then((body) => {
        if (!cancelled) setReport(body);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof ApiError ? reason.message : "Domain intelligence could not load.");
      });
    return () => {
      cancelled = true;
    };
  }, [dataset]);

  async function onCheck(event: React.FormEvent) {
    event.preventDefault();
    setChecking(true);
    try {
      setChecked(await checkDomain(candidate));
    } catch (reason) {
      setChecked(null);
      setError(reason instanceof ApiError ? reason.message : "The checker could not score that domain.");
    } finally {
      setChecking(false);
    }
  }

  if (dataset === "empty") {
    return <EmptyState title="No domains to compare">Upload emails in Triage. Sender, reply, and link domains will be scored here.</EmptyState>;
  }

  return (
    <div className="grid gap-8">
      <form onSubmit={onCheck} className="border border-border bg-card p-5">
        <h2 className="text-base font-semibold">Domain checker</h2>
        <p className="mt-1 max-w-xl text-sm text-muted-foreground">
          Score any domain against the protected brands. Nothing is looked up on the network.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <label className="sr-only" htmlFor="domain-checker">Domain</label>
          <input
            id="domain-checker"
            value={candidate}
            onChange={(event) => setCandidate(event.target.value)}
            className="h-9 min-w-64 border border-border bg-background px-3 font-mono text-sm"
            spellCheck={false}
          />
          <button type="submit" className={buttonVariants()} disabled={checking}>
            {checking ? "Scoring" : "Score domain"}
          </button>
        </div>
        {checked ? <DiffResult view={checked} /> : null}
      </form>

      {error ? <p className="text-sm text-threat">{error}</p> : null}
      {!report && !error ? <p className="text-sm text-muted-foreground">Loading domains from this dataset.</p> : null}
      {report && report.domains.length === 0 ? (
        <EmptyState title="No domains to compare">This dataset has no sender, reply, or link domains yet.</EmptyState>
      ) : null}
      {report && report.domains.length > 0 ? (
        <>
          <section>
            <h2 className="text-base font-semibold">Domains in this dataset</h2>
            <div className="mt-3 overflow-x-auto border border-border">
              <table className="w-full text-left text-sm">
                <thead className="text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Domain</th>
                    <th className="px-3 py-2 font-medium">Closest brand</th>
                    <th className="px-3 py-2 font-medium">Score</th>
                    <th className="px-3 py-2 font-medium">Technique</th>
                    <th className="px-3 py-2 font-medium">Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {report.domains
                    .filter((row) => !brand || row.closest_brand === brand)
                    .map((row) => (
                      <tr key={row.domain} className="border-t border-border">
                        <td className="px-3 py-2 font-mono">{row.domain}</td>
                        <td className="px-3 py-2 font-mono">{row.closest_brand ?? "—"}</td>
                        <td className="px-3 py-2 font-mono">{formatScore(row.similarity)}</td>
                        <td className="px-3 py-2">{row.technique.replaceAll("_", " ")}</td>
                        <td className="px-3 py-2 font-mono">{row.occurrences}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>
          <section>
            <h2 className="text-base font-semibold">Deceptive links</h2>
            {report.deceptive_links.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No link text points at a different domain than the address.</p>
            ) : (
              <ul className="mt-3 grid gap-3">
                {report.deceptive_links.map((link) => (
                  <li key={`${link.email_id}-${link.href}`} className="border border-border bg-card px-4 py-3">
                    <p className="text-sm">{link.subject}</p>
                    <p className="mt-2 font-mono text-sm">
                      <span>{link.visible_domain}</span>
                      <span className="px-2 text-muted-foreground">reads as</span>
                      <span className="text-threat">{link.real_domain}</span>
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{link.sentence}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}

function DiffResult({ view }: { view: SimilarityView }) {
  const parts = view.diff.split(/(\[[^\]]+\])/);
  return (
    <div className="mt-4">
      <p className="font-mono text-3xl">
        {view.legitimate ? "Legitimate" : formatScore(view.score)}
        <span className="ml-3 text-base text-muted-foreground">{view.technique.replaceAll("_", " ")}</span>
      </p>
      <p className="mt-2 font-mono text-sm">
        {parts.map((part, index) =>
          part.startsWith("[") ? (
            <span key={`${part}-${index}`} className="text-threat">{part}</span>
          ) : (
            <span key={`${part}-${index}`}>{part}</span>
          ),
        )}
      </p>
      <p className="mt-2 max-w-xl text-sm">{view.sentence}</p>
    </div>
  );
}
