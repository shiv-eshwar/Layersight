import type { Band } from "@/lib/types";
import { formatScore } from "@/lib/format";

const bandClass: Record<Band, string> = {
  critical: "text-threat",
  high: "text-threat",
  suspicious: "text-warning",
  low: "text-protected",
};

const bandStroke: Record<Band, string> = {
  critical: "#ff5c6c",
  high: "#ff5c6c",
  suspicious: "#ff8a3d",
  low: "#3ddc97",
};

export function RiskScore({ score, band }: { score: number; band: Band }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const dash = (pct / 100) * circumference;
  return (
    <div className="ls-panel flex items-center gap-3 px-4 py-3" data-testid="risk-score">
      <div>
        <p className="text-xs tracking-wide text-[#949aab] uppercase">Risk score</p>
        <p className={`mt-1 font-mono text-sm tabular-nums ${bandClass[band]}`}>{formatScore(score)}</p>
      </div>
      <svg width="88" height="88" viewBox="0 0 88 88" aria-hidden="true">
        <circle cx="44" cy="44" r={radius} fill="none" stroke="#2a2e3c" strokeWidth="8" />
        <circle
          cx="44"
          cy="44"
          r={radius}
          fill="none"
          stroke={bandStroke[band]}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference - dash}`}
          transform="rotate(-90 44 44)"
        />
        <text x="44" y="42" textAnchor="middle" fill="#f4f6fb" fontSize="18" fontWeight="700">{pct}</text>
        <text x="44" y="56" textAnchor="middle" fill="#949aab" fontSize="9">/ 100</text>
      </svg>
    </div>
  );
}

export function BandBadge({ band }: { band: Band }) {
  const label = band === "low" ? "Low" : band === "suspicious" ? "Suspicious" : band === "high" ? "High" : "Critical";
  return <span className={`text-sm font-medium ${bandClass[band]}`}>{label}</span>;
}

export function VerdictText({ label }: { label: "phishing" | "genuine" }) {
  const phishing = label === "phishing";
  return (
    <span
      className={
        phishing
          ? "inline-flex items-center rounded-full bg-[#3a1520] px-2.5 py-0.5 text-xs font-semibold text-[#ff8b96]"
          : "inline-flex items-center rounded-full bg-[#10291f] px-2.5 py-0.5 text-xs font-semibold text-[#3ddc97]"
      }
    >
      {phishing ? "Phishing" : "Genuine"}
    </span>
  );
}

export function AuthBadge({ name, value }: { name: string; value: string }) {
  const tone = value === "pass" ? "text-[#3ddc97]" : value === "none" ? "text-[#949aab]" : "text-[#ff8b96]";
  return (
    <span
      className="rounded-xl border border-white/10 bg-black/30 px-3 py-2"
      data-testid={`auth-${name.toLowerCase()}`}
      data-status={value}
    >
      <span className="block text-[10px] tracking-wide text-[#949aab] uppercase">{name}</span>
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
    <ol className="ls-panel flex flex-col overflow-hidden px-4">
      {items.map((item) => (
        <li
          key={`${item.rule_id}-${item.detail}`}
          className="border-t border-white/8 py-4 first:border-t-0"
          data-testid="evidence-item"
          data-rule={item.rule_id}
        >
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
          <div className="mt-2 h-1.5 w-full rounded-full bg-[#2a2e3c]" aria-hidden="true">
            <div className="h-1.5 rounded-full bg-[#8b7cff]" style={{ width: `${Math.round(item.share * 100)}%` }} />
          </div>
        </li>
      ))}
    </ol>
  );
}
