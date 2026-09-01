import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ConceptTable, type SortKey } from "../components/ConceptTable";
import { Filters, type ConceptFilters } from "../components/Filters";
import { SummaryCard } from "../components/SummaryCard";
import { EmptyState, ErrorState, InlineSpinner, SkeletonTable } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { DIFFICULTY_LABELS } from "../lib/labels";
import { api, ApiRequestError } from "../services/api";
import type { DifficultyLabel } from "../types";

const EMPTY_FILTERS: ConceptFilters = { difficulty: "", conceptType: "", clusterId: "" };

export function LectureDashboardPage() {
  const { lectureId } = useParams();
  const id = Number(lectureId);
  const [searchParams] = useSearchParams();
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const lecture = useAsync(() => api.getLecture(id), [id]);
  const isAnalyzed = lecture.data?.status === "analyzed";

  const concepts = useAsync(
    () => (isAnalyzed ? api.getConcepts(id) : Promise.resolve(null)),
    [id, isAnalyzed],
  );
  const clusters = useAsync(
    () => (isAnalyzed ? api.getClusters(id) : Promise.resolve(null)),
    [id, isAnalyzed],
  );

  const [filters, setFilters] = useState<ConceptFilters>(() => {
    const cluster = searchParams.get("cluster");
    return cluster ? { ...EMPTY_FILTERS, clusterId: Number(cluster) } : EMPTY_FILTERS;
  });
  const [sortBy, setSortBy] = useState<SortKey>("source");
  const [descending, setDescending] = useState(false);

  const filteredConcepts = useMemo(() => {
    const rows = concepts.data?.concepts ?? [];
    const filtered = rows.filter((c) => {
      if (filters.difficulty && c.difficulty_label !== filters.difficulty) return false;
      if (filters.conceptType && c.concept_type !== filters.conceptType) return false;
      if (filters.clusterId !== "" && c.cluster_id !== filters.clusterId) return false;
      return true;
    });
    const dir = descending ? -1 : 1;
    const key = (c: (typeof rows)[number]) => {
      if (sortBy === "difficulty") return c.difficulty_score ?? 0;
      if (sortBy === "confidence") return c.concept_type_confidence ?? 0;
      if (sortBy === "relevance") return c.relevance_score;
      return c.order_index;
    };
    return [...filtered].sort((a, b) => (key(a) - key(b)) * dir);
  }, [concepts.data, filters, sortBy, descending]);

  const stats = useMemo(() => {
    const rows = concepts.data?.concepts ?? [];
    const counts: Record<DifficultyLabel, number> = { easy: 0, medium: 0, hard: 0 };
    let hardest = rows[0];
    for (const c of rows) {
      if (c.difficulty_label) counts[c.difficulty_label] += 1;
      if ((c.difficulty_score ?? 0) > (hardest?.difficulty_score ?? -1)) hardest = c;
    }
    const avgScore =
      rows.length > 0
        ? rows.reduce((sum, c) => sum + (c.difficulty_score ?? 0), 0) / rows.length
        : 0;
    const topCluster = [...(clusters.data?.clusters ?? [])].sort(
      (a, b) => b.importance_score - a.importance_score,
    )[0];
    return { counts, hardest, avgScore, topCluster };
  }, [concepts.data, clusters.data]);

  function handleSort(key: SortKey) {
    if (sortBy === key) setDescending((d) => !d);
    else {
      setSortBy(key);
      setDescending(key === "difficulty" || key === "confidence" || key === "relevance");
    }
  }

  async function runAnalysis() {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      await api.analyzeLecture(id);
      lecture.reload();
    } catch (err) {
      setAnalyzeError(err instanceof ApiRequestError ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }

  if (lecture.loading) return <SkeletonTable rows={6} />;
  if (lecture.error || !lecture.data)
    return <ErrorState message={lecture.error ?? "Lecture not found"} onRetry={lecture.reload} />;

  const l = lecture.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">{l.course_name}</p>
          <h1 className="text-2xl font-bold text-ink">{l.lecture_title}</h1>
          <p className="mt-1 text-xs text-ink-faint">
            {l.files.map((f) => f.file_name).join(", ")} · {l.chunk_count} chunks
          </p>
        </div>
        {isAnalyzed && (
          <Link to={`/lectures/${id}/clusters`} className="btn-ghost">
            View study clusters →
          </Link>
        )}
      </div>

      {l.status === "uploaded" && (
        <EmptyState
          title="This lecture hasn't been analyzed yet"
          description="Run the ML pipeline to detect concepts, estimate difficulty and build clusters."
          action={
            <button className="btn-primary" onClick={runAnalysis} disabled={analyzing}>
              {analyzing ? "Analyzing..." : "Run analysis"}
            </button>
          }
        />
      )}
      {l.status === "processing" && (
        <div className="card p-8 text-center">
          <InlineSpinner label="Analysis in progress, refresh in a moment." />
        </div>
      )}
      {l.status === "failed" && (
        <ErrorState
          message={l.analysis_error ?? "Analysis failed for this lecture."}
          onRetry={runAnalysis}
        />
      )}
      {analyzeError && <ErrorState message={analyzeError} />}

      {isAnalyzed && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <SummaryCard label="Concepts" value={concepts.data?.total ?? ", "} />
            <SummaryCard label="Study clusters" value={clusters.data?.total ?? ", "} />
            <SummaryCard
              label="Avg difficulty"
              value={stats.avgScore ? stats.avgScore.toFixed(2) : ", "}
              hint={`${stats.counts.hard} hard · ${stats.counts.medium} medium · ${stats.counts.easy} easy`}
            />
            <SummaryCard
              label="Hardest concept"
              value={
                stats.hardest ? (
                  <Link to={`/concepts/${stats.hardest.id}`} className="hover:text-wine">
                    {stats.hardest.name}
                  </Link>
                ) : (
                  ", "
                )
              }
              hint={stats.hardest?.difficulty_label ? DIFFICULTY_LABELS[stats.hardest.difficulty_label] : undefined}
            />
            <SummaryCard
              label="Top cluster"
              value={stats.topCluster?.label ?? ", "}
              hint={
                stats.topCluster
                  ? `importance ${Math.round(stats.topCluster.importance_score * 100)}%`
                  : undefined
              }
            />
          </div>

          <div className="card space-y-4 p-4">
            <Filters
              filters={filters}
              clusters={(clusters.data?.clusters ?? []).map((c) => ({ id: c.id, label: c.label }))}
              onChange={setFilters}
              onReset={() => setFilters(EMPTY_FILTERS)}
            />
            <p className="text-xs text-ink-faint">
              Showing {filteredConcepts.length} of {concepts.data?.total ?? 0} concepts
            </p>
          </div>

          {concepts.error ? (
            <ErrorState message={concepts.error} onRetry={concepts.reload} />
          ) : concepts.loading && !concepts.data ? (
            <SkeletonTable />
          ) : (
            <ConceptTable
              concepts={filteredConcepts}
              sortBy={sortBy}
              descending={descending}
              onSort={handleSort}
            />
          )}
        </>
      )}
    </div>
  );
}
