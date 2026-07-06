"""Histórico local de operações em SQLite — base da Etapa 9.

Guarda apenas METADADOS de operações (tipo, origem, saídas, status) — nunca o
conteúdo dos documentos (Seção 14). `init` é idempotente; o arquivo fica na
área de dados do app (paths.database_path).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.infrastructure.paths import database_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    job_type TEXT NOT NULL,
    source_file TEXT,
    outputs_json TEXT,
    status TEXT NOT NULL,
    detail TEXT
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path or database_path()))
    conn.execute(_SCHEMA)
    return conn


def record_operation(job_type: str, source_file: str | None, outputs: list[str],
                     status: str, detail: str = "",
                     db_path: Path | None = None) -> None:
    conn = _connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO operations "
                "(created_at, job_type, source_file, outputs_json, status, detail) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(UTC).isoformat(),
                    job_type,
                    source_file,
                    json.dumps(outputs, ensure_ascii=False),
                    status,
                    detail,
                ),
            )
    finally:
        conn.close()


def list_operations(limit: int = 100, db_path: Path | None = None) -> list[dict]:
    conn = _connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM operations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
