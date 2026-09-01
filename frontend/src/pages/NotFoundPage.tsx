import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="card flex flex-col items-center gap-3 p-12 text-center">
      <p className="text-4xl font-bold text-ink-faint">404</p>
      <h1 className="text-lg font-semibold text-ink">Page not found</h1>
      <Link to="/" className="btn-primary">
        Back home
      </Link>
    </div>
  );
}
