"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { ConfigSummary, DatasetSummary } from "@/lib/types";

export function WorkspaceControls() {
  const params = useSearchParams();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const dataset = mounted ? (params.get("dataset") ?? "") : "";
  const baseline = mounted ? (params.get("baseline") ?? "") : "";
  const comparison = mounted ? (params.get("comparison") ?? "") : "";
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [configs, setConfigs] = useState<ConfigSummary[]>([]);

  useEffect(() => {
    void api<DatasetSummary[]>("/api/v1/datasets").then(setDatasets).catch(() => setDatasets([]));
    void api<ConfigSummary[]>("/api/v1/configs").then(setConfigs).catch(() => setConfigs([]));
  }, [dataset]);

  function update(next: { dataset?: string; baseline?: string; comparison?: string }) {
    const query = new URLSearchParams(params.toString());
    const values = {
      dataset: next.dataset ?? dataset,
      baseline: next.baseline ?? baseline,
      comparison: next.comparison ?? comparison,
    };
    for (const [key, value] of Object.entries(values)) {
      if (value) query.set(key, value);
      else query.delete(key);
    }
    const text = query.toString();
    router.replace(text ? `${window.location.pathname}?${text}` : window.location.pathname);
  }

  return (
    <>
      <label className="text-xs text-muted-foreground">
        Dataset
        <select
          aria-label="Dataset"
          data-testid="dataset-select"
          className="ml-2 h-8 max-w-48 border border-border bg-background px-2 text-sm text-foreground"
          value={dataset}
          onChange={(event) => update({ dataset: event.target.value })}
        >
          <option value="">None</option>
          {datasets.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} ({item.emails})
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs text-muted-foreground">
        Config pair
        <span className="ml-2 inline-flex items-center gap-1" data-testid="config-pair">
          <select
            aria-label="Baseline configuration"
            className="h-8 max-w-40 border border-border bg-background px-2 text-sm text-foreground"
            value={baseline}
            onChange={(event) => update({ baseline: event.target.value })}
          >
            <option value="">Untrained</option>
            {configs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <span aria-hidden="true">→</span>
          <select
            aria-label="Comparison configuration"
            className="h-8 max-w-40 border border-border bg-background px-2 text-sm text-foreground"
            value={comparison}
            onChange={(event) => update({ comparison: event.target.value })}
          >
            <option value="">Trained</option>
            {configs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </span>
      </label>
    </>
  );
}
