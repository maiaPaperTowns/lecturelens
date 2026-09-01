import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { SummaryCard } from "../components/SummaryCard";
import { ErrorState, Skeleton } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { CLUSTER_PALETTE } from "../lib/labels";
import { api } from "../services/api";

function metricValue(metrics: Record<string, unknown>, key: string): string {
  const v = metrics[key];
  return typeof v === "number" ? v.toFixed(3) : ", ";
}

export function ModelMetricsPage() {
  const { data, loading, error, reload } = useAsync(() => api.getModelMetrics());

  if (loading) return <Skeleton className="h-96" />;
  if (error || !data) return <ErrorState message={error ?? "Could not load metrics"} onRetry={reload} />;

  const feedbackByType = Object.entries(data.feedback.by_concept_type).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Model metrics</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Held-out evaluation of each model version, live inference stats, and how much feedback has
          been collected for the next retraining cycle.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard label="Lectures analyzed" value={data.lectures_analyzed} />
        <SummaryCard label="Concepts stored" value={data.concepts_total} />
        <SummaryCard label="Predictions logged" value={data.predictions.total_predictions} />
        <SummaryCard
          label="Feedback collected"
          value={data.feedback.total}
          hint={`${data.feedback.classification_flagged_incorrect} label · ${data.feedback.difficulty_flagged_off} difficulty`}
        />
      </div>

      <div className="card overflow-x-auto p-4">
        <h2 className="mb-3 text-sm font-semibold text-ink">Model versions</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-ink-faint">
            <tr>
              <th className="py-1">Model</th>
              <th>Family</th>
              <th>Version</th>
              <th>Accuracy</th>
              <th>F1 (macro)</th>
              <th>Trained</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {data.models.map((model) => (
              <tr key={`${model.name}-${model.version}`}>
                <td className="py-2 font-medium text-ink">{model.name}</td>
                <td className="text-ink-soft">{model.family}</td>
                <td className="font-mono text-xs">{model.version}</td>
                <td className="tabular-nums">{metricValue(model.metrics, "accuracy")}</td>
                <td className="tabular-nums">{metricValue(model.metrics, "f1_macro")}</td>
                <td className="text-xs text-ink-faint">
                  {model.trained_at ? model.trained_at.slice(0, 10) : ", "}
                </td>
                <td>
                  {model.is_active ? (
                    <span className="badge bg-green-50 text-green-700">active</span>
                  ) : (
                    <span className="badge bg-line/60 text-ink-faint">idle</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-ink-faint">
          Latency, avg {data.predictions.avg_latency_ms ?? ", "} ms, p95{" "}
          {data.predictions.p95_latency_ms ?? ", "} ms. Compare families by running{" "}
          <code className="rounded bg-line/60 px-1">python scripts/evaluate_models.py</code>.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="mb-3 text-sm font-semibold text-ink">Feedback by predicted type</h2>
          {feedbackByType.length === 0 ? (
            <p className="text-sm text-ink-faint">No feedback collected yet.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={feedbackByType} margin={{ left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e6eaf3" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} height={50} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {feedbackByType.map((_, i) => (
                      <Cell key={i} fill={CLUSTER_PALETTE[i % CLUSTER_PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="card p-4">
          <h2 className="mb-3 text-sm font-semibold text-ink">Recent corrections</h2>
          {data.feedback.recent.length === 0 ? (
            <p className="text-sm text-ink-faint">Nothing yet, submit feedback from any concept page.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.feedback.recent.slice(0, 8).map((entry, i) => (
                <li key={i} className="rounded-lg bg-paper px-3 py-2 text-xs text-ink-soft">
                  concept #{String(entry.concept_id)} · {String(entry.predicted_label ?? "?")} →{" "}
                  {String(entry.corrected_label ?? entry.difficulty_direction ?? "note")}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
