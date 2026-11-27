"use client";

import { useMemo, useState } from "react";

import { selectEmails, WORKSPACE_EMAILS } from "@/lib/flagship/fixtures";
import { formatCount, formatPct, formatRel } from "@/lib/flagship/format";
import { compareVersion, useFlagship } from "@/lib/flagship/store";
import { LAYER_LABEL, LAYERS, VECTOR_LABEL } from "@/lib/flagship/types";
import { useComparisonPreview } from "@/lib/flagship/use-results";

export function CompareScreen() {
  const draft = useFlagship((state) => state.draft);
  const dirty = useFlagship((state) => state.dirty);
  const other = useFlagship((state) => compareVersion(state)?.config);
  const [scope, setScope] = useState("email_illustrative");
  const [runs, setRuns] = useState(10_000);
  const [seed, setSeed] = useState(42);
  const emails = useMemo(() => selectEmails(scope), [scope]);
  const subjects = useMemo(
    () => new Map(WORKSPACE_EMAILS.map((email) => [email.email_id, email.subject])),
    [],
  );
  const preview = useComparisonPreview(
    draft,
    other ?? draft,
    emails,
    runs,
    seed,
  );

  if (!other) {
    return (
      <p className="ls-card p-4" role="status" data-testid="compare-screen">
        Choose a comparison configuration in the top bar.
      </p>
    );
  }

  const result = preview.result;
  const reduction = result.relative_reduction;
  const improved = reduction >= 0;

  return (
    <div data-testid="compare-screen" className="grid gap-4">
      <p className="text-sm text-[#8A9BB4]">
        Same emails, same seed, two configurations. The difference is the control change.
      </p>

      <section className="ls-card flex flex-wrap items-end gap-3 p-4">
        <label className="grid gap-1 text-sm text-[#8A9BB4]">
          Scope
          <select aria-label="Scope" value={scope} onChange={(event) => setScope(event.target.value)}>
            <option value="email_illustrative">Illustrative malware (all five layers)</option>
            <option value="all">All phishing emails</option>
            {WORKSPACE_EMAILS.filter((email) => email.email_id !== "email_illustrative").map((email) => (
              <option key={email.email_id} value={email.email_id}>
                {email.subject}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm text-[#8A9BB4]">
          Runs
          <select aria-label="Runs" value={runs} onChange={(event) => setRuns(Number(event.target.value))}>
            <option value={1000}>1,000</option>
            <option value={10000}>10,000</option>
            <option value={100000}>100,000</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm text-[#8A9BB4]">
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
        <p className={`ls-mono mt-4 text-5xl ${improved ? "text-[#10B981]" : "text-[#EF4444]"}`} data-testid="relative-reduction">
          {formatRel(reduction)}
        </p>
        <p className="mt-1 text-sm text-[#8A9BB4]">
          {improved ? "modeled reduction in pass-through" : "modeled increase in pass-through"}
          {dirty ? " · baseline includes unsaved edits" : ""}
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <article className="ls-card p-4">
          <h2 className="text-base font-semibold">{result.config_a_name}</h2>
          <p className="ls-mono mt-2 text-3xl text-[#EF4444]">
            {formatPct(result.result_a.aggregate.closed_form)}
          </p>
          <p className="text-sm text-[#8A9BB4]">modeled pass-through</p>
        </article>
        <article className="ls-card p-4">
          <h2 className="text-base font-semibold">{result.config_b_name}</h2>
          <p className="ls-mono mt-2 text-3xl text-[#10B981]">
            {formatPct(result.result_b.aggregate.closed_form)}
          </p>
          <p className="text-sm text-[#8A9BB4]">modeled pass-through</p>
        </article>
      </div>

      <section className="ls-card p-4">
        <h2 className="text-base font-semibold">What changed</h2>
        {result.changes.length === 0 ? (
          <p className="mt-2 text-sm" role="status">
            The two configurations match.
          </p>
        ) : (
          <ul className="mt-3 grid gap-2 text-sm">
            {result.changes.map((change) => (
              <li key={change.path} className="ls-mono text-[#E6EDF7]">
                {change.path}: {String(change.before)} → {String(change.after)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="ls-card overflow-x-auto p-4">
        <h2 className="text-base font-semibold">Stops by layer</h2>
        <table className="mt-3 w-full min-w-[32rem] text-left text-sm">
          <thead className="text-[#8A9BB4]">
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
                <tr key={layer} className="border-t border-[#24324A]">
                  <th className="py-2 font-normal">{LAYER_LABEL[layer]}</th>
                  <td className="ls-mono">{formatCount(left?.stopped ?? 0)}</td>
                  <td className="ls-mono">{formatCount(right?.stopped ?? 0)}</td>
                  <td className={`ls-mono ${delta >= 0 ? "text-[#10B981]" : "text-[#EF4444]"}`}>
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
        <p className="mt-1 text-sm text-[#8A9BB4]">Sorted by the largest modeled improvement</p>
        <table className="mt-3 w-full min-w-[40rem] text-left text-sm">
          <thead className="text-[#8A9BB4]">
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
              const email = emails.find((item) => item.email_id === row.email_id);
              return (
                <tr key={row.email_id} className="border-t border-[#24324A]">
                  <th className="py-2 font-normal">{subjects.get(row.email_id) ?? row.email_id}</th>
                  <td>{email ? VECTOR_LABEL[email.attack_vector] : ""}</td>
                  <td className="ls-mono">{formatPct(row.pass_rate_a)}</td>
                  <td className="ls-mono">{formatPct(row.pass_rate_b)}</td>
                  <td className="ls-mono text-[#10B981]">{formatPct(row.absolute_reduction)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <p className="text-xs text-[#8A9BB4]" role="status">
        {preview.source === "api"
          ? `Comparison from engine ${result.result_a.engine_version}.`
          : "Closed-form comparison. The simulation API replaces it when a run is returned."}
        {preview.loading ? " Checking the simulation API." : ""}
      </p>
    </div>
  );
}
