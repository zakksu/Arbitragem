#!/usr/bin/env bash
# Start Arbitragem locally — API + Dashboard
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

export PYTHONPATH="$ROOT"
export API_BASE_URL="http://localhost:8000/api/v1"

echo "Starting API on http://localhost:8000 ..."
.venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

sleep 2
echo "Starting Dashboard on http://localhost:8501 ..."
.venv/bin/streamlit run dashboard/app.py --server.port 8501 &
UI_PID=$!

echo ""
echo "Arbitragem running:"
echo "  Dashboard: http://localhost:8501"
echo "  API docs:  http://localhost:8000/docs"
echo "Press Ctrl+C to stop."

trap "kill $API_PID $UI_PID 2>/dev/null" EXIT
wait
