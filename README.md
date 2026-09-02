# LectureLens

**Turn lecture notes, PDFs and slide decks into a structured study map.**

Upload lecture material and LectureLens will extract the text, mine the important
concepts, classify each one (definition / example / theorem / process /
comparison / implementation / background), estimate its difficulty, group related
concepts into study clusters, and render an interactive dashboard showing every
concept, its cluster, its difficulty and exactly where it came from in the
source. You can correct any classification or difficulty rating, and those
corrections are stored and exportable as a training dataset.

The ML is a **real, offline PyTorch + scikit-learn pipeline**, no LLM API is
used anywhere in concept detection, classification, difficulty estimation or
clustering.

**Live demo:** https://maiapapertowns.github.io/lecturelens/ (static snapshot of a
seeded database, read only). Run the full stack with `docker compose up` to
upload your own lectures.

---

## Table of contents

- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [ML pipeline](#ml-pipeline)
- [Model comparison](#model-comparison-sklearn-vs-pytorch)
- [Setup](#setup)
- [API endpoints](#api-endpoints)
- [Database schema](#database-schema)
- [Evaluation metrics](#evaluation-metrics)
- [Project layout](#project-layout)
- [Testing](#testing)
- [Future work](#future-work)
- [Résumé bullets](#résumé-bullets)

---

## Screenshots

> _Placeholder, add screenshots to `docs/screenshots/` and link them here._

| Landing | Lecture dashboard | Study clusters | Concept detail | Model metrics |
| --- | --- | --- | --- | --- |
| `docs/screenshots/landing.png` | `docs/screenshots/dashboard.png` | `docs/screenshots/clusters.png` | `docs/screenshots/concept.png` | `docs/screenshots/metrics.png` |

---

## Architecture

```mermaid
flowchart TD
    U[Student] -->|uploads PDF / image / TXT / MD| FE[React + TypeScript SPA]
    FE -->|REST /api| API[FastAPI]

    subgraph Backend
        API --> SVC[Service layer]
        SVC --> PRE[Preprocessing<br/>extract · clean · chunk]
        PRE --> ML

        subgraph ML[ML pipeline]
            EMB[TF-IDF + SVD embedder]
            CE[Concept extraction<br/>noun-phrase + TF-IDF]
            CC[Concept classifier<br/>sklearn baseline / PyTorch MLP]
            DF[Difficulty model<br/>sklearn baseline / PyTorch MLP]
            CL[Clustering<br/>KMeans / Agglomerative / DBSCAN]
            EMB --> CE --> CC --> DF --> CL
        end

        ML --> SVC
        SVC --> DB[(PostgreSQL<br/>SQLAlchemy + Alembic)]
        REG[Model registry<br/>models/ + metadata.json] -.-> ML
    end

    API --> DOCS[OpenAPI docs /docs]
    FB[Feedback loop] --> DB
    DB --> EXP[export_feedback.py<br/>training dataset]
```

Request flow for an analysis:

```
User -> React -> FastAPI -> Preprocessing -> PyTorch + scikit-learn services -> PostgreSQL
```

The layers are cleanly separated:

| Concern | Where |
| --- | --- |
| HTTP / schemas | `backend/app/api`, `backend/app/schemas` |
| Orchestration / business logic | `backend/app/services` |
| ML (no I/O, no DB) | `backend/app/ml` |
| Persistence | `backend/app/db` |
| Model artifacts + versioning | `models/` via `app/ml/registry.py` |
| UI | `frontend/src` |

---

## Tech stack

| Area | Choice |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router, Recharts |
| Backend | Python 3.11, FastAPI, Pydantic v2, Uvicorn |
| ML | PyTorch (neural classifiers), scikit-learn (baselines, clustering, metrics, TF-IDF/SVD) |
| File processing | PyMuPDF (PDF), Tesseract OCR (images + scanned PDFs), native text/Markdown |
| Database | PostgreSQL 16, SQLAlchemy 2.0, Alembic migrations |
| Testing | pytest + httpx (backend), Vitest + Testing Library (frontend) |
| Tooling | Ruff, ESLint, mypy-ready type hints |
| Infra | Docker + Docker Compose, GitHub Actions CI |

---

## ML pipeline

### 1. Preprocessing (`app/ml/preprocessing/`)

Pure, unit-tested functions, never called directly from a route.

- **Extraction**, PyMuPDF for PDFs (with a slide-deck heuristic), native reader
  for TXT/MD, and Tesseract OCR for images (JPG/PNG) and scanned PDFs with no
  text layer. Page/slide numbers preserved.
- **Cleaning**, unicode normalisation, de-hyphenation across line breaks,
  running-header/footer removal, whitespace collapsing.
- **Chunking**, paragraph-aware splitting that keeps `page_number`,
  `slide_number`, `paragraph_number` and `section_title`; merges tiny fragments,
  splits oversized ones on sentence boundaries, and drops near-duplicate chunks
  via normalised hashing.

### 2. Embeddings (`app/ml/embeddings/`)

`TfidfVectorizer -> TruncatedSVD (LSA) -> L2-normalise`. Fully deterministic and
offline. Trained on the synthetic training corpus + demo lectures; used as the
representation for concept relevance, clustering, 2-D projection **and** as the
feature backbone for the neural classifiers.

### 3. Concept detection (`app/ml/classification/concept_extractor.py`)

Noun-phrase candidate generation (regex, no spaCy dependency) -> TF-IDF ranking
across the lecture (`peak salience × √document-frequency`) -> phrase de-dup ->
best-sentence snippet selection. No LLM.

### 4. Concept classification (`app/ml/classification/`)

Classifies each concept snippet into one of seven academically meaningful types.
Features = **dense LSA embedding ++ hand-crafted lexical-cue features** (definitional
phrasing, worked-example markers, theorem/rule language, step lists, comparison
markers, code/complexity markers, background markers).

- **Baseline:** `SklearnTabularClassifier`, Logistic Regression / Random Forest /
  Gradient Boosting (selectable), `StandardScaler` pipeline.
- **Neural:** `TorchTabularClassifier`, a PyTorch MLP
  (`Linear -> BatchNorm -> ReLU -> Dropout` blocks) trained with Adam + weighted
  cross-entropy and early stopping on a validation split.
- Both expose the same `fit / predict / predict_proba / save / load` API, so
  they are directly comparable and hot-swappable via the registry.
- Until a model is trained, a documented **heuristic** classifier
  (`heuristic-v1`) serves predictions so the app is never broken.

### 5. Difficulty estimation (`app/ml/difficulty/`)

Predicts Easy / Medium / Hard **and** a continuous `difficulty_score ∈ [0,1]`
(expected value over the class distribution). Engineered features:
sentence length, vocabulary complexity (mean word length, type-token ratio,
long-word ratio), technical-term density, math-symbol density, concept frequency
in the lecture, **dependency on other concepts** (how many other concept names
appear in its snippet), snippet length, plus the LSA embedding. Same
baseline-vs-neural setup as above.

### 6. Clustering (`app/ml/clustering/`)

Switchable behind `get_clusterer(name, n_clusters)`:

- **KMeans**, **Agglomerative** (ward), **DBSCAN** (cosine; noise points become
  singletons).
- `k` chosen automatically by silhouette scan (`choose_k`).
- Cluster labels generated from the most central concepts + TF-IDF keywords over
  their snippets (`labeler.py`), no LLM.
- Per cluster: average difficulty, concept count, importance score
  (share of total concept relevance), difficulty distribution, 2-D centroid.

### 7. Evaluation (`app/ml/evaluation/`)

`classification_metrics` (accuracy, macro precision/recall/F1, confusion matrix),
`clustering_metrics` (silhouette, cluster sizes, mean intra-cluster cosine
similarity), `measure_latency` (mean / p50 / p95).

---

## Model comparison (sklearn vs PyTorch)

```bash
cd backend
python scripts/build_training_data.py      # synthetic labelled datasets
python scripts/train_models.py             # trains + registers both families
python scripts/evaluate_models.py          # head-to-head report (console + JSON)
```

`evaluate_models.py` trains both families on an identical stratified split and
prints a table like:

```
### concept_classifier  (train=577, test=193)
metric               sklearn     pytorch
----------------------------------------
accuracy               0.865       0.881
precision_macro        0.868       0.884
recall_macro           0.865       0.879
f1_macro               0.865       0.878
p95 latency ms          0.37        0.55
  -> winner by macro-F1: pytorch
```

plus clustering quality per demo lecture across all three algorithms. Full
results are written to `models/evaluation_report.json` (and uploaded as a CI
artifact).

> The synthetic training data is deliberately *not* trivially separable, it
> includes shared filler clauses, sentences that carry cues for two classes, and
> a few percent of adjacent-class label noise, so the comparison is meaningful
> rather than a 100% tie.

---

## Setup

### Option A, Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

On first boot the backend container runs migrations, trains the models, and
seeds three demo lectures. Then:

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API + Swagger docs | http://localhost:8000/docs |
| Health | http://localhost:8000/api/health |
| PostgreSQL | localhost:5432 (`lenslab` / `lenslab`) |

### Option B, local dev

**Backend**

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# point at a local Postgres (or use SQLite: export DATABASE_URL=sqlite:///./dev.db)
export DATABASE_URL=postgresql+psycopg2://lenslab:lenslab@localhost:5432/lecturelens
export MODELS_DIR=$PWD/../models UPLOAD_DIR=$PWD/data/uploads

alembic upgrade head
python scripts/build_training_data.py
python scripts/train_models.py
python scripts/seed_demo_data.py
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api -> :8000
```

---

## API endpoints

Interactive docs at `/docs` (Swagger) and `/redoc`. All errors share the shape
`{ "error": { "code": "...", "message": "...", "detail"?: ... } }`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Service + DB + model-version health |
| `POST` | `/api/uploads` | Multipart upload (`course_name`, `lecture_title`, `files[]`); accepts PDF, JPG/PNG, TXT and MD |
| `GET` | `/api/uploads` | List previous uploads |
| `GET` | `/api/uploads/{id}` | Upload / lecture detail |
| `POST` | `/api/analyze/{upload_id}` | Run the full ML pipeline (idempotent) |
| `GET` | `/api/lectures/{id}/concepts` | Concepts with `difficulty` / `concept_type` / `cluster_id` filters and `sort_by` |
| `GET` | `/api/lectures/{id}/clusters` | Clusters + 2-D projection points |
| `GET` | `/api/concepts/{id}` | Concept detail: snippet, source passage, related concepts, prediction history, model versions |
| `POST` | `/api/concepts/{id}/feedback` | Submit classification / difficulty feedback |
| `GET` | `/api/models/metrics` | Model cards, prediction stats, feedback stats |

---

## Database schema

PostgreSQL, managed by Alembic (`backend/alembic/versions/`). Every table has
`created_at` / `updated_at`.

```mermaid
erDiagram
    users ||--o{ lectures : owns
    lectures ||--o{ uploaded_files : has
    lectures ||--o{ text_chunks : has
    lectures ||--o{ concepts : has
    lectures ||--o{ clusters : has
    uploaded_files ||--o{ text_chunks : source
    text_chunks ||--o{ concepts : source
    concepts ||--o{ concept_cluster_links : in
    clusters ||--o{ concept_cluster_links : contains
    concepts ||--o{ predictions : has
    concepts ||--o{ feedback : has
    model_versions ||--o{ predictions : produced
```

| Table | Purpose |
| --- | --- |
| `users` | Implicit demo user (auth is a documented extension point) |
| `lectures` | Course, title, status (`uploaded`/`processing`/`analyzed`/`failed`) |
| `uploaded_files` | File metadata + extracted text + page count |
| `text_chunks` | Cleaned chunks with page/slide/paragraph/section metadata |
| `concepts` | Name, snippet, source, relevance, cached type & difficulty, embedding |
| `clusters` | Label, algorithm, counts, avg difficulty, importance, keywords, centroid |
| `concept_cluster_links` | Many-to-many + `is_representative` flag |
| `predictions` | **Full prediction history** with `model_name` + `model_version` + latency |
| `feedback` | Predicted vs corrected label / difficulty, direction, note, timestamp |
| `model_versions` | Name, family, version, trained_at, metrics JSON, active flag |

---

## Evaluation metrics

| Task | Metrics |
| --- | --- |
| Concept classification | accuracy, macro precision / recall / F1, confusion matrix |
| Difficulty prediction | accuracy, macro precision / recall / F1, confusion matrix |
| Clustering | silhouette score, cluster sizes, mean intra-cluster cosine similarity |
| Inference | mean / p50 / p95 latency (per task, both families) |

Produced by `python scripts/evaluate_models.py` -> console + `models/evaluation_report.json`.

---

## Project layout

```
lecturelens/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI routers (thin)
│   │   ├── core/              # config, logging, exceptions, taxonomy
│   │   ├── db/                # SQLAlchemy models + session
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # orchestration: uploads, analysis, concepts, clusters, feedback, metrics
│   │   └── ml/
│   │       ├── preprocessing/ # extract · clean · chunk
│   │       ├── embeddings/    # TF-IDF + SVD encoder
│   │       ├── classification/# concept extraction + type classifier
│   │       ├── difficulty/    # difficulty features + classifier
│   │       ├── clustering/    # switchable algorithms + labeler
│   │       ├── evaluation/    # metrics + latency
│   │       ├── sklearn_models.py / torch_models.py / registry.py / projection.py
│   ├── alembic/               # migrations
│   ├── scripts/               # build_training_data · train_models · evaluate_models · seed_demo_data · export_feedback
│   ├── data/{training,demo}/  # synthetic labelled data + synthetic demo lectures
│   └── tests/                 # pytest (unit + integration)
├── frontend/
│   └── src/{components,pages,hooks,services,types,lib}/
├── models/                    # model registry (artifacts git-ignored)
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Testing

```bash
# backend
cd backend && pytest -q                      # unit + integration
ruff check app scripts tests

# frontend
cd frontend && npm test                      # Vitest
npm run lint && npm run typecheck && npm run build
```

Backend tests cover preprocessing, concept extraction, difficulty & clustering,
the analyze pipeline, prediction endpoints, feedback storage, invalid uploads,
and a full **upload -> analyze -> dashboard -> feedback -> metrics** integration
test. Frontend tests cover the upload flow, dashboard rendering, concept-table
filters/sorting, and the feedback interaction.

CI (`.github/workflows/ci.yml`) runs backend lint + tests + a train/evaluate
smoke, frontend lint + typecheck + tests + build, and `docker compose build`.

---

## Future work

- Background job queue for analysis (Celery/RQ) instead of a synchronous request
- Real authentication + per-user lecture ownership (schema already supports it)
- Automated retraining from exported feedback with champion/challenger promotion
- Sentence-transformer embeddings as an optional swap for the TF-IDF/SVD encoder
- Layout-aware OCR (tables, multi-column) and non-English language packs
- Spaced-repetition export (Anki) from the study map
- UMAP projection when the dependency is available

---

## Résumé bullets

- Built **LectureLens**, a full-stack ML application (React/TypeScript + FastAPI +
  PostgreSQL, Dockerised with CI) that converts lecture PDFs and notes into a
  structured study map, concept extraction, 7-way concept-type classification,
  Easy/Medium/Hard difficulty estimation, and study clustering, served through a
  typed REST API with an interactive dashboard.
- Engineered an **offline NLP/ML pipeline in PyTorch and scikit-learn** (no LLM
  API): TF-IDF + Truncated-SVD embeddings, noun-phrase/TF-IDF concept mining,
  hand-crafted linguistic features, and a PyTorch MLP benchmarked head-to-head
  against Logistic Regression / Random Forest / Gradient Boosting baselines
  (~0.88 macro-F1) with a dedicated evaluation script reporting accuracy,
  precision/recall/F1, confusion matrices, silhouette scores and p95 latency.
- Designed the system for **ML lifecycle management**: a file-based model
  registry with per-prediction version tracking in Postgres, switchable
  clustering algorithms (KMeans/Agglomerative/DBSCAN) behind one interface, a
  user-feedback loop that exports corrections to a training dataset, and a
  documented heuristic fallback so the service degrades gracefully before models
  are trained.
