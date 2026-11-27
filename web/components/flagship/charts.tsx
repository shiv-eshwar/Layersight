"use client";

import { useEffect, useMemo, useState } from "react";

import { formatCount, formatPct } from "@/lib/flagship/format";
import { sampleParticles } from "@/lib/flagship/model";
import {
  LAYER_COLOR,
  LAYER_LABEL,
  LAYERS,
  PASSED_COLOR,
  VECTOR_LABEL,
  type LayerName,
  type SensitivityRow,
  type SimulationResult,
} from "@/lib/flagship/types";

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);
  return reduced;
}

function passedCount(result: SimulationResult): number {
  const last = result.aggregate.layers[result.aggregate.layers.length - 1];
  if (!last) return 0;
  return Math.max(0, last.entered - last.stopped);
}

export function FunnelChart({ result }: { result: SimulationResult }) {
  const runs = Math.max(result.runs, 1);
  return (
    <figure className="ls-card p-4" data-testid="funnel">
      <figcaption className="text-base font-semibold">Where attacks stop</figcaption>
      <p className="mt-1 text-sm text-[#8A9BB4]">Modeled estimate · counts for {formatCount(runs)} runs</p>
      <ol className="mt-4 grid gap-3">
        {result.aggregate.layers.map((layer) => {
          const remaining = Math.max(0, layer.entered - layer.stopped);
          const width = Math.max(4, (layer.entered / runs) * 100);
          return (
            <li key={layer.layer}>
              <div className="mb-1 text-sm">
                <p>{LAYER_LABEL[layer.layer]}</p>
                <p className="ls-mono text-[#8A9BB4]">
                  {formatCount(layer.stopped)} stopped · {formatCount(remaining)} still in
                </p>
              </div>
              <div className="h-2.5 rounded-full bg-[#0B1120]">
                <div
                  className="h-2.5 rounded-full"
                  style={{ width: `${width}%`, background: LAYER_COLOR[layer.layer] }}
                />
              </div>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-sm">
        <span className="text-[#EF4444]">Passed every layer </span>
        <span className="ls-mono">{formatCount(passedCount(result))}</span>
      </p>
    </figure>
  );
}

export function OutcomeDonut({
  result,
  source,
}: {
  result: SimulationResult;
  source: "preview" | "api";
}) {
  const passRate = source === "api" ? result.aggregate.pass_rate : result.aggregate.closed_form;
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const passedLength = circumference * passRate;
  const [low, high] = result.aggregate.ci95;
  return (
    <figure className="ls-card flex flex-col items-center p-4" data-testid="outcome-donut">
      <figcaption className="self-start text-base font-semibold">Pass-through</figcaption>
      <p className="self-start text-sm text-[#8A9BB4]">Modeled estimate</p>
      <svg viewBox="0 0 140 140" className="mt-2 h-40 w-40" role="img" aria-label={`Pass-through ${formatPct(passRate)}`}>
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#10B981" strokeWidth="14" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="#EF4444"
          strokeWidth="14"
          strokeDasharray={`${passedLength} ${circumference - passedLength}`}
          strokeLinecap="butt"
          transform="rotate(-90 70 70)"
        />
        <text x="70" y="66" textAnchor="middle" fill="#EF4444" fontSize="16" fontFamily="ui-monospace, monospace">
          {formatPct(passRate)}
        </text>
        <text x="70" y="84" textAnchor="middle" fill="#8A9BB4" fontSize="9">
          passed
        </text>
      </svg>
      <dl className="mt-2 grid w-full gap-1 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-[#10B981]">Blocked</dt>
          <dd className="ls-mono">{formatPct(1 - passRate)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-[#EF4444]">Passed</dt>
          <dd className="ls-mono" data-testid="pass-through">
            {formatPct(result.aggregate.pass_rate)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-[#8A9BB4]">Closed form</dt>
          <dd className="ls-mono" data-testid="closed-form">
            {formatPct(result.aggregate.closed_form)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-[#8A9BB4]">95% interval</dt>
          <dd className="ls-mono">
            {formatPct(low)}–{formatPct(high)}
          </dd>
        </div>
      </dl>
    </figure>
  );
}

export function AttackFlow({ result }: { result: SimulationResult }) {
  const reduced = useReducedMotion();
  const stopped = result.aggregate.layers.map((layer) => layer.stopped);
  const passed = passedCount(result);
  const particles = useMemo(() => sampleParticles(stopped, passed, 220), [stopped, passed]);
  const stops = ["8%", "26%", "44%", "62%", "80%"];
  return (
    <figure className="ls-card p-4" data-testid="attack-flow">
      <figcaption className="text-base font-semibold">Attack flow</figcaption>
      <p className="mt-1 text-sm text-[#8A9BB4]">
        {reduced
          ? "Motion is off. The counts below are the modeled stops."
          : "Each dot is a share of the modeled stops. Green drops out where a layer stops the attack. Red reaches the end."}
      </p>
      <div className="attack-stage mt-4">
        <div className="absolute top-[36%] right-0 left-0 h-px bg-[#24324A]" />
        {LAYERS.map((layer, index) => (
          <div
            key={layer}
            className="absolute top-2 w-24 -translate-x-1/2 text-center"
            style={{ left: stops[index] }}
          >
            <p className="text-xs text-[#8A9BB4]">{index + 1}</p>
            <p className="text-sm">{LAYER_LABEL[layer]}</p>
            <p className="ls-mono text-xs text-[#10B981]">{formatCount(stopped[index] ?? 0)} stop</p>
          </div>
        ))}
        <div className="absolute top-2 right-0 text-right">
          <p className="text-xs text-[#8A9BB4]">Out</p>
          <p className="text-sm text-[#EF4444]">Passed</p>
          <p className="ls-mono text-xs text-[#EF4444]">{formatCount(passed)}</p>
        </div>
        {reduced
          ? null
          : particles.map((particle) => (
              <span
                key={particle.id}
                className="attack-particle"
                data-passed={particle.stopAt >= LAYERS.length ? "true" : "false"}
                style={{
                  ["--stop" as string]: stops[particle.stopAt] ?? "96%",
                  animationDelay: `${(particle.id % 36) * 70}ms`,
                }}
              />
            ))}
      </div>
    </figure>
  );
}

function stackRows(
  result: SimulationResult,
  mode: "vector" | "email",
  subjects: Map<string, string>,
): { key: string; label: string; shares: { color: string; value: number }[] }[] {
  const groups = new Map<string, SimulationResult["per_email"]>();
  for (const email of result.per_email) {
    const key = mode === "vector" ? email.attack_vector : email.email_id;
    const list = groups.get(key) ?? [];
    list.push(email);
    groups.set(key, list);
  }
  return [...groups.entries()].map(([key, emails]) => {
    const runs = Math.max(result.runs, 1);
    const shares = LAYERS.map((layer) => {
      const stopped =
        emails.reduce((sum, email) => {
          const row = email.layers.find((item) => item.layer === layer);
          return sum + (row?.stopped ?? 0);
        }, 0) / emails.length;
      return { color: LAYER_COLOR[layer], value: stopped / runs };
    });
    const passed =
      emails.reduce((sum, email) => sum + email.passed, 0) / emails.length / runs;
    shares.push({ color: PASSED_COLOR, value: passed });
    const label =
      mode === "vector"
        ? VECTOR_LABEL[key as keyof typeof VECTOR_LABEL] ?? key
        : subjects.get(key) ?? key;
    return { key, label, shares };
  });
}

export function StopBars({
  result,
  mode,
  subjects,
}: {
  result: SimulationResult;
  mode: "vector" | "email";
  subjects: Map<string, string>;
}) {
  const rows = stackRows(result, mode, subjects);
  const title = mode === "vector" ? "By attack vector" : "By email";
  return (
    <figure className="ls-card p-4" data-testid={`stop-bars-${mode}`}>
      <figcaption className="text-base font-semibold">{title}</figcaption>
      <p className="mt-1 text-sm text-[#8A9BB4]">Share of runs stopped by each layer, then passed</p>
      <ul className="mt-4 grid gap-3">
        {rows.map((row) => (
          <li key={row.key}>
            <p className="mb-1 text-sm">{row.label}</p>
            <div className="flex h-3 overflow-hidden rounded-full bg-[#0B1120]">
              {row.shares.map((share, index) => (
                <span
                  key={`${row.key}-${index}`}
                  style={{ width: `${Math.max(0, share.value) * 100}%`, background: share.color }}
                />
              ))}
            </div>
          </li>
        ))}
      </ul>
      <ul className="mt-3 flex flex-wrap gap-3 text-xs text-[#8A9BB4]">
        {LAYERS.map((layer) => (
          <li key={layer} className="flex items-center gap-1">
            <span className="inline-block h-2 w-2" style={{ background: LAYER_COLOR[layer] }} />
            {LAYER_LABEL[layer]}
          </li>
        ))}
        <li className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 bg-[#EF4444]" />
          Passed
        </li>
      </ul>
    </figure>
  );
}

export function TornadoChart({ rows }: { rows: SensitivityRow[] }) {
  const swing = (row: SensitivityRow) =>
    Math.max(Math.abs(row.decreased - row.baseline), Math.abs(row.increased - row.baseline));
  const scale = Math.max(0.01, ...rows.map(swing));
  return (
    <figure className="ls-card p-4" data-testid="tornado">
      <figcaption className="text-base font-semibold">Sensitivity</figcaption>
      <p className="mt-1 text-sm text-[#8A9BB4]">
        Modeled estimate · each applicable layer moved 10 points. Red is a higher pass-through.
      </p>
      <ul className="mt-4 grid gap-3">
        {rows.map((row) => {
          const worse = Math.max(0, row.decreased - row.baseline);
          const better = Math.max(0, row.baseline - row.increased);
          return (
            <li key={row.layer} className="grid grid-cols-[9rem_1fr] items-center gap-3 text-sm">
              <span>{LAYER_LABEL[row.layer as LayerName]}</span>
              <div className="relative h-3 bg-[#0B1120]">
                <span className="absolute top-0 left-1/2 h-3 w-px bg-[#8A9BB4]" />
                <span
                  className="absolute top-0 h-3 bg-[#EF4444]"
                  style={{ left: "50%", width: `${(worse / scale) * 50}%` }}
                />
                <span
                  className="absolute top-0 h-3 bg-[#10B981]"
                  style={{ right: "50%", width: `${(better / scale) * 50}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-[#8A9BB4]">
        {`Center is the current pass-through, ${rows[0] ? formatPct(rows[0].baseline) : ""}. Green means the layer was strengthened.`}
      </p>
    </figure>
  );
}

export function ApplicabilityMatrix({
  credentialSegmentation,
}: {
  credentialSegmentation: boolean;
}) {
  const vectors = [
    ["Malware attachment", [true, true, true, true, true]],
    ["Malware link", [true, true, true, true, true]],
    ["Credential harvesting", [true, true, false, false, credentialSegmentation]],
    ["Payment fraud", [true, true, false, false, false]],
  ] as const;
  return (
    <figure className="ls-card overflow-x-auto p-4" data-testid="applicability-matrix">
      <figcaption className="text-base font-semibold">What each layer can see</figcaption>
      <table className="mt-3 w-full min-w-[32rem] text-left text-sm">
        <thead className="text-[#8A9BB4]">
          <tr>
            <th className="py-1 pr-3 font-medium">Attack</th>
            {LAYERS.map((layer) => (
              <th key={layer} className="px-2 py-1 font-medium">
                {LAYER_LABEL[layer].replace(" training", "").replace(" control", "")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {vectors.map(([label, flags]) => (
            <tr key={label} className="border-t border-[#24324A]">
              <th className="py-2 pr-3 font-normal">{label}</th>
              {flags.map((applies, index) => (
                <td key={`${label}-${index}`} className="px-2 py-2">
                  {applies ? (
                    <span className="text-[#10B981]">Applies</span>
                  ) : (
                    <span className="text-[#8A9BB4]">Not applicable</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
