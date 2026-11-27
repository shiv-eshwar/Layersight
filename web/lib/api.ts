export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as { detail?: string; title?: string } | null;
    throw new ApiError(problem?.detail || problem?.title || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function selectionHref(path: string, params: { dataset?: string | null; baseline?: string | null; comparison?: string | null }): string {
  const query = new URLSearchParams();
  if (params.dataset) query.set("dataset", params.dataset);
  if (params.baseline) query.set("baseline", params.baseline);
  if (params.comparison) query.set("comparison", params.comparison);
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}
