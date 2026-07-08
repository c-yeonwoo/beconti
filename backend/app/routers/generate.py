import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..db import get_media_paths, save_content
from ..models import GeneratePayload, GeneratedContent, ScriptLine, default_platform_status
from ..services.gemini import generate_draft

router = APIRouter(prefix="/api", tags=["generate"])

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


def media_has_video(paths: list[tuple[str, str]]) -> bool:
    """(path, mime) 목록에 영상이 하나라도 있으면 True."""
    return any(
        (mime or "").startswith("video/") or Path(p).suffix.lower() in VIDEO_EXTS
        for p, mime in paths
    )


@router.post("/generate", response_model=GeneratedContent)
def generate(payload: GeneratePayload) -> GeneratedContent:
    paths = get_media_paths(payload.mediaIds)
    if not paths and payload.mediaIds:
        raise HTTPException(status_code=404, detail="mediaIds 에 해당하는 업로드 파일을 찾을 수 없습니다.")

    image_paths = [p for (p, _mime) in paths]
    draft = generate_draft(
        image_paths,
        keywords=payload.keywords,
        category=payload.category,
        content_type=payload.contentType,
        guideline=payload.guideline,
        hashtags=payload.requiredHashtags,
        has_video=media_has_video(paths),
        script_style=payload.scriptStyle,
    )

    script = [
        ScriptLine(
            time=str(line.get("time", "")),
            caption=str(line.get("caption", "")),
            narration=str(line.get("narration", "")),
        )
        for line in draft.get("script", [])
        if isinstance(line, dict)
    ]

    content = GeneratedContent(
        id=uuid.uuid4().hex,
        title=draft.get("title", ""),
        body=draft.get("body", ""),
        videoUrl=None,
        script=script,
        createdAt=datetime.now(timezone.utc).isoformat(),
        platformStatus=default_platform_status(),
    )
    save_content(content, payload.mediaIds, payload.placeName, _gen_params(payload))
    return content


def _gen_params(payload: GeneratePayload) -> dict:
    return {
        "keywords": payload.keywords,
        "category": payload.category,
        "contentType": payload.contentType,
        "guideline": payload.guideline,
        "requiredHashtags": payload.requiredHashtags,
        "placeName": payload.placeName,
        "placeUrl": payload.placeUrl,
        "scriptStyle": payload.scriptStyle,
    }
