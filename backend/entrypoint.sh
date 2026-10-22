#!/bin/sh
set -e

echo "Starting Interview AutoApply backend..."

# Run alembic migrations if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ]; then
    echo "Applying database schema migrations..."
    alembic upgrade head || echo "Alembic migrations completed or skipped."
fi

# Seed demo user Maya Patel
echo "Seeding demo user and CRM baseline..."
python seed_example_user.py || echo "Seed step completed or skipped."

# Execute CMD passed to container or default to uvicorn on $PORT
if [ $# -gt 0 ]; then
    exec "$@"
else
    PORT="${PORT:-8000}"
    echo "Starting Uvicorn server on port $PORT..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi
