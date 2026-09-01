import type { ConceptType, DifficultyLabel } from "../types";
import { CONCEPT_TYPE_OPTIONS, DIFFICULTY_LABELS } from "../lib/labels";

export interface ConceptFilters {
  difficulty: DifficultyLabel | "";
  conceptType: ConceptType | "";
  clusterId: number | "";
}

interface Props {
  filters: ConceptFilters;
  clusters: { id: number; label: string }[];
  onChange: (next: ConceptFilters) => void;
  onReset: () => void;
}

export function Filters({ filters, clusters, onChange, onReset }: Props) {
  const hasActive = filters.difficulty || filters.conceptType || filters.clusterId !== "";
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs font-medium text-ink-faint">
        Difficulty
        <select
          className="input"
          aria-label="Filter by difficulty"
          value={filters.difficulty}
          onChange={(e) =>
            onChange({ ...filters, difficulty: e.target.value as DifficultyLabel | "" })
          }
        >
          <option value="">All</option>
          {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-ink-faint">
        Concept type
        <select
          className="input"
          aria-label="Filter by concept type"
          value={filters.conceptType}
          onChange={(e) =>
            onChange({ ...filters, conceptType: e.target.value as ConceptType | "" })
          }
        >
          <option value="">All</option>
          {CONCEPT_TYPE_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-ink-faint">
        Cluster
        <select
          className="input"
          aria-label="Filter by cluster"
          value={filters.clusterId}
          onChange={(e) =>
            onChange({
              ...filters,
              clusterId: e.target.value === "" ? "" : Number(e.target.value),
            })
          }
        >
          <option value="">All</option>
          {clusters.map((cluster) => (
            <option key={cluster.id} value={cluster.id}>
              {cluster.label}
            </option>
          ))}
        </select>
      </label>

      {hasActive && (
        <button className="btn-ghost" onClick={onReset}>
          Clear filters
        </button>
      )}
    </div>
  );
}
