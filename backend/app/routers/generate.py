import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..db import get_media_paths, save_content
from ..models import GeneratePayload, GeneratedContent, default_platform_status
from ..services.gemini import generate_blog

router = APIRouter(prefix="/api", tags=["generate"])

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


def media_has_video(paths: list[tuple[str, str]]) -> bool:
    """(path, mime) 목록에 영상이 하나라도 있으면 True."""
    return any(
        (mime or "").startswith("video/") or Path(p).suffix.lower() in VIDEO_EXTS
        for p, mime in paths
    )


def gen_params(payload: GeneratePayload) -> dict:
    """생성 설정을 DB 저장용 dict 로. guideline(구) → blogGuideline 하위호환 매핑."""
    blog_g = payload.blogGuideline or payload.guideline
    return {
        "keywords": payload.keywords,
        "category": payload.category,
        "contentType": payload.contentType,
        "blogGuideline": blog_g,
        "shortsGuideline": payload.shortsGuideline,
        "requiredHashtags": payload.requiredHashtags,
        "placeName": payload.placeName,
        "placeUrl": payload.placeUrl,
        "scriptStyle": payload.scriptStyle,
        "captionStyle": payload.captionStyle,
    }


@router.post("/generate", response_model=GeneratedContent)
def generate(payload: GeneratePayload) -> GeneratedContent:
    """블로그 글을 생성한다(메인). 숏폼 대본은 상세 페이지에서 별도로 생성."""
    paths = get_media_paths(payload.mediaIds)
    if not paths and payload.mediaIds:
        raise HTTPException(status_code=404, detail="mediaIds 에 해당하는 업로드 파일을 찾을 수 없습니다.")

    image_paths = [p for (p, _mime) in paths]
    draft = generate_blog(
        image_paths,
        keywords=payload.keywords,
        category=payload.category,
        content_type=payload.contentType,
        guideline=payload.blogGuideline or payload.guideline,
        hashtags=payload.requiredHashtags,
    )

    content = GeneratedContent(
        id=uuid.uuid4().hex,
        title=draft.get("title", ""),
        body=draft.get("body", ""),
        videoUrl=None,
        script=[],  # 숏폼은 옵셔널 — 상세에서 생성
        createdAt=datetime.now(timezone.utc).isoformat(),
        platformStatus=default_platform_status(),
    )
    save_content(content, payload.mediaIds, payload.placeName, gen_params(payload))
    return content
