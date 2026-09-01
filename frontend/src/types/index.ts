export type UploadStatus = "uploaded" | "processing" | "analyzed" | "failed";

export type DifficultyLabel = "easy" | "medium" | "hard";

export type ConceptType =
  | "definition"
  | "example"
  | "theorem_or_rule"
  | "process"
  | "comparison"
  | "implementation_detail"
  | "background_information";

export interface UploadedFile {
  id: number;
  file_name: string;
  file_type: string;
  size_bytes: number;
  page_count: number | null;
  created_at: string;
}

export interface LectureSummary {
  id: number;
  course_name: string;
  lecture_title: string;
  status: UploadStatus;
  created_at: string;
  analyzed_at: string | null;
  concept_count: number;
  cluster_count: number;
}

export interface LectureDetail extends LectureSummary {
  analysis_error: string | null;
  files: UploadedFile[];
  chunk_count: number;
}

export interface AnalyzeResponse {
  lecture_id: number;
  status: UploadStatus;
  concept_count: number;
  cluster_count: number;
  chunk_count: number;
  duration_ms: number;
  model_versions: Record<string, string>;
  warnings: string[];
}

export interface ConceptSummary {
  id: number;
  name: string;
  concept_type: ConceptType | null;
  concept_type_confidence: number | null;
  difficulty_label: DifficultyLabel | null;
  difficulty_score: number | null;
  difficulty_confidence: number | null;
  relevance_score: number;
  source_page: number | null;
  source_section: string | null;
  order_index: number;
  cluster_id: number | null;
  cluster_label: string | null;
}

export interface RelatedConcept {
  id: number;
  name: string;
  concept_type: ConceptType | null;
  difficulty_label: DifficultyLabel | null;
  similarity: number;
}

export interface PredictionOut {
  task: string;
  predicted_label: string;
  predicted_score: number | null;
  confidence: number | null;
  model_name: string;
  model_version: string;
  latency_ms: number | null;
  created_at: string;
}

export interface ConceptDetail extends ConceptSummary {
  snippet: string;
  original_text: string | null;
  cluster_label: string | null;
  model_versions: Record<string, string>;
  related_concepts: RelatedConcept[];
  predictions: PredictionOut[];
  feedback_count: number;
}

export interface ConceptListResponse {
  lecture_id: number;
  total: number;
  concepts: ConceptSummary[];
}

export interface ClusterConceptPoint {
  id: number;
  name: string;
  difficulty_label: DifficultyLabel | null;
  difficulty_score: number | null;
  concept_type: ConceptType | null;
  x: number;
  y: number;
  is_representative: boolean;
}

export interface ClusterDetail {
  id: number;
  label: string;
  algorithm: string;
  cluster_index: number;
  concept_count: number;
  avg_difficulty_score: number;
  importance_score: number;
  keywords: string[];
  difficulty_distribution: Record<string, number>;
  concepts: ConceptSummary[];
  points: ClusterConceptPoint[];
}

export interface ClusterListResponse {
  lecture_id: number;
  algorithm: string;
  total: number;
  clusters: ClusterDetail[];
}

export interface FeedbackPayload {
  classification_is_correct?: boolean | null;
  corrected_label?: ConceptType | null;
  difficulty_direction?: "too_easy" | "correct" | "too_hard" | null;
  corrected_difficulty?: DifficultyLabel | null;
  note?: string | null;
}

export interface ModelCard {
  name: string;
  family: string;
  version: string;
  trained_at: string | null;
  is_active: boolean;
  metrics: Record<string, unknown>;
}

export interface ModelMetricsResponse {
  models: ModelCard[];
  feedback: {
    total: number;
    classification_flagged_incorrect: number;
    difficulty_flagged_off: number;
    corrections_with_label: number;
    by_concept_type: Record<string, number>;
    recent: Array<Record<string, unknown>>;
  };
  predictions: {
    total_predictions: number;
    by_task: Record<string, number>;
    by_model_version: Record<string, number>;
    avg_latency_ms: number | null;
    p95_latency_ms: number | null;
  };
  lectures_analyzed: number;
  concepts_total: number;
  clusters_total: number;
}

export interface ApiError {
  error: { code: string; message: string; detail?: unknown };
}
