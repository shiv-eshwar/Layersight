"use client";

import { useMemo, useState } from "react";

import {
  AttackFlow,
  FunnelChart,
  OutcomeDonut,
  StopBars,
  TornadoChart,
} from "@/components/flagship/charts";
import { selectEmails, WORKSPACE_EMAILS } from "@/lib/flagship/fixtures";
import { formatPct } from "@/lib/flagship/format";
import { useFlagship } from "@/lib/flagship/store";
import { LAYER_LABEL, VECTOR_LABEL, type Recommendation } from "@/lib/flagship/types";
import { useRecommendationPreview, useSimulationPreview } from "@/lib/flagship/use-results";

export function SimulatorScreen() {
  const draft = useFlagship((state) => state.draft);
  const [scope, setScope] = useState("email_illustrative");
  const [runs, setRuns] = useState(10_000);
  const [seed, setSeed] = useState(42);
  const emails = useMemo(() => selectEmails(scope), [scope]);
  const subjects = useMemo(
    () => new Map(WORKSPACE_EMAILS.map((email) => [email.email_id, email.subject])),
    [],
  );
  const preview = useSimulationPreview(draft, emails, runs, seed);
  const advice = useRecommendationPreview(draft, emails);

  return (
    <div data-testid="simulator-screen" className="grid gap-4">
      <p className="text-sm text-[#8A9BB4]">
        {formatPct(preview.result.aggregate.closed_form)} of these attacks are modeled to pass every
        layer that applies. Counts are the expected stops in {runs.toLocaleString("en-US")} runs.
      </p>

      <section className="ls-card flex flex-wrap items-end gap-3 p-4">
        <label className="grid gap-1 text-sm text-[#8A9BB4]">
          Configuration
          <input type="text" readOnly value={draft.name} aria-label="Configuration" />
        </label>
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
          <select
            aria-label="Runs"
            value={runs}
            onChange={(event) => setRuns(Number(event.target.value))}
          >
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
        <p className="text-sm text-[#8A9BB4]" role="status">
          {preview.source === "api"
            ? `Monte Carlo from engine ${preview.result.engine_version}, seed ${preview.result.seed}.`
            : `Closed form for seed ${seed}. Monte Carlo counts appear when the API returns this seed.`}
          {preview.loading ? " Checking the simulation API." : ""}
        </p>
      </section>

      {emails.length === 0 ? (
        <p className="ls-card p-4 text-sm" role="status">
          This scope has no phishing emails to simulate.
        </p>
      ) : (
        <>
          <AttackFlow result={preview.result} />
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <FunnelChart result={preview.result} />
            <OutcomeDonut result={preview.result} source={preview.source} />
          </div>
          <StopBars result={preview.result} mode="vector" subjects={subjects} />
          <StopBars result={preview.result} mode="email" subjects={subjects} />
          <div className="grid gap-4 lg:grid-cols-2">
            <TornadoChart rows={advice.result.sensitivity} />
            <section className="ls-card p-4" data-testid="recommendations">
              <h2 className="text-base font-semibold">What to improve next</h2>
              <p className="mt-1 text-sm text-[#8A9BB4]">
                Ranked by how much each change lowers modeled pass-through on this scope.
              </p>
              {advice.result.recommendations.length === 0 ? (
                <p className="mt-4 text-sm" role="status">
                  None of the catalogued changes lower pass-through for this scope.
                </p>
              ) : (
                <ol className="mt-4 grid gap-3">
                  {advice.result.recommendations.map((item: Recommendation, index) => (
                    <li key={item.id} className="border-t border-[#24324A] pt-3">
                      <p className="text-sm font-semibold">
                        {index + 1}. {item.title}
                      </p>
                      <p className="mt-1 text-sm text-[#8A9BB4]">{item.detail}</p>
                      <p className="ls-mono mt-1 text-sm text-[#10B981]">
                        {formatPct(item.absolute_reduction)} lower · {LAYER_LABEL[item.layer]}
                      </p>
                      <p className="text-xs text-[#8A9BB4]">
                        Helps {item.vectors_helped.map((vector) => VECTOR_LABEL[vector]).join(", ")}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
