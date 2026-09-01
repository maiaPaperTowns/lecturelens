import { Link } from "react-router-dom";

import type { ConceptSummary } from "../types";
import { ConceptTypeBadge, ConfidenceMeter, DifficultyBadge } from "./Badges";

export type SortKey = "source" | "difficulty" | "confidence" | "relevance";

interface Props {
  concepts: ConceptSummary[];
  sortBy: SortKey;
  descending: boolean;
  onSort: (key: SortKey) => void;
}

const COLUMNS: { key: SortKey | null; label: string }[] = [
  { key: null, label: "Concept" },
  { key: null, label: "Type" },
  { key: "difficulty", label: "Difficulty" },
  { key: "confidence", label: "Confidence" },
  { key: null, label: "Cluster" },
  { key: "source", label: "Source" },
];

export function ConceptTable({ concepts, sortBy, descending, onSort }: Props) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line bg-paper text-left text-xs uppercase tracking-wide text-ink-faint">
              {COLUMNS.map((col) => (
                <th key={col.label} className="px-4 py-3 font-medium">
                  {col.key ? (
                    <button
                      className="inline-flex items-center gap-1 hover:text-ink"
                      onClick={() => onSort(col.key as SortKey)}
                    >
                      {col.label}
                      {sortBy === col.key && <span aria-hidden>{descending ? "▾" : "▴"}</span>}
                    </button>
                  ) : (
                    col.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {concepts.map((concept) => (
              <tr key={concept.id} className="hover:bg-paper">
                <td className="px-4 py-3">
                  <Link
                    to={`/concepts/${concept.id}`}
                    className="font-medium text-ink hover:text-wine"
                  >
                    {concept.name}
                  </Link>
                  {concept.source_section && (
                    <p className="text-xs text-ink-faint">{concept.source_section}</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <ConceptTypeBadge type={concept.concept_type} />
                </td>
                <td className="px-4 py-3">
                  <DifficultyBadge label={concept.difficulty_label} />
                </td>
                <td className="px-4 py-3">
                  <ConfidenceMeter value={concept.concept_type_confidence} />
                </td>
                <td className="px-4 py-3 text-ink-soft">{concept.cluster_label ?? "n/a"}</td>
                <td className="px-4 py-3 tabular-nums text-ink-faint">
                  {concept.source_page ? `p.${concept.source_page}` : `#${concept.order_index + 1}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {concepts.length === 0 && (
        <p className="p-6 text-center text-sm text-ink-faint">No concepts match the current filters.</p>
      )}
    </div>
  );
}
