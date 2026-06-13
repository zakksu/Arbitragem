#!/usr/bin/env bash
# Arbitragem — autonomous dev launcher (Linux/Mac)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

case "${1:-start}" in
  stop)    exec "$PY" scripts/dev.py stop ;;
  status)  exec "$PY" scripts/dev.py status ;;
  setup)   exec "$PY" scripts/dev.py setup ;;
  restart) exec "$PY" scripts/dev.py restart --wait "${@:2}" ;;
  open)    exec "$PY" scripts/dev.py open ;;
  start)   exec "$PY" scripts/dev.py start --wait --open ;;
  *)       exec "$PY" scripts/dev.py "$@" ;;
esac
