"""가벼운 SQLite 영속화 계층 (stdlib sqlite3).

콘텐츠(생성 결과)와 미디어 등록 정보를 저장한다.
JSON blob 컬럼으로 script / platformStatus 를 담아 단순하게 유지.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings
from .models import GeneratedContent, default_platform_status


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    settings.ensure_dirs()
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS media (
                id          TEXT PRIMARY KEY,
                path        TEXT NOT NULL,
                filename    TEXT NOT NULL,
                mime        TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS content (
                id               TEXT PRIMARY KEY,
                title            TEXT NOT NULL,
                body             TEXT NOT NULL,
                video_url        TEXT,
                script_json      TEXT NOT NULL DEFAULT '[]',
                platform_json    TEXT NOT NULL DEFAULT '{}',
                media_ids_json   TEXT NOT NULL DEFAULT '[]',
                created_at       TEXT NOT NULL
            );
            """
        )


# ─── media ────────────────────────────────────────────────────────
def insert_media(media_id: str, path: str, filename: str, mime: str, created_at: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO media (id, path, filename, mime, created_at) VALUES (?,?,?,?,?)",
            (media_id, path, filename, mime, created_at),
        )


def get_media_paths(media_ids: list[str]) -> list[tuple[str, str]]:
    """(path, mime) 목록을 media_ids 순서대로 반환. 없는 id 는 건너뜀."""
    if not media_ids:
        return []
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in media_ids)
        rows = conn.execute(
            f"SELECT id, path, mime FROM media WHERE id IN ({placeholders})",
            media_ids,
        ).fetchall()
    by_id = {r["id"]: (r["path"], r["mime"] or "") for r in rows}
    return [by_id[mid] for mid in media_ids if mid in by_id]


# ─── content ──────────────────────────────────────────────────────
def _row_to_content(row: sqlite3.Row) -> GeneratedContent:
    return GeneratedContent(
        id=row["id"],
        title=row["title"],
        body=row["body"],
        videoUrl=row["video_url"],
        script=json.loads(row["script_json"]),
        createdAt=row["created_at"],
        platformStatus=json.loads(row["platform_json"]) or default_platform_status(),
    )


def save_content(content: GeneratedContent, media_ids: list[str]) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO content
               (id, title, body, video_url, script_json, platform_json, media_ids_json, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                content.id,
                content.title,
                content.body,
                content.videoUrl,
                json.dumps([s.model_dump() for s in content.script], ensure_ascii=False),
                json.dumps(content.platformStatus, ensure_ascii=False),
                json.dumps(media_ids, ensure_ascii=False),
                content.createdAt,
            ),
        )


def get_content(content_id: str) -> GeneratedContent | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM content WHERE id = ?", (content_id,)).fetchone()
    return _row_to_content(row) if row else None


def get_content_media_ids(content_id: str) -> list[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT media_ids_json FROM content WHERE id = ?", (content_id,)
        ).fetchone()
    return json.loads(row["media_ids_json"]) if row else []


def list_content(limit: int = 50) -> list[GeneratedContent]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM content ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_content(r) for r in rows]


def update_video_url(content_id: str, url: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE content SET video_url = ? WHERE id = ?", (url, content_id))


def update_platform_status(content_id: str, platform: str, status: str) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT platform_json FROM content WHERE id = ?", (content_id,)
        ).fetchone()
        if not row:
            return
        platform_status = json.loads(row["platform_json"]) or default_platform_status()
        platform_status[platform] = status
        conn.execute(
            "UPDATE content SET platform_json = ? WHERE id = ?",
            (json.dumps(platform_status, ensure_ascii=False), content_id),
        )
