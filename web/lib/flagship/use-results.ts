"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  fetchComparison,
  fetchRecommendations,
  fetchSimulation,
} from "@/lib/flagship/api";
import { compare, recommend, simulate } from "@/lib/flagship/model";
import type {
  ComparisonResult,
  LayerConfig,
  RecommendationSet,
  SimEmail,
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
  emails: readonly SimEmail[],
  runs: number,
  seed: number,
): { result: SimulationResult; source: "preview" | "api"; loading: boolean } {
  const local = useMemo(
    () => simulate(emails, config, runs, seed),
    [emails, config, runs, seed],
  );
  const requestKey = useMemo(
    () => JSON.stringify({ config, emailIds: emails.map((email) => email.email_id), runs, seed }),
    [config, emails, runs, seed],
  );
  const debouncedKey = useDebounced(requestKey, 150);
  const query = useQuery({
    queryKey: ["flagship-simulation", debouncedKey],
    queryFn: () => {
      const parsed = JSON.parse(debouncedKey) as {
        config: LayerConfig;
        emailIds: string[];
        runs: number;
        seed: number;
      };
      return fetchSimulation({ ...parsed, persist: false });
    },
  });
  const remote = debouncedKey === requestKey ? query.data ?? null : null;
  return {
    result: remote ?? local,
    source: remote ? "api" : "preview",
    loading: query.isFetching,
  };
}

export function useComparisonPreview(
  configA: LayerConfig,
  configB: LayerConfig,
  emails: readonly SimEmail[],
  runs: number,
  seed: number,
): { result: ComparisonResult; source: "preview" | "api"; loading: boolean } {
  const local = useMemo(
    () => compare(emails, configA, configB, runs, seed),
    [emails, configA, configB, runs, seed],
  );
  const requestKey = useMemo(
    () =>
      JSON.stringify({
        configA,
        configB,
        emailIds: emails.map((email) => email.email_id),
        runs,
        seed,
      }),
    [configA, configB, emails, runs, seed],
  );
  const debouncedKey = useDebounced(requestKey, 150);
  const query = useQuery({
    queryKey: ["flagship-comparison", debouncedKey],
    queryFn: () =>
      fetchComparison(
        JSON.parse(debouncedKey) as {
          configA: LayerConfig;
          configB: LayerConfig;
          emailIds: string[];
          runs: number;
          seed: number;
        },
      ),
  });
  const remote = debouncedKey === requestKey ? query.data ?? null : null;
  return {
    result: remote ?? local,
    source: remote ? "api" : "preview",
    loading: query.isFetching,
  };
}

export function useRecommendationPreview(
  config: LayerConfig,
  emails: readonly SimEmail[],
): { result: RecommendationSet; source: "preview" | "api"; loading: boolean } {
  const local = useMemo(() => recommend(emails, config), [emails, config]);
  const requestKey = useMemo(
    () => JSON.stringify({ config, emailIds: emails.map((email) => email.email_id) }),
    [config, emails],
  );
  const debouncedKey = useDebounced(requestKey, 150);
  const query = useQuery({
    queryKey: ["flagship-recommendations", debouncedKey],
    queryFn: () =>
      fetchRecommendations(
        JSON.parse(debouncedKey) as { config: LayerConfig; emailIds: string[] },
      ),
  });
  const remote = debouncedKey === requestKey ? query.data ?? null : null;
  return {
    result: remote ?? local,
    source: remote ? "api" : "preview",
    loading: query.isFetching,
  };
}
