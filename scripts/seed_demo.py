"""Populate the SQLite database with demo orders so the UI works without Gmail.

Usage: python scripts/seed_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.db.base import SessionLocal, init_db  # noqa: E402
from api.demo import seed_demo_data  # noqa: E402


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        print(json.dumps(seed_demo_data(db, only_if_empty=False)))
    finally:
        db.close()


if __name__ == "__main__":
    main()
