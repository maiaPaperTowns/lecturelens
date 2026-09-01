import type { ConceptType, DifficultyLabel } from "../types";
import { CONCEPT_TYPE_LABELS, DIFFICULTY_LABELS } from "../lib/labels";

const DIFFICULTY_CLASSES: Record<DifficultyLabel, string> = {
  easy: "bg-green-50 text-green-700 ring-1 ring-green-200",
  medium: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  hard: "bg-red-50 text-red-700 ring-1 ring-red-200",
};

export function DifficultyBadge({ label }: { label: DifficultyLabel | null }) {
  if (!label) return <span className="badge bg-line/60 text-ink-faint">Unrated</span>;
  return <span className={`badge ${DIFFICULTY_CLASSES[label]}`}>{DIFFICULTY_LABELS[label]}</span>;
}

export function ConceptTypeBadge({ type }: { type: ConceptType | null }) {
  if (!type) return <span className="badge bg-line/60 text-ink-faint">, </span>;
  return (
    <span className="badge bg-accent-soft text-wine ring-1 ring-line">
      {CONCEPT_TYPE_LABELS[type]}
    </span>
  );
}

export function ConfidenceMeter({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <span className="text-ink-faint">, </span>;
  const pct = Math.round(value * 100);
  const tone = pct >= 70 ? "bg-green-500" : pct >= 45 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-line/60">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-ink-faint">{pct}%</span>
    </div>
  );
}
