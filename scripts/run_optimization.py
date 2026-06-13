#!/usr/bin/env python3
"""CLI: run autonomous optimization loop."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.logging_config import setup_logging
from src.models import Strategy, get_session_factory, init_db
from src.services.optimizer import OptimizerService


def main():
    setup_logging()
    init_db()
    parser = argparse.ArgumentParser(description="Run grid or genetic optimization")
    parser.add_argument("--strategy-id", type=int, default=1)
    parser.add_argument("--symbol", default="BOVAX125")
    parser.add_argument("--method", choices=["grid", "genetic"], default="grid")
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        strategy = session.get(Strategy, args.strategy_id)
        if not strategy:
            print(f"Strategy {args.strategy_id} not found")
            sys.exit(1)
        svc = OptimizerService(session)
        if args.method == "genetic":
            run = svc.run_genetic_search(
                strategy,
                args.symbol,
                {"stop_ticks": (2.0, 10.0), "target_ticks": (4.0, 15.0)},
            )
        else:
            run = svc.run_grid_search(
                strategy,
                args.symbol,
                {"stop_ticks": [3, 5, 7], "target_ticks": [6, 8, 10]},
            )
        print(f"Optimization {run.id} — {run.status}")
        print(f"Best params: {run.best_parameters}")
        print(f"Best metrics: {run.best_metrics}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
