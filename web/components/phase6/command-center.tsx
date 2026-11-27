"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shell/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { formatCount, formatPct, formatScore, vectorLabel } from "@/lib/format";
import { loadCommand, type CommandCenter, type Outlook } from "@/lib/phase6";
import { useWorkspaceDataset } from "@/lib/use-dataset";

export function CommandCenter() {
  const dataset = useWorkspaceDataset();
  const [report, setReport] = useState<CommandCenter | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dataset) return;
    let cancelled = false;
    setReport(null);
    setError(null);
    void loadCommand(dataset)
      .then((body) => {
        if (!cancelled) setReport(body);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof ApiError ? reason.message : "The command center could not load.");
      });
    return () => {
      cancelled = true;
    };
  }, [dataset]);

  if (!dataset) {
    return <p className="text-sm text-muted-foreground">Loading the dataset.</p>;
  }
  if (dataset === "empty") {
    return (
      <EmptyState title="No emails loaded" action={<Link href="/triage" className={buttonVariants()}>Upload emails</Link>}>
        Upload a set to see residual risk, where attacks stop, and which change reduces that risk the most.
      </EmptyState>
    );
  }
  if (error) {
    return (
      <EmptyState title="The command center could not load">
        {error} Start the API, or open the development corpus from this screen with the dataset set to dev.
      </EmptyState>
    );
  }
  if (!report) {
    return <p className="text-sm text-muted-foreground">Loading modeled exposure for this dataset.</p>;
  }
  if (report.summary.email_count === 0) {
    return (
      <EmptyState title="No emails loaded" action={<Link href="/triage" className={buttonVariants()}>Upload emails</Link>}>
        Upload a set to see residual risk, where attacks stop, and which change reduces that risk the most.
      </EmptyState>
    );
  }

  const { summary } = report;
  return (
    <div className="grid gap-8">
      <section className="grid gap-3 sm:grid-cols-4">
        <Kpi label="Emails analyzed" value={formatCount(summary.email_count)} href="/triage" />
        <Kpi label="Predicted phishing" value={formatCount(summary.phishing_count ?? 0)} href="/triage" />
        <Kpi label="Predicted genuine" value={formatCount(summary.genuine_count ?? 0)} href="/triage" />
        <Kpi
          label="Accuracy"
          value={summary.accuracy == null ? "—" : formatPct(summary.accuracy)}
          hint={summary.labeled ? `${summary.correct} of ${summary.labeled} labeled` : "No labels"}
          href="/reports"
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="border border-border bg-card p-5">
          <h2 className="text-base font-semibold">Residual risk</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {report.user_layer_source === "quiz"
              ? "After uses the quiz accuracy as the user-layer catch rate."
              : "Before is untrained. After is the trained configuration."}
          </p>
          <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
            <Rate outlook={report.before} />
            <p className="font-mono text-2xl text-protected">
              {summary.relative_reduction == null ? "—" : `${(summary.relative_reduction * 100).toFixed(1)}%`}
              <span className="mt-1 block text-xs font-sans text-muted-foreground">lower</span>
            </p>
            <Rate outlook={report.after} />
          </div>
          {report.user_layer_source === "quiz" && report.trained_pass_rate != null ? (
            <p className="mt-4 text-sm text-muted-foreground">
              Advanced training, without the quiz rate, leaves a modeled pass-through of {formatPct(report.trained_pass_rate)}.
            </p>
          ) : null}
        </div>
        <Donut outlook={report.before} />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Funnel outlook={report.before} />
        <div className="border border-border bg-card p-5">
          <h2 className="text-base font-semibold">Top recommendation</h2>
          {report.recommendation ? (
            <>
              <p className="mt-3 font-medium">{report.recommendation.title}</p>
              <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">{report.recommendation.detail}</p>
              <Link href="/defense" className={`${buttonVariants({ variant: "outline" })} mt-4`}>
                Open Defense
              </Link>
            </>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">No modeled reduction is available for this set.</p>
          )}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-base font-semibold">Highest-risk emails</h2>
          <ul className="mt-3 divide-y divide-border border border-border">
            {report.threats.map((threat) => (
              <li key={threat.email_id}>
                <Link href={`/triage/${threat.email_id}`} className="block px-4 py-3 hover:bg-card">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="font-medium">{threat.subject}</span>
                    <span className={`font-mono ${threat.label === "phishing" ? "text-threat" : "text-protected"}`}>
                      {formatScore(threat.risk_score)}
                    </span>
                  </span>
                  <span className="mt-1 block text-sm text-muted-foreground">
                    {threat.sender} · {vectorLabel(threat.attack_vector)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-base font-semibold">Most-impersonated brands</h2>
          <ul className="mt-3 divide-y divide-border border border-border">
            {report.brands.length === 0 ? (
              <li className="px-4 py-3 text-sm text-muted-foreground">No look-alike domains in this set.</li>
            ) : (
              report.brands.map((brand) => (
                <li key={brand.brand} className="flex items-baseline justify-between gap-3 px-4 py-3">
                  <Link href={`/intelligence?brand=${encodeURIComponent(brand.brand)}`} className="font-mono text-sm text-intelligence">
                    {brand.brand}
                  </Link>
                  <span className="text-sm text-muted-foreground">
                    {brand.occurrences} · {brand.technique.replaceAll("_", " ")}
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>
      <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{report.note}</p>
    </div>
  );
}

function Kpi({ label, value, hint, href }: { label: string; value: string; hint?: string; href: string }) {
  return (
    <Link href={href} className="border border-white/8 bg-card px-4 py-4">
      <span className="block text-sm text-muted-foreground">{label}</span>
      <span className="mt-1 block font-mono text-2xl">{value}</span>
      {hint ? <span className="mt-1 block text-xs text-muted-foreground">{hint}</span> : null}
    </Link>
  );
}

function Rate({ outlook }: { outlook: Outlook }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{outlook.name}</p>
      <p className="mt-1 font-mono text-4xl text-threat">
        {outlook.closed_form == null ? "—" : formatPct(outlook.closed_form)}
      </p>
      {outlook.uncertainty ? (
        <p className="mt-1 font-mono text-xs text-muted-foreground">
          5th–95th {formatPct(outlook.uncertainty.p05)}–{formatPct(outlook.uncertainty.p95)}
        </p>
      ) : null}
    </div>
  );
}

function Donut({ outlook }: { outlook: Outlook }) {
  const blocked = outlook.blocked ?? 0;
  const passed = outlook.passed ?? 0;
  const total = blocked + passed || 1;
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const passedLength = (passed / total) * circumference;
  return (
    <figure className="border border-border bg-card p-5">
      <figcaption className="text-base font-semibold">Blocked versus passed</figcaption>
      <p className="mt-1 text-sm text-muted-foreground">Modeled estimate, untrained configuration.</p>
      <div className="mt-4 flex items-center gap-5">
        <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r={radius} fill="none" stroke="#2a2e3c" strokeWidth="12" />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="#3ddc97"
            strokeWidth="12"
            strokeDasharray={`${circumference - passedLength} ${passedLength}`}
            transform="rotate(-90 60 60)"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="#ff5c6c"
            strokeWidth="12"
            strokeDasharray={`${passedLength} ${circumference - passedLength}`}
            strokeDashoffset={-(circumference - passedLength)}
            transform="rotate(-90 60 60)"
          />
        </svg>
        <div className="text-sm">
          <p><span className="mr-2 inline-block size-2 bg-protected" />Blocked {formatCount(blocked)}</p>
          <p className="mt-2"><span className="mr-2 inline-block size-2 bg-threat" />Passed {formatCount(passed)}</p>
        </div>
      </div>
    </figure>
  );
}

function Funnel({ outlook }: { outlook: Outlook }) {
  return (
    <section className="border border-border bg-card p-5">
      <h2 className="text-base font-semibold">Where attacks stop</h2>
      <p className="mt-1 text-sm text-muted-foreground">Per {formatCount(outlook.runs)} modeled runs. Green is stopped.</p>
      <ol className="mt-4 grid gap-3">
        {outlook.funnel.map((step) => {
          const width = outlook.runs ? (step.entered / outlook.runs) * 100 : 0;
          const stopped = step.entered ? (step.stopped / step.entered) * 100 : 0;
          const passed = step.layer === "passed";
          return (
            <li key={step.layer}>
              <div className="flex justify-between text-sm">
                <span>{step.label}</span>
                <span className="font-mono">{formatCount(step.entered)}</span>
              </div>
              <div className="mt-1 h-2 bg-background">
                <div className="h-full" style={{ width: `${width}%`, background: passed ? "#ff5c6c" : "#2a2e3c" }}>
                  {passed ? null : <div className="h-full bg-protected" style={{ width: `${stopped}%` }} />}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
