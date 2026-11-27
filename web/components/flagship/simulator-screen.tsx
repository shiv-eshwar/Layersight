"use client";

import { useMemo, useState } from "react";

import {
  AttackFlow,
  FunnelChart,
  OutcomeDonut,
  StopBars,
  TornadoChart,
} from "@/components/flagship/charts";
import { EmptyState } from "@/components/shell/empty-state";
import { formatPct } from "@/lib/flagship/format";
import { useFlagship } from "@/lib/flagship/store";
import { useWorkspaceDataset } from "@/lib/use-dataset";
import { LAYER_LABEL, VECTOR_LABEL, type Recommendation, type SimulationResult } from "@/lib/flagship/types";
import { useRecommendationPreview, useSimulationPreview } from "@/lib/flagship/use-results";

function focusResult(result: SimulationResult, scope: string): SimulationResult {
  if (scope === "all") return result;
  const email = result.per_email.find((item) => item.email_id === scope || item.id === scope);
  if (!email) return result;
  return {
    ...result,
    per_email: [email],
    aggregate: {
      ...result.aggregate,
      email_count: 1,
      pass_rate: email.pass_rate,
      blocked_rate: 1 - email.pass_rate,
      closed_form: email.closed_form,
      ci95: email.ci95,
      layers: email.layers.map((layer) => ({
        layer: layer.layer,
        entered: layer.entered,
        stopped: layer.stopped,
        applicable_emails: layer.applicable ? 1 : 0,
      })),
    },
  };
}

export function SimulatorScreen() {
  const datasetId = useWorkspaceDataset();
  const draft = useFlagship((state) => state.draft);
  const [scope, setScope] = useState("all");
  const [runs, setRuns] = useState(10_000);
  const [seed, setSeed] = useState(42);
  const preview = useSimulationPreview(draft, datasetId, runs, seed);
  const advice = useRecommendationPreview(draft, datasetId);
  const result = useMemo(
    () => (preview.result ? focusResult(preview.result, scope) : null),
    [preview.result, scope],
  );
  const subjects = useMemo(() => {
    const found = new Map<string, string>();
    for (const email of preview.result?.per_email ?? []) {
      const subject = email.subject || email.filename || email.email_id;
      found.set(email.email_id, subject);
      if (email.id) found.set(email.id, subject);
    }
    return found;
  }, [preview.result]);

  if (!datasetId) {
    return (
      <EmptyState title="No dataset selected">
        Load the 20-email test set in Triage. The simulator runs those predicted phishing emails
        through the engine.
      </EmptyState>
    );
  }

  return (
    <div data-testid="simulator-screen" className="grid gap-4">
      <p className="text-sm text-[#949aab]" data-testid="modeled-estimate">
        {result
          ? `${formatPct(result.aggregate.closed_form)} of these attacks are modeled to pass every layer that applies. Counts are from ${runs.toLocaleString("en-US")} runs.`
          : "Running the engine."}
      </p>

      <section className="ls-card flex flex-wrap items-end gap-3 p-4">
        <label className="grid gap-1 text-sm text-[#949aab]">
          Configuration
          <input type="text" readOnly value={draft.name} aria-label="Configuration" />
        </label>
        <label className="grid gap-1 text-sm text-[#949aab]">
          Scope
          <select aria-label="Scope" value={scope} onChange={(event) => setScope(event.target.value)}>
            <option value="all">All predicted phishing</option>
            {(preview.result?.per_email ?? []).map((email) => (
              <option key={email.id || email.email_id} value={email.id || email.email_id}>
                {email.subject || email.filename || email.email_id}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm text-[#949aab]">
          Runs
          <select
            aria-label="Runs"
            data-testid="sim-runs"
            data-value={runs}
            value={runs}
            onChange={(event) => setRuns(Number(event.target.value))}
          >
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
            data-testid="sim-seed"
            data-value={seed}
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value) || 0)}
          />
        </label>
        <p className="text-sm text-[#949aab]" role="status">
          {result
            ? `Monte Carlo from engine ${result.engine_version}, seed ${result.seed}.`
            : "Waiting for the engine."}
          {preview.loading ? " Running." : ""}
          {preview.error ? ` ${preview.error}` : ""}
        </p>
      </section>

      {!result ? (
        <p className="ls-card p-4 text-sm" role="status">
          {preview.error ?? "Simulating the predicted phishing in this dataset."}
        </p>
      ) : (
        <>
          <AttackFlow result={result} />
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <FunnelChart result={result} />
            <OutcomeDonut result={result} source="api" />
          </div>
          <StopBars result={result} mode="vector" subjects={subjects} />
          <StopBars result={result} mode="email" subjects={subjects} />
          <div className="grid gap-4 lg:grid-cols-2">
            <TornadoChart rows={advice.result?.sensitivity ?? []} />
            <section className="ls-card p-4" data-testid="recommendations">
              <h2 className="text-base font-semibold">What to improve next</h2>
              <p className="mt-1 text-sm text-[#949aab]">
                Ranked by how much each change lowers modeled pass-through on this scope.
              </p>
              {(advice.result?.recommendations.length ?? 0) === 0 ? (
                <p className="mt-4 text-sm" role="status">
                  None of the catalogued changes lower pass-through for this scope.
                </p>
              ) : (
                <ol className="mt-4 grid gap-3">
                  {(advice.result?.recommendations ?? []).map((item: Recommendation, index) => (
                    <li key={item.id} className="border-t border-[#2a2e3c] pt-3">
                      <p className="text-sm font-semibold">
                        {index + 1}. {item.title}
                      </p>
                      <p className="mt-1 text-sm text-[#949aab]">{item.detail}</p>
                      <p className="ls-mono mt-1 text-sm text-[#3ddc97]">
                        {formatPct(item.absolute_reduction)} lower · {LAYER_LABEL[item.layer]}
                      </p>
                      <p className="text-xs text-[#949aab]">
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
