import type { ComparisonResult, LayerConfig, RecommendationSet, SimulationResult } from "@/lib/flagship/types";

export function apiBaseUrl(): string {
  if (typeof window !== "undefined") return "";
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isSimulationResult(value: unknown): value is SimulationResult {
  if (!isRecord(value) || !isRecord(value.aggregate)) return false;
  return typeof value.aggregate.closed_form === "number" && Array.isArray(value.per_email);
}

function isComparisonResult(value: unknown): value is ComparisonResult {
  if (!isRecord(value)) return false;
  return (
    typeof value.narrative === "string" &&
    Array.isArray(value.changes) &&
    isSimulationResult(value.result_a) &&
    isSimulationResult(value.result_b)
  );
}

function isRecommendationSet(value: unknown): value is RecommendationSet {
  if (!isRecord(value)) return false;
  return Array.isArray(value.recommendations) && Array.isArray(value.sensitivity);
}

async function postJson(path: string, body: unknown): Promise<unknown> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) {
    throw new Error(`Simulation request failed (${response.status})`);
  }
  return (await response.json()) as unknown;
}

export interface SimulationRequest {
  datasetId: string;
  config: LayerConfig;
  runs: number;
  seed: number;
  persist: boolean;
  closedForm?: boolean;
}

export async function fetchSimulation(request: SimulationRequest): Promise<SimulationResult> {
  const body = await postJson("/api/v1/simulations", {
    dataset_id: request.datasetId,
    config: request.config,
    runs: request.runs,
    seed: request.seed,
    persist: request.persist,
    closed_form: request.closedForm ?? false,
  });
  if (!isSimulationResult(body)) {
    throw new Error("The simulation response did not match the engine.");
  }
  return body;
}

export async function fetchComparison(input: {
  datasetId: string;
  configA: LayerConfig;
  configB: LayerConfig;
  runs: number;
  seed: number;
}): Promise<ComparisonResult> {
  const body = await postJson("/api/v1/comparisons", {
    dataset_id: input.datasetId,
    config_a: input.configA,
    config_b: input.configB,
    runs: input.runs,
    seed: input.seed,
  });
  if (!isComparisonResult(body)) {
    throw new Error("The comparison response did not match the engine.");
  }
  return body;
}

export async function fetchRecommendations(input: {
  datasetId: string;
  config: LayerConfig;
}): Promise<RecommendationSet> {
  const body = await postJson("/api/v1/recommendations", {
    dataset_id: input.datasetId,
    config: input.config,
  });
  if (!isRecommendationSet(body)) {
    throw new Error("The recommendation response did not match the engine.");
  }
  return body;
}

export async function fetchStoredConfig(configId: string): Promise<LayerConfig> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/configs/${configId}`, {
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error(`Configuration ${configId} is not stored.`);
  const body: unknown = await response.json();
  if (!isRecord(body) || !isRecord(body.config) || typeof body.config.name !== "string") {
    throw new Error("The stored configuration is unreadable.");
  }
  return body.config as unknown as LayerConfig;
}

export async function fetchMeta(): Promise<{ engine_version: string } | null> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/meta`, {
      signal: AbortSignal.timeout(800),
    });
    if (!response.ok) return null;
    const body: unknown = await response.json();
    if (!isRecord(body) || typeof body.engine_version !== "string") return null;
    return { engine_version: body.engine_version };
  } catch {
    return null;
  }
}
