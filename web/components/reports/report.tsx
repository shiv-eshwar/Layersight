"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shell/empty-state";
import { Button } from "@/components/ui/button";
import { ApiError, api, selectionHref } from "@/lib/api";
import { formatPct, formatScore } from "@/lib/format";
import type { ValidationReport } from "@/lib/types";

export function Report() {
  const params = useSearchParams();
  const dataset = params.get("dataset");
  const baseline = params.get("baseline");
  const comparison = params.get("comparison");
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dataset) return;
    const search = new URLSearchParams();
    if (baseline) search.set("baseline", baseline);
    if (comparison) search.set("comparison", comparison);
    const suffix = search.toString();
    let cancelled = false;
    void api<ValidationReport>(`/api/v1/datasets/${dataset}/validation${suffix ? `?${suffix}` : ""}`)
      .then((body) => {
        if (!cancelled) {
          setReport(body);
          setError(null);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof ApiError ? reason.message : "The report could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [dataset, baseline, comparison]);

  if (!dataset) {
    return (
      <EmptyState
        title="No dataset selected"
        action={<Button variant="outline" render={<Link href="/triage" />}>Open triage</Button>}
      >
        Upload emails with a labels file, or load the 20-email test set. Accuracy appears here only when labels exist.
      </EmptyState>
    );
  }
  if (error) return <p className="text-sm text-threat" role="alert">{error}</p>;
  if (!report) return <p className="text-sm text-muted-foreground">Computing the report…</p>;

  const query = new URLSearchParams();
  if (baseline) query.set("baseline", baseline);
  if (comparison) query.set("comparison", comparison);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const correct = report.correct ?? 0;
  const labeled = report.labeled;

  return (
    <article className="report-sheet flex flex-col gap-8">
      <header>
        <p className="font-mono text-5xl tabular-nums">
          {labeled > 0 ? `${correct} / ${labeled}` : "No labels"}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          {labeled > 0
            ? `${formatPct(report.accuracy ?? 0)} accuracy on ${report.dataset_name}.`
            : "This dataset has predictions, but no labels file, so accuracy cannot be scored."}
        </p>
      </header>

      {labeled > 0 ? (
        <>
          <section className="grid gap-6 md:grid-cols-[16rem_1fr]">
            <table className="border border-border text-sm">
              <caption className="px-3 py-2 text-left text-muted-foreground">Confusion matrix</caption>
              <thead>
                <tr className="text-muted-foreground">
                  <th className="px-3 py-2" />
                  <th className="px-3 py-2 font-medium">Pred. phishing</th>
                  <th className="px-3 py-2 font-medium">Pred. genuine</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Actual phishing</th>
                  <td className="px-3 py-2 font-mono">{report.confusion.tp}</td>
                  <td className="px-3 py-2 font-mono">{report.confusion.fn}</td>
                </tr>
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Actual genuine</th>
                  <td className="px-3 py-2 font-mono">{report.confusion.fp}</td>
                  <td className="px-3 py-2 font-mono">{report.confusion.tn}</td>
                </tr>
              </tbody>
            </table>
            <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
              <Metric label="Precision" value={report.precision} />
              <Metric label="Recall" value={report.recall} />
              <Metric label="F1" value={report.f1} />
              <Metric label="False-positive rate" value={report.false_positive_rate} />
            </dl>
          </section>
          <section>
            <h2 className="text-base font-semibold">Misclassifications</h2>
            {report.misclassifications.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No misclassifications on this dataset.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-4">
                {report.misclassifications.map((row) => (
                  <li key={row.filename} className="border-l-2 border-threat pl-3 text-sm leading-6">
                    <p className="font-medium">{row.subject}</p>
                    <p className="text-muted-foreground">{row.explanation}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      <section>
        <h2 className="text-base font-semibold">Modeled pass-through</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6">{report.pass_through.narrative}</p>
        <p className="mt-2 font-mono text-sm">
          {report.pass_through.baseline.config_name} {formatPct(report.pass_through.baseline.simulation.closed_form)}
          {" → "}
          {report.pass_through.comparison.config_name} {formatPct(report.pass_through.comparison.simulation.closed_form)}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">Figures are model estimates from the assumptions shown, not measured outcomes.</p>
      </section>

      <section className="overflow-x-auto">
        <h2 className="text-base font-semibold">Per email</h2>
        <table className="mt-3 w-full text-left text-sm">
          <thead className="text-muted-foreground">
            <tr className="border-b border-border">
              <th className="py-2 font-medium">Subject</th>
              <th className="py-2 font-medium">Label</th>
              <th className="py-2 font-medium">Prediction</th>
              <th className="py-2 font-medium">Risk</th>
              <th className="py-2 font-medium">Result</th>
            </tr>
          </thead>
          <tbody>
            {report.per_email.map((row) => (
              <tr key={row.filename} className="border-b border-border">
                <td className="py-2 pr-3">{row.subject}</td>
                <td className="py-2 pr-3">{row.actual ?? "—"}</td>
                <td className="py-2 pr-3">{row.predicted}</td>
                <td className="py-2 pr-3 font-mono">{formatScore(row.risk_score)}</td>
                <td className={`py-2 ${row.correct === false ? "text-threat" : ""}`}>
                  {row.correct === null ? "Unlabeled" : row.correct ? "Correct" : "Wrong"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <footer className="grid gap-2 border-t border-border pt-4 text-sm sm:grid-cols-2">
        <p>Engine version <span className="font-mono">{report.engine_version}</span></p>
        <p>Weights hash <span className="font-mono">{report.weights_hash}</span></p>
        <p>Seed <span className="font-mono">{report.pass_through.seed}</span></p>
        <p>Runs per email <span className="font-mono">{report.pass_through.runs.toLocaleString("en-US")}</span></p>
        {report.notes.map((note) => (
          <p key={note} className="sm:col-span-2 text-muted-foreground">{note}</p>
        ))}
      </footer>

      <div className="no-print flex flex-wrap gap-3">
        <a className="text-sm text-intelligence underline-offset-2 hover:underline" href={`/api/v1/datasets/${dataset}/report.json${suffix}`}>
          Download JSON
        </a>
        <a className="text-sm text-intelligence underline-offset-2 hover:underline" href={`/api/v1/datasets/${dataset}/report.csv${suffix}`}>
          Download CSV
        </a>
        <button type="button" className="text-sm text-intelligence underline-offset-2 hover:underline" onClick={() => window.print()}>
          Print report
        </button>
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-mono text-lg tabular-nums">{value === null ? "—" : formatPct(value)}</dd>
    </div>
  );
}
