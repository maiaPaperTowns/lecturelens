import type {
  ClusterListResponse,
  ConceptDetail,
  ConceptListResponse,
  LectureDetail,
} from "../src/types";

export const lectureFixture: LectureDetail = {
  id: 1,
  course_name: "CS 201",
  lecture_title: "Binary Search",
  status: "analyzed",
  created_at: "2026-01-01T00:00:00Z",
  analyzed_at: "2026-01-01T00:05:00Z",
  analysis_error: null,
  concept_count: 3,
  cluster_count: 2,
  chunk_count: 9,
  files: [
    { id: 1, file_name: "binary_search.md", file_type: "md", size_bytes: 1234, page_count: 1, created_at: "2026-01-01T00:00:00Z" },
  ],
};

export const conceptsFixture: ConceptListResponse = {
  lecture_id: 1,
  total: 3,
  concepts: [
    {
      id: 10,
      name: "Binary Search",
      concept_type: "definition",
      concept_type_confidence: 0.91,
      difficulty_label: "medium",
      difficulty_score: 0.55,
      difficulty_confidence: 0.7,
      relevance_score: 1.0,
      source_page: 1,
      source_section: "Definition",
      order_index: 0,
      cluster_id: 100,
      cluster_label: "Search & Intervals",
    },
    {
      id: 11,
      name: "Loop Invariant",
      concept_type: "theorem_or_rule",
      concept_type_confidence: 0.66,
      difficulty_label: "hard",
      difficulty_score: 0.83,
      difficulty_confidence: 0.6,
      relevance_score: 0.7,
      source_page: 2,
      source_section: "The Core Rule",
      order_index: 1,
      cluster_id: 100,
      cluster_label: "Search & Intervals",
    },
    {
      id: 12,
      name: "Midpoint Overflow",
      concept_type: "implementation_detail",
      concept_type_confidence: 0.8,
      difficulty_label: "easy",
      difficulty_score: 0.25,
      difficulty_confidence: 0.75,
      relevance_score: 0.4,
      source_page: 3,
      source_section: "Implementation Detail",
      order_index: 2,
      cluster_id: 101,
      cluster_label: "Implementation",
    },
  ],
};

export const clustersFixture: ClusterListResponse = {
  lecture_id: 1,
  algorithm: "kmeans",
  total: 2,
  clusters: [
    {
      id: 100,
      label: "Search & Intervals",
      algorithm: "kmeans",
      cluster_index: 0,
      concept_count: 2,
      avg_difficulty_score: 0.69,
      importance_score: 0.7,
      keywords: ["interval", "sorted"],
      difficulty_distribution: { easy: 0, medium: 1, hard: 1 },
      concepts: conceptsFixture.concepts.slice(0, 2),
      points: [
        { id: 10, name: "Binary Search", difficulty_label: "medium", difficulty_score: 0.55, concept_type: "definition", x: 10, y: 20, is_representative: true },
        { id: 11, name: "Loop Invariant", difficulty_label: "hard", difficulty_score: 0.83, concept_type: "theorem_or_rule", x: 15, y: 25, is_representative: false },
      ],
    },
    {
      id: 101,
      label: "Implementation",
      algorithm: "kmeans",
      cluster_index: 1,
      concept_count: 1,
      avg_difficulty_score: 0.25,
      importance_score: 0.3,
      keywords: ["overflow"],
      difficulty_distribution: { easy: 1, medium: 0, hard: 0 },
      concepts: conceptsFixture.concepts.slice(2),
      points: [
        { id: 12, name: "Midpoint Overflow", difficulty_label: "easy", difficulty_score: 0.25, concept_type: "implementation_detail", x: 80, y: 70, is_representative: true },
      ],
    },
  ],
};

export const conceptDetailFixture: ConceptDetail = {
  ...conceptsFixture.concepts[0],
  snippet: "Binary search is defined as an algorithm that locates a target value in a sorted array.",
  original_text: "Binary search is defined as an algorithm that locates a target value in a sorted array by repeatedly halving the interval.",
  cluster_label: "Search & Intervals",
  model_versions: { concept_type: "sklearn-gradient_boosting", difficulty: "pytorch-mlp-v1" },
  related_concepts: [
    { id: 11, name: "Loop Invariant", concept_type: "theorem_or_rule", difficulty_label: "hard", similarity: 0.62 },
  ],
  predictions: [
    { task: "concept_type", predicted_label: "definition", predicted_score: null, confidence: 0.91, model_name: "concept_classifier", model_version: "sklearn-gradient_boosting", latency_ms: 1.2, created_at: "2026-01-01T00:05:00Z" },
    { task: "difficulty", predicted_label: "medium", predicted_score: 0.55, confidence: 0.7, model_name: "difficulty", model_version: "pytorch-mlp-v1", latency_ms: 2.1, created_at: "2026-01-01T00:05:00Z" },
  ],
  feedback_count: 0,
};
