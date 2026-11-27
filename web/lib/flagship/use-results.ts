"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  fetchComparison,
  fetchRecommendations,
  fetchSimulation,
} from "@/lib/flagship/api";
import type {
  ComparisonResult,
  LayerConfig,
  RecommendationSet,
  SimulationResult,
} from "@/lib/flagship/types";

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export function useSimulationPreview(
  config: LayerConfig,
  datasetId: string | null,
  runs: number,
  seed: number,
  closedForm = false,
): { result: SimulationResult | null; loading: boolean; error: string | null } {
  const requestKey = useMemo(
    () => JSON.stringify({ config, runs, seed, closedForm }),
    [config, runs, seed, closedForm],
  );
  const debouncedKey = useDebounced(requestKey, closedForm ? 40 : 120);
  const query = useQuery({
    queryKey: ["flagship-simulation", datasetId, debouncedKey],
    enabled: Boolean(datasetId),
    placeholderData: keepPreviousData,
    queryFn: () => {
      const parsed = JSON.parse(debouncedKey) as {
        config: LayerConfig;
        runs: number;
        seed: number;
        closedForm: boolean;
      };
      return fetchSimulation({
        datasetId: datasetId ?? "",
        config: parsed.config,
        runs: parsed.runs,
        seed: parsed.seed,
        persist: false,
        closedForm: parsed.closedForm,
      });
    },
  });
  return {
    result: datasetId ? query.data ?? null : null,
    loading: Boolean(datasetId) && (query.isFetching || query.data == null),
    error: query.error instanceof Error ? query.error.message : null,
  };
}

export function useComparisonPreview(
  configA: LayerConfig,
  configB: LayerConfig,
  datasetId: string | null,
  runs: number,
  seed: number,
): { result: ComparisonResult | null; loading: boolean; error: string | null } {
  const requestKey = useMemo(
    () => JSON.stringify({ configA, configB, runs, seed }),
    [configA, configB, runs, seed],
  );
  const debouncedKey = useDebounced(requestKey, 120);
  const query = useQuery({
    queryKey: ["flagship-comparison", datasetId, debouncedKey],
    enabled: Boolean(datasetId),
    placeholderData: keepPreviousData,
    queryFn: () => {
      const parsed = JSON.parse(debouncedKey) as {
        configA: LayerConfig;
        configB: LayerConfig;
        runs: number;
        seed: number;
      };
      return fetchComparison({
        datasetId: datasetId ?? "",
        configA: parsed.configA,
        configB: parsed.configB,
        runs: parsed.runs,
        seed: parsed.seed,
      });
    },
  });
  return {
    result: datasetId ? query.data ?? null : null,
    loading: Boolean(datasetId) && (query.isFetching || query.data == null),
    error: query.error instanceof Error ? query.error.message : null,
  };
}

export function useRecommendationPreview(
  config: LayerConfig,
  datasetId: string | null,
): { result: RecommendationSet | null; loading: boolean; error: string | null } {
  const requestKey = useMemo(() => JSON.stringify({ config }), [config]);
  const debouncedKey = useDebounced(requestKey, 120);
  const query = useQuery({
    queryKey: ["flagship-recommendations", datasetId, debouncedKey],
    enabled: Boolean(datasetId),
    placeholderData: keepPreviousData,
    queryFn: () => {
      const parsed = JSON.parse(debouncedKey) as { config: LayerConfig };
      return fetchRecommendations({ datasetId: datasetId ?? "", config: parsed.config });
    },
  });
  return {
    result: datasetId ? query.data ?? null : null,
    loading: Boolean(datasetId) && (query.isFetching || query.data == null),
    error: query.error instanceof Error ? query.error.message : null,
  };
}
