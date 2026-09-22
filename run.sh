#!/usr/bin/env bash
# Aus Gov Data Explorer - Unified Development Runner
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "================================================="
echo "   Starting Aus Gov Data Explorer"
echo "================================================="

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3.11 -m venv .venv
    .venv/bin/pip install -r backend/requirements.txt
fi

# Check database
if [ ! -f "backend/data/aus_labour_force.db" ]; then
    echo "Ingesting ABS Labour Force dataset..."
    PYTHONPATH=. .venv/bin/python backend/data_ingest.py
fi

echo "Starting Backend API on http://127.0.0.1:8001..."
PYTHONPATH=. .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

echo "Starting Frontend on http://localhost:3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!

cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
