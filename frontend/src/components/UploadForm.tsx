import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiRequestError, uploadLecture } from "../services/api";

const ACCEPTED = [".pdf", ".txt", ".md", ".markdown", ".jpg", ".jpeg", ".png"];
const MAX_MB = 25;

function isAccepted(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED.some((ext) => name.endsWith(ext));
}

export function UploadForm() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [course, setCourse] = useState("");
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<"idle" | "uploading" | "analyzing" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const next: File[] = [];
    for (const file of Array.from(incoming)) {
      if (!isAccepted(file)) {
        setError(`"${file.name}" is not a supported file type (PDF, image, TXT, MD).`);
        continue;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`"${file.name}" exceeds the ${MAX_MB} MB limit.`);
        continue;
      }
      next.push(file);
    }
    if (next.length) setError(null);
    setFiles((prev) => [...prev, ...next]);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!course.trim() || !title.trim() || files.length === 0) {
      setError("Course, lecture title and at least one file are required.");
      return;
    }
    setError(null);
    setPhase("uploading");
    setProgress(0);
    try {
      const { lecture } = await uploadLecture({
        courseName: course.trim(),
        lectureTitle: title.trim(),
        files,
        onProgress: setProgress,
      });
      setPhase("analyzing");
      // kick off analysis, then land on the dashboard
      await api.analyzeLecture(lecture.id);
      navigate(`/lectures/${lecture.id}`);
    } catch (err) {
      setPhase("error");
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Upload failed. Check that the backend is running.",
      );
    }
  }

  const busy = phase === "uploading" || phase === "analyzing";

  return (
    <form className="card space-y-5 p-6" onSubmit={handleSubmit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-medium text-ink">
          Course name
          <input
            className="input"
            placeholder="CS 201 · Algorithms"
            value={course}
            onChange={(e) => setCourse(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-ink">
          Lecture title
          <input
            className="input"
            placeholder="Binary Search and Divide-and-Conquer"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
      </div>

      <div
        className={`rounded-xl border-2 border-dashed p-6 text-center transition ${
          dragging ? "border-wine bg-accent-soft" : "border-line bg-paper"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
      >
        <p className="text-sm text-ink-soft">
          Drag & drop lecture notes / slides here, or{" "}
          <button
            type="button"
            className="font-medium text-wine hover:underline"
            onClick={() => inputRef.current?.click()}
          >
            browse
          </button>
        </p>
        <p className="mt-1 text-xs text-ink-faint">PDF, image (JPG/PNG), TXT or Markdown · up to {MAX_MB} MB each</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          aria-label="Lecture files"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="space-y-1 text-sm" data-testid="file-list">
          {files.map((file, i) => (
            <li
              key={`${file.name}-${i}`}
              className="flex items-center justify-between rounded-lg bg-paper px-3 py-2"
            >
              <span className="truncate text-ink">{file.name}</span>
              <button
                type="button"
                className="text-xs text-ink-faint hover:text-red-600"
                onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
              >
                remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {busy && (
        <div className="space-y-2" role="status">
          <div className="h-2 overflow-hidden rounded-full bg-line/60">
            <div
              className="h-full bg-wine transition-all"
              style={{ width: phase === "analyzing" ? "100%" : `${progress}%` }}
            />
          </div>
          <p className="text-xs text-ink-faint">
            {phase === "uploading" ? `Uploading... ${progress}%` : "Running the analysis pipeline..."}
          </p>
        </div>
      )}

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <button className="btn-primary w-full" type="submit" disabled={busy}>
        {busy ? "Working..." : "Upload & analyze"}
      </button>
    </form>
  );
}
