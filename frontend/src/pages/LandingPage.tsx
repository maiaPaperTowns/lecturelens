import { Link } from "react-router-dom";

const STEPS = [
  ["01", "Extract & chunk", "PDF, slide and text extraction with page-level metadata preserved."],
  ["02", "Detect concepts", "Noun-phrase and TF-IDF concept mining, then a classifier tags each one."],
  ["03", "Estimate difficulty", "Engineered linguistic features feed sklearn and PyTorch models."],
  ["04", "Cluster & map", "KMeans, Agglomerative or DBSCAN over concept embeddings."],
];

const FEATURES = [
  [
    "Concept classification",
    "Seven academic types: definition, example, theorem or rule, process, comparison, implementation detail, background.",
  ],
  [
    "Difficulty model",
    "A Gradient Boosting baseline benchmarked head to head against a PyTorch MLP, about 0.88 macro F1.",
  ],
  [
    "Feedback loop",
    "Correct a label or a difficulty rating and the correction exports straight into a training dataset.",
  ],
];

export function LandingPage() {
  return (
    <div className="space-y-20">
      {/* Hero */}
      <section className="overflow-hidden rounded-2xl bg-wine-fade text-paper">
        <div className="relative px-6 py-16 sm:px-12 sm:py-20">
          {/* hairline grid */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-25"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(244,239,231,.4) 1px, transparent 1px), linear-gradient(to bottom, rgba(244,239,231,.25) 1px, transparent 1px)",
              backgroundSize: "25% 100%, 100% 33%",
            }}
          />
          <div className="relative mx-auto max-w-3xl text-center">
            <p className="eyebrow text-paper/70">Study-map builder</p>
            <h1 className="mt-5 font-display text-4xl font-normal leading-[1.05] sm:text-6xl">
              A study map that
              <br /> reads your lectures
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-base text-paper/80">
              Upload notes, PDFs or slide decks. LectureLens mines the key concepts, rates how hard
              each one is, groups them into study clusters, and shows you where every concept came
              from. Powered by an offline PyTorch and scikit-learn pipeline, not an LLM API.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link
                to="/upload"
                className="btn rounded-full bg-paper px-6 py-3 text-wine shadow-glass hover:bg-white"
              >
                Upload a lecture
              </Link>
              <Link to="/lectures" className="btn-on-dark">
                Browse the demo
              </Link>
            </div>
          </div>

          {/* frosted-glass stat cards */}
          <div className="relative mx-auto mt-14 grid max-w-3xl gap-3 sm:grid-cols-3">
            {[
              ["120", "concepts detected across 3 demo lectures"],
              ["16", "study clusters, silhouette 0.58 to 0.63"],
              ["0.88", "macro F1, PyTorch vs sklearn"],
            ].map(([n, label]) => (
              <div key={label} className="glass-dark bracket p-4 text-left">
                <p className="font-display text-3xl font-medium text-paper">{n}</p>
                <p className="mt-1 text-xs leading-snug text-paper/75">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section>
        <p className="eyebrow">The pipeline</p>
        <div className="mt-6 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(([n, title, body]) => (
            <div key={n} className="bg-card p-5">
              <span className="font-mono text-xs text-accent-ink">{n}</span>
              <h3 className="mt-2 font-display text-lg text-ink">{title}</h3>
              <p className="mt-1 text-sm text-ink-soft">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section>
        <p className="eyebrow">What it does</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {FEATURES.map(([title, body]) => (
            <div key={title} className="glass p-6">
              <h3 className="font-display text-lg text-ink">{title}</h3>
              <p className="mt-2 text-sm text-ink-soft">{body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
