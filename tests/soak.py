#!/usr/bin/env python
"""Per-game soak test: runs N full games, catches all exceptions, prints
SUMMARY: X/N succeeded, Y failed and lists the first few unique tracebacks.

Usage:
    python tests/soak.py [N] [--workers W]

By default runs serially. Pass --workers W to fan games out across W
processes (each worker initializes its own card DB once). Each game is
independent so this is embarrassingly parallel — a typical box cuts
wall time ~Wx.
"""
import argparse
import os
import sys
import traceback
from collections import Counter
from multiprocessing import Pool

from fireplace import cards
from fireplace.exceptions import GameOver
from fireplace.utils import play_full_game


def _run_one(_index: int) -> tuple[bool, str, str]:
    """Run a single game. Returns (ok, exc_key, traceback_text)."""
    try:
        play_full_game()
        return (True, "", "")
    except GameOver:
        return (True, "", "")
    except Exception as e:
        key = f"{type(e).__name__}: {e}"
        return (False, key, traceback.format_exc())


def _worker_init():
    """Initialize card DB once per worker process."""
    # Soak only cares about crashes, not gameplay logs — silence the verbose
    # per-action logging so the run is fast and the output file stays small.
    import logging
    logging.disable(logging.CRITICAL)
    cards.db.initialize()


def main(numgames: int, workers: int) -> int:
    import logging
    logging.disable(logging.CRITICAL)
    cards.db.initialize()
    failures: Counter[str] = Counter()
    sample: dict[str, str] = {}
    ok = 0

    if workers <= 1:
        results = (_run_one(i) for i in range(numgames))
    else:
        # `chunksize` keeps per-task IPC cheap; tasks are O(seconds) each
        # so a small chunksize is fine and gives smoother load balancing.
        pool = Pool(processes=workers, initializer=_worker_init)
        results = pool.imap_unordered(_run_one, range(numgames), chunksize=4)

    for success, key, tb in results:
        if success:
            ok += 1
        else:
            failures[key] += 1
            if key not in sample:
                sample[key] = tb

    print(f"SUMMARY: {ok}/{numgames} succeeded, {numgames - ok} failed")
    for key, count in failures.most_common():
        print(f"  [{count:3d}] {key}")
        for line in sample[key].splitlines():
            line = line.strip()
            if line.startswith("File ") or line.startswith(key.split(":")[0]):
                print(f"  {line}")
        print(f"--- {key} ---")
        print(sample[key])
    return 0 if not failures else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Per-game soak test for fireplace.")
    parser.add_argument(
        "numgames", nargs="?", type=int, default=100, help="number of games to run"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="parallel worker processes (default 1 = serial). "
        "Pass e.g. --workers %d for one per core." % (os.cpu_count() or 1),
    )
    args = parser.parse_args()
    sys.exit(main(args.numgames, args.workers))
