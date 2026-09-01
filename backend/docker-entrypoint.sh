#!/usr/bin/env bash
# Backend container startup:
#   1. wait for Postgres
#   2. run migrations
#   3. train models if no artifacts exist yet (heuristic fallback works regardless)
#   4. seed demo lectures (idempotent)
#   5. exec the CMD (uvicorn)
set -euo pipefail

echo "[entrypoint] waiting for database ..."
python - <<'PY'
import os, time
import sqlalchemy as sa

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        sa.create_engine(url).connect().close()
        print("[entrypoint] database is up")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] db not ready ({attempt+1}/30): {exc}")
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] database never became available")
PY

echo "[entrypoint] running migrations ..."
alembic upgrade head

if [ ! -f "${MODELS_DIR:-/models}/concept_classifier/metadata.json" ]; then
  echo "[entrypoint] no trained models found - training now ..."
  python scripts/build_training_data.py
  python scripts/train_models.py || echo "[entrypoint] training failed; heuristic models will be used"
fi

echo "[entrypoint] seeding demo data ..."
python scripts/seed_demo_data.py || echo "[entrypoint] seeding skipped/failed (non-fatal)"

echo "[entrypoint] starting: $*"
exec "$@"
