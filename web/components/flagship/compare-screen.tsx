"use client";

import { useMemo, useState } from "react";

import { EmptyState } from "@/components/shell/empty-state";
import { formatCount, formatPct, formatRel } from "@/lib/flagship/format";
import { compareVersion, useFlagship } from "@/lib/flagship/store";
import { LAYER_LABEL, LAYERS, VECTOR_LABEL } from "@/lib/flagship/types";
import { useComparisonPreview } from "@/lib/flagship/use-results";
import { useWorkspaceDataset } from "@/lib/use-dataset";

export function CompareScreen() {
  const datasetId = useWorkspaceDataset();
  const draft = useFlagship((state) => state.draft);
  const dirty = useFlagship((state) => state.dirty);
  const other = useFlagship((state) => compareVersion(state)?.config);
  const [runs, setRuns] = useState(10_000);
  const [seed, setSeed] = useState(42);
  const preview = useComparisonPreview(draft, other ?? draft, datasetId, runs, seed);
  const subjects = useMemo(() => {
    const found = new Map<string, string>();
    for (const email of preview.result?.result_a.per_email ?? []) {
      found.set(email.email_id, email.subject || email.filename || email.email_id);
      if (email.id) found.set(email.id, email.subject || email.filename || email.email_id);
    }
    return found;
  }, [preview.result]);

  if (!datasetId) {
    return (
      <EmptyState title="No dataset selected">
        Load the 20-email test set in Triage, then compare the untrained and trained configurations.
      </EmptyState>
    );
  }

  if (!other || !preview.result) {
    return (
      <p className="ls-card p-4" role="status" data-testid="compare-screen">
        {preview.error ?? "Comparing the two configurations."}
      </p>
    );
  }

  const result = preview.result;
  const reduction = result.relative_reduction;
  const improved = reduction >= 0;

  return (
    <div data-testid="compare-screen" className="grid gap-4">
      <p className="text-sm text-[#949aab]">
        Same emails, same seed, two configurations. The difference is the control change.
      </p>

      <section className="ls-card flex flex-wrap items-end gap-3 p-4">
        <label className="grid gap-1 text-sm text-[#949aab]">
          Runs
          <select aria-label="Runs" value={runs} onChange={(event) => setRuns(Number(event.target.value))}>
            <option value={1000}>1,000</option>
            <option value={10000}>10,000</option>
            <option value={100000}>100,000</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm text-[#949aab]">
          Seed
          <input
            type="number"
            aria-label="Seed"
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value) || 0)}
          />
        </label>
      </section>

      <section className="ls-card p-5">
        <p className="max-w-3xl text-lg leading-7" data-testid="comparison-narrative">
          {result.narrative}
        </p>
        <p className={`ls-mono mt-4 text-5xl ${improved ? "text-[#3ddc97]" : "text-[#ff5c6c]"}`} data-testid="relative-reduction" data-value={reduction}>
          {formatRel(reduction)}
        </p>
        <p className="mt-1 text-sm text-[#949aab]">
          {improved ? "modeled reduction in pass-through" : "modeled increase in pass-through"}
          {dirty ? " · baseline includes unsaved edits" : ""}
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <article className="ls-card p-4" data-testid="result-card-a" data-pass-rate={result.result_a.aggregate.closed_form}>
          <h2 className="text-base font-semibold">{result.config_a_name}</h2>
          <p className="ls-mono mt-2 text-3xl text-[#ff5c6c]">
            {formatPct(result.result_a.aggregate.closed_form)}
          </p>
          <p className="text-sm text-[#949aab]">modeled pass-through</p>
        </article>
        <article className="ls-card p-4" data-testid="result-card-b" data-pass-rate={result.result_b.aggregate.closed_form}>
          <h2 className="text-base font-semibold">{result.config_b_name}</h2>
          <p className="ls-mono mt-2 text-3xl text-[#3ddc97]">
            {formatPct(result.result_b.aggregate.closed_form)}
          </p>
          <p className="text-sm text-[#949aab]">modeled pass-through</p>
        </article>
      </div>

      <section className="ls-card p-4" data-testid="config-diff">
        <h2 className="text-base font-semibold">What changed</h2>
        {result.changes.length === 0 ? (
          <p className="mt-2 text-sm" role="status">
            The two configurations match.
          </p>
        ) : (
          <ul className="mt-3 grid gap-2 text-sm">
            {result.changes.map((change) => (
              <li key={change.path} className="ls-mono text-[#f4f6fb]">
                {change.path}: {String(change.before)} → {String(change.after)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="ls-card overflow-x-auto p-4">
        <h2 className="text-base font-semibold">Stops by layer</h2>
        <table className="mt-3 w-full min-w-[32rem] text-left text-sm">
          <thead className="text-[#949aab]">
            <tr>
              <th className="py-1 font-medium">Layer</th>
              <th className="py-1 font-medium">Baseline stopped</th>
              <th className="py-1 font-medium">Comparison stopped</th>
              <th className="py-1 font-medium">Difference</th>
            </tr>
          </thead>
          <tbody>
            {LAYERS.map((layer) => {
              const left = result.result_a.aggregate.layers.find((item) => item.layer === layer);
              const right = result.result_b.aggregate.layers.find((item) => item.layer === layer);
              const delta = (right?.stopped ?? 0) - (left?.stopped ?? 0);
              return (
                <tr key={layer} className="border-t border-[#2a2e3c]">
                  <th className="py-2 font-normal">{LAYER_LABEL[layer]}</th>
                  <td className="ls-mono">{formatCount(left?.stopped ?? 0)}</td>
                  <td className="ls-mono">{formatCount(right?.stopped ?? 0)}</td>
                  <td className={`ls-mono ${delta >= 0 ? "text-[#3ddc97]" : "text-[#ff5c6c]"}`}>
                    {delta >= 0 ? "+" : ""}
                    {formatCount(delta)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="ls-card overflow-x-auto p-4">
        <h2 className="text-base font-semibold">Per email</h2>
        <p className="mt-1 text-sm text-[#949aab]">Sorted by the largest modeled improvement</p>
        <table className="mt-3 w-full min-w-[40rem] text-left text-sm">
          <thead className="text-[#949aab]">
            <tr>
              <th className="py-1 font-medium">Email</th>
              <th className="py-1 font-medium">Vector</th>
              <th className="py-1 font-medium">Before</th>
              <th className="py-1 font-medium">After</th>
              <th className="py-1 font-medium">Improvement</th>
            </tr>
          </thead>
          <tbody>
            {result.per_email.map((row) => {
              return (
                <tr key={row.email_id} className="border-t border-[#2a2e3c]">
                  <th className="py-2 font-normal">{row.subject || subjects.get(row.email_id) || row.filename || row.email_id}</th>
                  <td>{row.attack_vector ? VECTOR_LABEL[row.attack_vector] : ""}</td>
                  <td className="ls-mono">{formatPct(row.pass_rate_a)}</td>
                  <td className="ls-mono">{formatPct(row.pass_rate_b)}</td>
                  <td className="ls-mono text-[#3ddc97]">{formatPct(row.absolute_reduction)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <p className="text-xs text-[#949aab]" role="status" data-testid="top-recommendation">
        {result.narrative}
        {preview.loading ? " Updating." : ""}
      </p>
    </div>
  );
}
