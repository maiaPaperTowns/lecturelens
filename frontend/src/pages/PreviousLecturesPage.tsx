import { Link } from "react-router-dom";

import { EmptyState, ErrorState, SkeletonTable } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { formatDate } from "../lib/labels";
import { api } from "../services/api";

const STATUS_STYLES: Record<string, string> = {
  analyzed: "bg-green-50 text-green-700",
  processing: "bg-amber-50 text-amber-700",
  uploaded: "bg-line/60 text-ink-soft",
  failed: "bg-red-50 text-red-700",
};

export function PreviousLecturesPage() {
  const { data, loading, error, reload } = useAsync(() => api.listLectures());

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">Previous lectures</h1>
        <Link to="/upload" className="btn-primary">
          New upload
        </Link>
      </div>

      {loading && <SkeletonTable rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && data?.length === 0 && (
        <EmptyState
          title="No lectures yet"
          description="Upload your first lecture to generate a study map."
          action={
            <Link to="/upload" className="btn-primary">
              Upload a lecture
            </Link>
          }
        />
      )}

      {!loading && !error && data && data.length > 0 && (
        <div className="card divide-y divide-line">
          {data.map((lecture) => (
            <Link
              key={lecture.id}
              to={`/lectures/${lecture.id}`}
              className="flex items-center justify-between gap-4 p-4 hover:bg-paper"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{lecture.lecture_title}</p>
                <p className="text-xs text-ink-faint">
                  {lecture.course_name} · uploaded {formatDate(lecture.created_at)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3 text-xs text-ink-faint">
                <span>{lecture.concept_count} concepts</span>
                <span>{lecture.cluster_count} clusters</span>
                <span
                  className={`badge ${STATUS_STYLES[lecture.status] ?? "bg-line/60 text-ink-soft"}`}
                >
                  {lecture.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
