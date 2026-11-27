import type { Band } from "@/lib/types";
import { formatScore } from "@/lib/format";

const bandClass: Record<Band, string> = {
  critical: "text-threat",
  high: "text-threat",
  suspicious: "text-warning",
  low: "text-protected",
};

export function RiskScore({ score, band }: { score: number; band: Band }) {
  const width = `${Math.max(4, Math.round(score * 100))}%`;
  const bar = band === "low" ? "bg-protected" : band === "suspicious" ? "bg-warning" : "bg-threat";
  return (
    <div>
      <p className="text-sm text-muted-foreground">Risk score</p>
      <p className={`mt-1 font-mono text-4xl tabular-nums ${bandClass[band]}`}>{formatScore(score)}</p>
      <div className="mt-3 h-1 w-28 bg-line" aria-hidden="true">
        <div className={`h-1 ${bar}`} style={{ width }} />
      </div>
    </div>
  );
}

export function BandBadge({ band }: { band: Band }) {
  const label = band === "low" ? "Low" : band === "suspicious" ? "Suspicious" : band === "high" ? "High" : "Critical";
  return <span className={`text-sm font-medium ${bandClass[band]}`}>{label}</span>;
}

export function VerdictText({ label }: { label: "phishing" | "genuine" }) {
  return (
    <span className={label === "phishing" ? "text-threat" : "text-protected"}>
      {label === "phishing" ? "Phishing" : "Genuine"}
    </span>
  );
}

export function AuthBadge({ name, value }: { name: string; value: string }) {
  const tone = value === "pass" ? "text-protected" : value === "none" ? "text-muted-foreground" : "text-threat";
  return (
    <span className="border border-border bg-background px-3 py-2">
      <span className="block text-xs text-muted-foreground">{name}</span>
      <span className={`font-mono text-sm ${tone}`}>{value}</span>
    </span>
  );
}

export function DomainDiff({
  diff,
  closest,
}: {
  diff: { char: string; changed: boolean }[];
  closest: string | null;
}) {
  if (diff.length === 0) return null;
  return (
    <p className="font-mono text-[13px]">
      {diff.map((item, index) => (
        <span key={`${item.char}-${index}`} className={item.changed ? "text-threat underline decoration-threat" : undefined}>
          {item.char}
        </span>
      ))}
      {closest ? <span className="text-muted-foreground"> imitates {closest}</span> : null}
    </p>
  );
}

export function EvidenceList({
  items,
}: {
  items: { rule_id: string; title: string; detail: string; contribution: number; share: number; category: string }[];
}) {
  return (
    <ol className="flex flex-col">
      {items.map((item) => (
        <li key={`${item.rule_id}-${item.detail}`} className="border-t border-border py-4">
          <div className="flex items-baseline justify-between gap-4">
            <p className="font-medium">
              {item.title} <span className="font-mono text-xs text-muted-foreground">{item.rule_id}</span>
            </p>
            <p className={`font-mono text-sm tabular-nums ${item.contribution >= 0 ? "text-threat" : "text-protected"}`}>
              {item.contribution > 0 ? "+" : ""}
              {item.contribution.toFixed(2)}
            </p>
          </div>
          <p className="mt-1 max-w-xl text-sm leading-6 text-muted-foreground">{item.detail}</p>
          <div className="mt-2 h-1 w-full bg-line" aria-hidden="true">
            <div className="h-1 bg-intelligence" style={{ width: `${Math.round(item.share * 100)}%` }} />
          </div>
        </li>
      ))}
    </ol>
  );
}
