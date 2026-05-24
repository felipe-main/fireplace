#!/usr/bin/env python
"""Per-game soak test: runs N full games, catches all exceptions, prints
SUMMARY: X/N succeeded, Y failed and lists the first few unique tracebacks.
"""
import sys
import traceback
from collections import Counter

from fireplace import cards
from fireplace.exceptions import GameOver
from fireplace.utils import play_full_game


def main(numgames: int) -> int:
    cards.db.initialize()
    failures: Counter[str] = Counter()
    sample: dict[str, str] = {}
    ok = 0
    for i in range(numgames):
        try:
            play_full_game()
            ok += 1
        except GameOver:
            ok += 1
        except Exception as e:
            key = f"{type(e).__name__}: {e}"
            failures[key] += 1
            if key not in sample:
                sample[key] = traceback.format_exc()
    print(f"SUMMARY: {ok}/{numgames} succeeded, {numgames - ok} failed")
    for key, count in failures.most_common():
        print(f"  [{count:3d}] {key}")
        # Print the first short traceback for each unique failure.
        for line in sample[key].splitlines():
            line = line.strip()
            if line.startswith("File ") or line.startswith(key.split(":")[0]):
                print(f"  {line}")
        print(f"--- {key} ---")
        print(sample[key])
    return 0 if not failures else 1


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    sys.exit(main(n))
