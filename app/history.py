import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(
    os.environ.get(
        "QUERYFORGE_HISTORY_DB",
        "/code/data/benchmarks.sqlite3"
    )
)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            rows_per_database INTEGER NOT NULL,
            repetitions INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        )
    """)

    return conn


def save_experiment(payload, repetitions):
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO experiments
            (created_at, rows_per_database, repetitions, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                payload["rows_per_database"],
                repetitions,
                json.dumps(payload)
            )
        )
        return cursor.lastrowid


def list_experiments(limit=25):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, rows_per_database, repetitions
            FROM experiments
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [dict(row) for row in rows]


def get_experiment(experiment_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM experiments WHERE id = ?",
            (experiment_id,)
        ).fetchone()

        if row is None:
            return None

        result = json.loads(row["payload_json"])
        result["experiment_id"] = row["id"]
        result["created_at"] = row["created_at"]
        result["repetitions"] = row["repetitions"]

        return result