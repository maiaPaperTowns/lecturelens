import { Link } from "react-router-dom";

import { CLUSTER_PALETTE } from "../lib/labels";
import type { ClusterDetail } from "../types";
import { DifficultyBadge } from "./Badges";
import { DifficultyBar } from "./DifficultyBar";

export function ClusterCard({
  cluster,
  index,
  lectureId,
}: {
  cluster: ClusterDetail;
  index: number;
  lectureId: number;
}) {
  const color = CLUSTER_PALETTE[index % CLUSTER_PALETTE.length];
  return (
    <div className="glass flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
          <h3 className="font-semibold text-ink">{cluster.label}</h3>
        </div>
        <span className="badge bg-line/60 text-ink-soft">
          {cluster.concept_count} concept{cluster.concept_count === 1 ? "" : "s"}
        </span>
      </div>

      {cluster.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {cluster.keywords.slice(0, 5).map((kw) => (
            <span key={kw} className="badge bg-accent-soft text-wine">
              {kw}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-ink-faint">
          <span>Difficulty mix</span>
          <span>importance {Math.round(cluster.importance_score * 100)}%</span>
        </div>
        <DifficultyBar distribution={cluster.difficulty_distribution} />
      </div>

      <ul className="mt-1 space-y-1 text-sm">
        {cluster.concepts.slice(0, 5).map((concept) => (
          <li key={concept.id} className="flex items-center justify-between gap-2">
            <Link to={`/concepts/${concept.id}`} className="truncate text-ink hover:text-wine">
              {concept.name}
            </Link>
            <DifficultyBadge label={concept.difficulty_label} />
          </li>
        ))}
      </ul>
      {cluster.concepts.length > 5 && (
        <Link
          to={`/lectures/${lectureId}?cluster=${cluster.id}`}
          className="text-xs font-medium text-wine hover:underline"
        >
          +{cluster.concepts.length - 5} more in the concept table
        </Link>
      )}
    </div>
  );
}
