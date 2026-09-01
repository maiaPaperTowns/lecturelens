import { useState } from "react";

import { api, ApiRequestError } from "../services/api";
import type { ConceptDetail, ConceptType } from "../types";
import { CONCEPT_TYPE_OPTIONS } from "../lib/labels";

type DifficultyDirection = "too_easy" | "correct" | "too_hard";

export function FeedbackControls({
  concept,
  onSubmitted,
}: {
  concept: ConceptDetail;
  onSubmitted?: () => void;
}) {
  const [classificationOk, setClassificationOk] = useState<boolean | null>(null);
  const [correctedLabel, setCorrectedLabel] = useState<ConceptType | "">("");
  const [difficultyDirection, setDifficultyDirection] = useState<DifficultyDirection | "">("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    classificationOk !== null || correctedLabel || difficultyDirection || note.trim();

  async function submit() {
    setStatus("saving");
    setError(null);
    try {
      await api.submitFeedback(concept.id, {
        classification_is_correct: classificationOk,
        corrected_label: correctedLabel || null,
        difficulty_direction: difficultyDirection || null,
        note: note.trim() || null,
      });
      setStatus("done");
      onSubmitted?.();
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiRequestError ? err.message : "Could not save feedback");
    }
  }

  if (status === "done") {
    return (
      <div className="card border-green-100 bg-green-50/50 p-4 text-sm text-green-700">
        Thanks, your feedback was recorded. It feeds the training-data export on the metrics page.
      </div>
    );
  }

  return (
    <div className="glass space-y-4 p-4" data-testid="feedback-controls">
      <div>
        <p className="text-sm font-medium text-ink">Is the “{concept.concept_type}” label correct?</p>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            className={`btn-ghost ${classificationOk === true ? "border-wine text-wine" : ""}`}
            aria-pressed={classificationOk === true}
            onClick={() => setClassificationOk(true)}
          >
            Correct
          </button>
          <button
            type="button"
            className={`btn-ghost ${classificationOk === false ? "border-red-400 text-red-600" : ""}`}
            aria-pressed={classificationOk === false}
            onClick={() => setClassificationOk(false)}
          >
            Incorrect
          </button>
        </div>
        {classificationOk === false && (
          <select
            className="input mt-2"
            aria-label="Corrected concept type"
            value={correctedLabel}
            onChange={(e) => setCorrectedLabel(e.target.value as ConceptType | "")}
          >
            <option value="">Pick the right type...</option>
            {CONCEPT_TYPE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        )}
      </div>

      <div>
        <p className="text-sm font-medium text-ink">
          Difficulty is rated “{concept.difficulty_label}”. How does that feel?
        </p>
        <div className="mt-2 flex gap-2">
          {(["too_easy", "correct", "too_hard"] as DifficultyDirection[]).map((dir) => (
            <button
              key={dir}
              type="button"
              className={`btn-ghost ${difficultyDirection === dir ? "border-wine text-wine" : ""}`}
              aria-pressed={difficultyDirection === dir}
              onClick={() => setDifficultyDirection(dir)}
            >
              {dir.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <textarea
        className="input"
        rows={2}
        placeholder="Optional note for the ML team..."
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button className="btn-primary" disabled={!canSubmit || status === "saving"} onClick={submit}>
        {status === "saving" ? "Saving..." : "Submit feedback"}
      </button>
    </div>
  );
}
