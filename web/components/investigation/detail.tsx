"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthBadge, BandBadge, DomainDiff, EvidenceList, RiskScore, VerdictText } from "@/components/layersight/marks";
import { EmptyState } from "@/components/shell/empty-state";
import { Button } from "@/components/ui/button";
import { ApiError, api, selectionHref } from "@/lib/api";
import { formatPct, layerLabel, vectorLabel } from "@/lib/format";
import type { Address, EmailDetail } from "@/lib/types";

export function Investigation({ emailId }: { emailId: string }) {
  const params = useSearchParams();
  const dataset = params.get("dataset");
  const baseline = params.get("baseline");
  const comparison = params.get("comparison");
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const search = new URLSearchParams();
    if (baseline) search.set("baseline", baseline);
    if (comparison) search.set("comparison", comparison);
    const suffix = search.toString();
    let cancelled = false;
    void api<EmailDetail>(`/api/v1/emails/${emailId}${suffix ? `?${suffix}` : ""}`)
      .then((body) => {
        if (!cancelled) {
          setDetail(body);
          setError(null);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof ApiError ? reason.message : "This email could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [emailId, baseline, comparison]);

  if (error) {
    return (
      <EmptyState
        title="This email could not be opened"
        action={
          <Button variant="outline" render={<Link href={selectionHref("/triage", { dataset, baseline, comparison })} />}>
            Back to triage
          </Button>
        }
      >
        {error}
      </EmptyState>
    );
  }
  if (!detail) return <p className="text-sm text-muted-foreground">Opening the analysis…</p>;

  const { presentation, analysis } = detail;
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-border pb-6">
        <div>
          <p className="text-sm text-muted-foreground">{presentation.subject || detail.filename}</p>
          <h2 className="mt-2 text-2xl font-semibold">
            <VerdictText label={analysis.label} />
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            <BandBadge band={analysis.band} />
            {analysis.label === "phishing" ? ` · ${vectorLabel(analysis.attack_vector)}` : " · Not treated as an attack"}
          </p>
          <p className="mt-3 max-w-xl text-sm leading-6">{analysis.vector_reason}</p>
          {detail.ground_truth ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Labeled {detail.ground_truth}. The classifier did not see this label.
            </p>
          ) : null}
        </div>
        <RiskScore score={analysis.risk_score} band={analysis.band} />
      </header>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="flex flex-col gap-8">
          <section>
            <h3 className="text-base font-semibold">What to tell the recipient</h3>
            <ul className="mt-3 flex flex-col gap-2 text-sm leading-6">
              {analysis.advice.map((line) => (
                <li key={line} className="border-l-2 border-intelligence pl-3">
                  {line}
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h3 className="text-base font-semibold">Evidence</h3>
            <EvidenceList items={analysis.evidence} />
          </section>
          <Outlook detail={detail} />
        </div>
        <div className="flex flex-col gap-8">
          <section>
            <h3 className="text-base font-semibold">Headers</h3>
            <dl className="mt-3 flex flex-col gap-3 text-sm">
              <Header label="From" party={presentation.sender} mismatch={presentation.mismatches.some((item) => item.includes("display"))} />
              <Header label="Reply-To" party={presentation.reply_to} mismatch={presentation.mismatches.some((item) => item.startsWith("Reply-To"))} />
              <Header label="Return-Path" party={presentation.return_path} mismatch={presentation.mismatches.some((item) => item.startsWith("Return-Path"))} />
              <div>
                <dt className="text-muted-foreground">Date</dt>
                <dd className="font-mono text-[13px]">{presentation.date ?? "No date"}</dd>
              </div>
            </dl>
          </section>
          <section>
            <h3 className="text-base font-semibold">Authentication</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <AuthBadge name="SPF" value={presentation.auth.spf} />
              <AuthBadge name="DKIM" value={presentation.auth.dkim} />
              <AuthBadge name="DMARC" value={presentation.auth.dmarc} />
            </div>
          </section>
          <section>
            <h3 className="text-base font-semibold">Links</h3>
            {presentation.links.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No links.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-4">
                {presentation.links.map((link) => (
                  <li key={`${link.href}-${link.text}`} className="text-sm">
                    <p>{link.text || "Link"}</p>
                    <p className="font-mono text-[13px] text-muted-foreground">{link.display_href}</p>
                    {link.similarity >= 0.8 && link.technique && link.technique !== "legitimate" ? (
                      <DomainDiff diff={link.diff} closest={link.closest} />
                    ) : (
                      <p className="font-mono text-[13px] text-muted-foreground">{link.registrable_domain}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h3 className="text-base font-semibold">Attachments</h3>
            <p className="mt-1 text-sm text-muted-foreground">Attachment contents are not opened. This is metadata only.</p>
            {presentation.attachments.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No attachments.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-2 text-sm">
                {presentation.attachments.map((item) => (
                  <li key={item.filename} className="font-mono text-[13px]">
                    {item.filename} · {item.risk_class}
                    {item.double_extension ? " · double extension" : ""}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h3 className="text-base font-semibold">Body</h3>
            <pre className="mt-3 max-h-96 overflow-auto border border-border bg-background p-4 font-mono text-[13px] leading-6 whitespace-pre-wrap">
              <Highlighted text={presentation.body_text_sanitized || "Empty body."} phrases={presentation.highlights} />
            </pre>
          </section>
        </div>
      </div>
    </div>
  );
}

function Header({ label, party, mismatch }: { label: string; party: Address | null; mismatch: boolean }) {
  return (
    <div>
      <dt className="text-muted-foreground">
        {label}
        {mismatch ? <span className="ml-2 text-threat">Mismatch</span> : null}
      </dt>
      <dd className="font-mono text-[13px]">
        {party ? (
          <>
            {party.display_name ? `${party.display_name} ` : ""}
            {party.address || "Missing"}
          </>
        ) : (
          "Missing"
        )}
      </dd>
    </div>
  );
}

function Outlook({ detail }: { detail: EmailDetail }) {
  if (!detail.outlook) {
    return (
      <section>
        <h3 className="text-base font-semibold">Defense outlook</h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Pass-through is simulated for emails predicted as phishing. This one was predicted genuine.
        </p>
      </section>
    );
  }
  const { baseline, comparison, narrative, relative_reduction: reduction, seed, runs } = detail.outlook;
  return (
    <section>
      <h3 className="text-base font-semibold">Defense outlook</h3>
      <p className="mt-1 text-sm text-muted-foreground">Modeled estimate, not a measured outcome.</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <RateCard title={baseline.config_name} value={baseline.simulation.closed_form} />
        <RateCard title={comparison.config_name} value={comparison.simulation.closed_form} />
      </div>
      <p className="mt-4 max-w-xl text-sm leading-6">{narrative}</p>
      <p className="mt-2 font-mono text-xs text-muted-foreground">
        Relative reduction {formatPct(reduction)} · seed {seed} · {runs.toLocaleString("en-US")} runs
      </p>
      <ol className="mt-4 flex flex-col gap-2">
        {baseline.simulation.layers.map((layer, index) => {
          const other = comparison.simulation.layers[index];
          return (
            <li key={layer.layer} className="grid grid-cols-[9rem_1fr] gap-3 text-sm">
              <span>{layerLabel(layer.layer)}</span>
              <span className="text-muted-foreground">
                {layer.applicable
                  ? `${formatPct(layer.p_stop)} stop, then ${other && other.applicable ? formatPct(other.p_stop) : "n/a"}`
                  : "Not applicable"}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function RateCard({ title, value }: { title: string; value: number }) {
  return (
    <div className="border border-border bg-card px-4 py-3">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="mt-1 font-mono text-2xl tabular-nums">{formatPct(value)}</p>
      <p className="text-xs text-muted-foreground">Closed-form pass-through</p>
    </div>
  );
}

function Highlighted({ text, phrases }: { text: string; phrases: string[] }) {
  if (phrases.length === 0) return <>{text}</>;
  const lower = text.toLowerCase();
  const ranges: { start: number; end: number }[] = [];
  for (const phrase of phrases) {
    const needle = phrase.toLowerCase();
    let from = 0;
    while (needle && from < text.length) {
      const at = lower.indexOf(needle, from);
      if (at < 0) break;
      ranges.push({ start: at, end: at + needle.length });
      from = at + needle.length;
    }
  }
  ranges.sort((left, right) => left.start - right.start);
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  ranges.forEach((range, index) => {
    if (range.start < cursor) return;
    if (range.start > cursor) nodes.push(text.slice(cursor, range.start));
    nodes.push(
      <mark key={index} className="bg-warning/20 text-warning">
        {text.slice(range.start, range.end)}
      </mark>,
    );
    cursor = range.end;
  });
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return <>{nodes}</>;
}
