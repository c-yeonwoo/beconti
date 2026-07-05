"""업로드 파일 저장 + media 레지스트리."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from ..config import settings
from ..db import insert_media


def _ext(filename: str) -> str:
    suffix = Path(filename or "").suffix
    return suffix if len(suffix) <= 10 else ""


async def save_uploads(files: list[UploadFile]) -> list[str]:
    """파일들을 data/uploads 에 저장하고 media_id 목록을 반환."""
    settings.ensure_dirs()
    media_ids: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for f in files:
        media_id = uuid.uuid4().hex
        dest = settings.upload_dir / f"{media_id}{_ext(f.filename or '')}"
        contents = await f.read()
        dest.write_bytes(contents)
        insert_media(
            media_id=media_id,
            path=str(dest),
            filename=f.filename or dest.name,
            mime=f.content_type or "",
            created_at=now,
        )
        media_ids.append(media_id)

    return media_ids
