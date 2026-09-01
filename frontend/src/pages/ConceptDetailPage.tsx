import { Link, useParams } from "react-router-dom";

import { ConceptTypeBadge, ConfidenceMeter, DifficultyBadge } from "../components/Badges";
import { FeedbackControls } from "../components/FeedbackControls";
import { ErrorState, Skeleton } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export function ConceptDetailPage() {
  const { conceptId } = useParams();
  const id = Number(conceptId);
  const { data, loading, error, reload } = useAsync(() => api.getConcept(id), [id]);

  if (loading) return <Skeleton className="h-96" />;
  if (error || !data) return <ErrorState message={error ?? "Concept not found"} onRetry={reload} />;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">
            {data.source_section ?? "Concept"}
            {data.source_page ? ` · page ${data.source_page}` : ""}
          </p>
          <h1 className="text-2xl font-bold text-ink">{data.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <ConceptTypeBadge type={data.concept_type} />
            <DifficultyBadge label={data.difficulty_label} />
            {data.cluster_label && (
              <span className="badge bg-line/60 text-ink-soft">cluster: {data.cluster_label}</span>
            )}
          </div>
        </div>

        <div className="glass p-4">
          <h2 className="text-sm font-semibold text-ink">Snippet</h2>
          <p className="mt-1 text-sm text-ink">{data.snippet}</p>
          {data.original_text && data.original_text !== data.snippet && (
            <>
              <h3 className="mt-4 text-sm font-semibold text-ink">Source passage</h3>
              <p className="mt-1 whitespace-pre-line text-sm text-ink-soft">{data.original_text}</p>
            </>
          )}
        </div>

        <div className="glass p-4">
          <h2 className="text-sm font-semibold text-ink">Model predictions</h2>
          <table className="mt-2 w-full text-sm">
            <thead className="text-left text-xs uppercase text-ink-faint">
              <tr>
                <th className="py-1">Task</th>
                <th>Label</th>
                <th>Confidence</th>
                <th>Model</th>
                <th className="text-right">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.predictions.map((p, i) => (
                <tr key={i}>
                  <td className="py-1.5 text-ink-soft">{p.task}</td>
                  <td className="font-medium text-ink">{p.predicted_label}</td>
                  <td>
                    <ConfidenceMeter value={p.confidence} />
                  </td>
                  <td className="font-mono text-xs text-ink-faint">
                    {p.model_name}@{p.model_version}
                  </td>
                  <td className="text-right tabular-nums text-ink-faint">
                    {p.latency_ms ? `${p.latency_ms.toFixed(1)} ms` : "n/a"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <FeedbackControls concept={data} onSubmitted={reload} />
      </div>

      <aside className="space-y-4">
        <div className="glass p-4">
          <h2 className="text-sm font-semibold text-ink">Related concepts</h2>
          {data.related_concepts.length === 0 ? (
            <p className="mt-2 text-sm text-ink-faint">No strongly related concepts found.</p>
          ) : (
            <ul className="mt-2 space-y-2 text-sm">
              {data.related_concepts.map((rc) => (
                <li key={rc.id} className="flex items-center justify-between gap-2">
                  <Link to={`/concepts/${rc.id}`} className="truncate text-ink hover:text-wine">
                    {rc.name}
                  </Link>
                  <span className="text-xs tabular-nums text-ink-faint">
                    {Math.round(rc.similarity * 100)}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="glass p-4 text-xs text-ink-faint">
          <h2 className="text-sm font-semibold text-ink">Provenance</h2>
          <dl className="mt-2 space-y-1">
            <div className="flex justify-between">
              <dt>Relevance score</dt>
              <dd className="tabular-nums">{data.relevance_score.toFixed(3)}</dd>
            </div>
            {Object.entries(data.model_versions).map(([task, version]) => (
              <div key={task} className="flex justify-between">
                <dt>{task} model</dt>
                <dd className="font-mono">{version}</dd>
              </div>
            ))}
            <div className="flex justify-between">
              <dt>Feedback received</dt>
              <dd>{data.feedback_count}</dd>
            </div>
          </dl>
        </div>
      </aside>
    </div>
  );
}
