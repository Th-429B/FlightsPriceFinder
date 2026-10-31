import csv
import os
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / os.environ.get("FPF_HISTORY_FILE", "data/history.csv")
FIELDS = ["run_date", "start", "end", "depart", "return", "total", "currency"]


def load() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    with HISTORY_FILE.open(newline="") as f:
        return list(csv.DictReader(f))


def append(rows: list[dict]):
    """Add today's rows, replacing any earlier rows from the same run_date
    and route (so re-runs don't create duplicates)."""
    if not rows:
        return
    replaced_keys = {(r["run_date"], r["start"], r["end"], r["depart"], r["return"]) for r in rows}
    kept = [
        r for r in load()
        if (r["run_date"], r["start"], r["end"], r["depart"], r["return"]) not in replaced_keys
    ]
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    with HISTORY_FILE.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(kept + rows)


def for_route(start: str, end: str) -> list[dict]:
    return [r for r in load() if r["start"] == start and r["end"] == end]
