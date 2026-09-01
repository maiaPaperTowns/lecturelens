import type { ConceptType, DifficultyLabel } from "../types";

export const CONCEPT_TYPE_LABELS: Record<ConceptType, string> = {
  definition: "Definition",
  example: "Example",
  theorem_or_rule: "Theorem / Rule",
  process: "Process",
  comparison: "Comparison",
  implementation_detail: "Implementation",
  background_information: "Background",
};

export const CONCEPT_TYPE_OPTIONS = Object.entries(CONCEPT_TYPE_LABELS) as [ConceptType, string][];

export const DIFFICULTY_LABELS: Record<DifficultyLabel, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

export const DIFFICULTY_COLORS: Record<DifficultyLabel, string> = {
  easy: "#0f9d58",
  medium: "#d99a00",
  hard: "#d64545",
};

export const CLUSTER_PALETTE = [
  "#4f46e5",
  "#0891b2",
  "#0f9d58",
  "#d99a00",
  "#d64545",
  "#9333ea",
  "#db2777",
  "#65a30d",
];

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return ", ";
  return `${Math.round(value * 100)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return ", ";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
