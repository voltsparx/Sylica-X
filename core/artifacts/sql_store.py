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
    conn = sqlite3.connect(path)
    try:
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments (
                run_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                details_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ocr_items (
                run_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                source_kind TEXT,
                ocr_engine TEXT,
                confidence_hint TEXT,
                text_excerpt TEXT,
                signals_json TEXT NOT NULL,
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
        run_id = int(cursor.lastrowid or 0)

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
        for kind, key in (("plugin", "selected_plugins"), ("filter", "selected_filters"), ("module", "attached_modules")):
            raw_value = payload.get(key)
            if kind == "module":
                rows = raw_value if isinstance(raw_value, list) else []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    conn.execute(
                        """
                        INSERT INTO attachments(run_id, kind, name, details_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            kind,
                            str(row.get("id", "module")),
                            json.dumps(row, indent=2, default=str),
                        ),
                    )
                continue
            names = raw_value if isinstance(raw_value, list) else []
            for name in names:
                conn.execute(
                    """
                    INSERT INTO attachments(run_id, kind, name, details_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        kind,
                        str(name),
                        json.dumps({"name": str(name)}, indent=2, default=str),
                    ),
                )
        ocr_scan = payload.get("ocr_scan", {}) if isinstance(payload.get("ocr_scan"), dict) else {}
        ocr_items = ocr_scan.get("items", []) if isinstance(ocr_scan.get("items"), list) else []
        for item in ocr_items:
            if not isinstance(item, dict):
                continue
            conn.execute(
                """
                INSERT INTO ocr_items(run_id, source, source_kind, ocr_engine, confidence_hint, text_excerpt, signals_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(item.get("source", "image")),
                    str(item.get("source_kind", "")),
                    str(item.get("ocr_engine", "")),
                    str(item.get("confidence_hint", "")),
                    str(item.get("normalized_text", "") or item.get("raw_text", ""))[:4000],
                    json.dumps(item.get("signals", {}), indent=2, default=str),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    return str(path)
