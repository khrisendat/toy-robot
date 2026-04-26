#!/usr/bin/env python3
"""Remove entries with corrupt embeddings from memory.json."""

import json
import os

import numpy as np

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "..", "memory.json")


def main():
    path = os.path.abspath(MEMORY_PATH)
    if not os.path.exists(path):
        print("No memory.json found — nothing to clean.")
        return

    with open(path) as f:
        entries = json.load(f)

    total = len(entries)
    clean = [
        e for e in entries
        if np.isfinite(np.array(e["embedding"], dtype=np.float32)).all()
    ]
    removed = total - len(clean)

    if removed == 0:
        print(f"All {total} entries are valid — nothing to remove.")
        return

    with open(path, "w") as f:
        json.dump(clean, f)

    print(f"Removed {removed} corrupt entr{'y' if removed == 1 else 'ies'}. {len(clean)}/{total} kept.")


if __name__ == "__main__":
    main()
