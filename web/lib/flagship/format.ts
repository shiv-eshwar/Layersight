/** Display formatters. Pass-through uses two decimals; relative reduction uses one. */

export function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(2)}%`;
}

export function formatRel(rate: number): string {
  return `${(Math.abs(rate) * 100).toFixed(1)}%`;
}

export function formatCount(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

export function formatPoints(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}
