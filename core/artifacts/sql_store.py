# ──────────────────────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
# ──────────────────────────────────────────────────────────────────────────────

"""SQLite artifact storage for full scan payloads."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def write_sqlite_report(path: Path, payload: dict[str, Any]) -> str:
    """Persist the full run payload to a SQLite database file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                mode TEXT NOT NULL,
                generated_at_utc TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS findings (
                run_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                identifier TEXT NOT NULL,
                severity TEXT,
                summary TEXT,
                data_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
            """
        )
        generated_at = str((payload.get("metadata") or {}).get("generated_at_utc") or "")
        summary_json = json.dumps(payload.get("summary", {}), indent=2, default=str)
        payload_json = json.dumps(payload, indent=2, default=str)
        cursor = conn.execute(
            """
            INSERT INTO runs(target, mode, generated_at_utc, summary_json, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(payload.get("target", "")),
                str((payload.get("metadata") or {}).get("mode", "profile")),
                generated_at,
                summary_json,
                payload_json,
            ),
        )
        run_id = int(cursor.lastrowid)

        def _insert_rows(kind: str, rows: list[dict[str, Any]], identifier_key: str, summary_key: str) -> None:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                conn.execute(
                    """
                    INSERT INTO findings(run_id, kind, identifier, severity, summary, data_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        kind,
                        str(row.get(identifier_key, row.get("id", kind))),
                        str(row.get("severity", "")),
                        str(row.get(summary_key, row.get("title", ""))),
                        json.dumps(row, indent=2, default=str),
                    ),
                )

        _insert_rows("result", list(payload.get("results", []) or []), "platform", "context")
        _insert_rows("issue", list(payload.get("issues", []) or []), "title", "recommendation")
        _insert_rows("plugin", list(payload.get("plugins", []) or []), "id", "summary")
        _insert_rows("filter", list(payload.get("filters", []) or []), "id", "summary")
        conn.commit()

    return str(path)
