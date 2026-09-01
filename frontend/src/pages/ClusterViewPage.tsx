import { Link, useParams } from "react-router-dom";

import { ClusterCard } from "../components/ClusterCard";
import { EmbeddingScatter } from "../components/EmbeddingScatter";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export function ClusterViewPage() {
  const { lectureId } = useParams();
  const id = Number(lectureId);
  const { data, loading, error, reload } = useAsync(() => api.getClusters(id), [id]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Study clusters</h1>
          {data && (
            <p className="text-xs text-ink-faint">
              {data.total} clusters · grouped with {data.algorithm} over concept embeddings
            </p>
          )}
        </div>
        <Link to={`/lectures/${id}`} className="btn-ghost">
          ← Back to dashboard
        </Link>
      </div>

      {loading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52" />
          ))}
        </div>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && data?.total === 0 && (
        <EmptyState title="No clusters" description="Analyze the lecture to generate study clusters." />
      )}

      {!loading && !error && data && data.total > 0 && (
        <>
          <div className="glass p-4">
            <h2 className="mb-2 text-sm font-semibold text-ink">Concept embedding map</h2>
            <p className="mb-3 text-xs text-ink-faint">
              2-D projection (t-SNE / PCA) of concept embeddings, coloured by cluster.
            </p>
            <EmbeddingScatter clusters={data.clusters} />
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.clusters.map((cluster, index) => (
              <ClusterCard key={cluster.id} cluster={cluster} index={index} lectureId={id} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
