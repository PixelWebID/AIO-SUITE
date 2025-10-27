"""SQLite-backed persistence helpers for article history and activity logs."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import aiosqlite

from ..config import settings

_INIT_LOCK = asyncio.Lock()
_INITIALISED = False


def _resolve_database_path() -> Path:
    """Translate DATABASE_URL into an absolute sqlite path."""

    db_url = settings.database_url
    if not db_url:
        base = Path(os.getcwd()) / "data"
        base.mkdir(parents=True, exist_ok=True)
        return base / "aio_content.sqlite3"

    if db_url.startswith("sqlite:///"):
        path = Path(db_url.replace("sqlite:///", "", 1))
    elif db_url.startswith("file:"):
        path = Path(db_url.replace("file:", "", 1))
    else:
        raise ValueError("Only sqlite database URLs are supported by the default driver.")

    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH = _resolve_database_path()


async def _initialise() -> None:
    """Create database schema if missing."""

    global _INITIALISED
    if _INITIALISED:
        return

    async with _INIT_LOCK:
        if _INITIALISED:
            return

        async with aiosqlite.connect(DB_PATH) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute("PRAGMA journal_mode = WAL;")
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS article_history (
                    id TEXT PRIMARY KEY,
                    keyword TEXT NOT NULL,
                    geo TEXT,
                    tone TEXT,
                    language TEXT,
                    created_at TEXT NOT NULL,
                    article_html TEXT NOT NULL,
                    meta_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    sources_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS article_simhash (
                    history_id TEXT NOT NULL REFERENCES article_history(id) ON DELETE CASCADE,
                    simhash TEXT NOT NULL,
                    sha1 TEXT NOT NULL,
                    sha256 TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS gap_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    response_json TEXT NOT NULL
                );
                """
            )
            await conn.commit()

        _INITIALISED = True


async def get_connection() -> aiosqlite.Connection:
    """
    Return an aiosqlite connection.

    Callers are responsible for closing the connection.
    """

    await _initialise()
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _serialize(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


async def record_activity(category: str, payload: Dict[str, Any], *, level: str = "info") -> None:
    """Persist an activity event and optionally echo it to stdout."""

    await _initialise()
    now = datetime.now(timezone.utc).isoformat()

    async with await get_connection() as conn:
        await conn.execute(
            "INSERT INTO activity_log (occurred_at, level, category, payload_json) VALUES (?, ?, ?, ?)",
            (now, level, category, _serialize(payload)),
        )
        await conn.commit()

    if settings.activity_log_console:
        print(f"[activity] {now} {level.upper()} {category}: {payload}")


async def prune_history(retention_days: Optional[int] = None) -> None:
    """Remove old history entries beyond the retention window."""

    await _initialise()
    days = retention_days if retention_days is not None else settings.history_retention_days
    if days <= 0:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    async with await get_connection() as conn:
        await conn.execute("DELETE FROM article_history WHERE created_at < ?", (cutoff_iso,))
        await conn.commit()


async def log_generation_job(payload: Any, response: Any) -> str:
    """Persist metadata about a generation job and return the history identifier."""

    await _initialise()

    history_id = getattr(response, "history_id", None) or secrets.token_hex(12)
    if hasattr(response, "history_id"):
        response.history_id = history_id  # type: ignore[attr-defined]

    meta = response.meta.dict() if hasattr(response.meta, "dict") else response.meta
    metrics = response.metrics.dict() if hasattr(response.metrics, "dict") else response.metrics
    sources = [source.dict() if hasattr(source, "dict") else dict(source) for source in response.sources]

    async with await get_connection() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO article_history (
                id, keyword, geo, tone, language, created_at, article_html,
                meta_json, metrics_json, sources_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                getattr(payload, "keyword", None),
                getattr(payload, "geo", None),
                getattr(payload, "tone", None),
                getattr(payload, "target_language", None),
                datetime.now(timezone.utc).isoformat(),
                response.article_html,
                _serialize(meta),
                _serialize(metrics),
                _serialize(sources),
            ),
        )

        signatures = metrics if isinstance(metrics, dict) else {}
        await conn.execute(
            """
            INSERT OR REPLACE INTO article_simhash (history_id, simhash, sha1, sha256)
            VALUES (?, ?, ?, ?)
            """,
            (
                history_id,
                signatures.get("simhash"),
                signatures.get("checksum_sha1"),
                signatures.get("checksum_sha256"),
            ),
        )

        await conn.commit()

    await record_activity(
        "article.generated",
        {
            "history_id": history_id,
            "keyword": getattr(payload, "keyword", None),
            "geo": getattr(payload, "geo", None),
            "tone": getattr(payload, "tone", None),
        },
    )
    await prune_history()
    return history_id


async def log_gap_job(payload: Any, response: Any, *, trends: Iterable[str] = ()) -> None:
    """Persist metadata about a content gap analysis job."""

    await _initialise()

    async with await get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO gap_jobs (keyword, created_at, response_json) VALUES (?, ?, ?)
            """,
            (
                getattr(payload, "keyword", None),
                datetime.now(timezone.utc).isoformat(),
                _serialize(
                    {
                        "response": response.dict() if hasattr(response, "dict") else response,
                        "trends": list(trends),
                    }
                ),
            ),
        )
        await conn.commit()

    await record_activity(
        "analysis.gap",
        {
            "keyword": getattr(payload, "keyword", None),
            "competitors": getattr(payload, "competitors", []),
        },
    )


async def fetch_recent_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent article history entries."""

    await _initialise()
    async with await get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM article_history ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
    history: List[Dict[str, Any]] = []
    for row in rows:
        history.append(
            {
                "id": row["id"],
                "keyword": row["keyword"],
                "geo": row["geo"],
                "tone": row["tone"],
                "language": row["language"],
                "created_at": row["created_at"],
                "meta": json.loads(row["meta_json"]),
                "metrics": json.loads(row["metrics_json"]),
                "sources": json.loads(row["sources_json"]),
            }
        )
    return history


async def fetch_history_item(history_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single article history record."""

    await _initialise()
    async with await get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM article_history WHERE id = ?", (history_id,)
        )
        row = await cursor.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "keyword": row["keyword"],
        "geo": row["geo"],
        "tone": row["tone"],
        "language": row["language"],
        "created_at": row["created_at"],
        "article_html": row["article_html"],
        "meta": json.loads(row["meta_json"]),
        "metrics": json.loads(row["metrics_json"]),
        "sources": json.loads(row["sources_json"]),
    }


async def fetch_recent_simhashes(limit: int = 100) -> List[Dict[str, str]]:
    """Return a set of previously generated simhash signatures for duplication checks."""

    await _initialise()
    async with await get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """
            SELECT history_id, simhash FROM article_simhash
            ORDER BY rowid DESC LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    return [{"history_id": row["history_id"], "simhash": row["simhash"]} for row in rows]


async def fetch_activity(limit: int = 50) -> List[Dict[str, Any]]:
    """Return the most recent activity log entries."""

    await _initialise()
    async with await get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """
            SELECT occurred_at, level, category, payload_json
            FROM activity_log
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    return [
        {
            "occurred_at": row["occurred_at"],
            "level": row["level"],
            "category": row["category"],
            "payload": json.loads(row["payload_json"]),
        }
        for row in rows
    ]
