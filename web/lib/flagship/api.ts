import type { ComparisonResult, LayerConfig, RecommendationSet, SimulationResult } from "@/lib/flagship/types";

const ABSENT = "absent";
const READY = "ready";

let simulationApi: "unknown" | typeof READY | typeof ABSENT = "unknown";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export function simulationApiStatus(): "unknown" | "ready" | "absent" {
  return simulationApi;
}

export function resetSimulationApiProbe(): void {
  simulationApi = "unknown";
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
    isSimulationResult(value.result_a) &&
    isSimulationResult(value.result_b)
  );
}

function isRecommendationSet(value: unknown): value is RecommendationSet {
  if (!isRecord(value)) return false;
  return Array.isArray(value.recommendations) && Array.isArray(value.sensitivity);
}

async function postJson(path: string, body: unknown): Promise<unknown | null> {
  if (simulationApi === ABSENT) return null;
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(800),
    });
    if (response.status === 404 || response.status === 405) {
      simulationApi = ABSENT;
      return null;
    }
    if (!response.ok) return null;
    simulationApi = READY;
    return (await response.json()) as unknown;
  } catch {
    simulationApi = ABSENT;
    return null;
  }
}

export interface SimulationRequest {
  config: LayerConfig;
  emailIds: string[];
  runs: number;
  seed: number;
  persist: boolean;
}

export async function fetchSimulation(request: SimulationRequest): Promise<SimulationResult | null> {
  const body = await postJson("/api/v1/simulations", {
    config: request.config,
    email_ids: request.emailIds,
    runs: request.runs,
    seed: request.seed,
    persist: request.persist,
  });
  return isSimulationResult(body) ? body : null;
}

export async function fetchComparison(input: {
  configA: LayerConfig;
  configB: LayerConfig;
  emailIds: string[];
  runs: number;
  seed: number;
}): Promise<ComparisonResult | null> {
  const body = await postJson("/api/v1/comparisons", {
    config_a: input.configA,
    config_b: input.configB,
    email_ids: input.emailIds,
    runs: input.runs,
    seed: input.seed,
  });
  return isComparisonResult(body) ? body : null;
}

export async function fetchRecommendations(input: {
  config: LayerConfig;
  emailIds: string[];
}): Promise<RecommendationSet | null> {
  const body = await postJson("/api/v1/recommendations", {
    config: input.config,
    email_ids: input.emailIds,
  });
  return isRecommendationSet(body) ? body : null;
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
