"""콘텐츠 조회/수정/재생성 엔드포인트."""

import os

from fastapi import APIRouter, HTTPException

from ..db import (
    get_content,
    get_content_gen_params,
    get_content_media_ids,
    get_media_infos,
    get_media_paths,
    list_content,
    save_content,
    update_content_fields,
)
from ..models import GeneratedContent, GeneratePayload, ScriptLine, UpdateContentPayload
from ..services.gemini import generate_draft

router = APIRouter(prefix="/api", tags=["content"])

PUBLIC_BASE = "http://localhost:8000"


def _media_url(path: str) -> str:
    return f"{PUBLIC_BASE}/media/uploads/{os.path.basename(path)}"


def _gen_params(payload: GeneratePayload) -> dict:
    return {
        "keywords": payload.keywords,
        "category": payload.category,
        "contentType": payload.contentType,
        "guideline": payload.guideline,
        "requiredHashtags": payload.requiredHashtags,
        "placeName": payload.placeName,
    }


@router.get("/content", response_model=list[GeneratedContent])
def get_all_content() -> list[GeneratedContent]:
    return list_content()


@router.get("/content/{content_id}", response_model=GeneratedContent)
def get_one(content_id: str) -> GeneratedContent:
    content = get_content(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
    return content


@router.patch("/content/{content_id}", response_model=GeneratedContent)
def update_one(content_id: str, payload: UpdateContentPayload) -> GeneratedContent:
    if get_content(content_id) is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
    update_content_fields(
        content_id, payload.title, payload.body, [s.model_dump() for s in payload.script]
    )
    result = get_content(content_id)
    assert result is not None
    return result


@router.get("/content/{content_id}/settings")
def get_settings(content_id: str) -> dict:
    """상세 페이지의 '생성 설정' 편집기용: 저장된 생성 파라미터 + 미디어(썸네일 URL)."""
    if get_content(content_id) is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
    gp = get_content_gen_params(content_id)
    infos = get_media_infos(get_content_media_ids(content_id))
    return {
        "keywords": gp.get("keywords", []),
        "category": gp.get("category", ""),
        "contentType": gp.get("contentType", "place_review"),
        "guideline": gp.get("guideline", ""),
        "requiredHashtags": gp.get("requiredHashtags", []),
        "placeName": gp.get("placeName", ""),
        "media": [{"mediaId": m["id"], "url": _media_url(m["path"])} for m in infos],
    }


@router.post("/content/{content_id}/regenerate", response_model=GeneratedContent)
def regenerate(content_id: str, payload: GeneratePayload) -> GeneratedContent:
    """수정된 설정/사진으로 AI 재생성 → 같은 콘텐츠를 갱신(발행상태·생성일 유지)."""
    existing = get_content(content_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    paths = [p for (p, _m) in get_media_paths(payload.mediaIds)]
    if not paths and payload.mediaIds:
        raise HTTPException(status_code=404, detail="mediaIds 에 해당하는 파일을 찾을 수 없습니다.")

    draft = generate_draft(
        paths,
        keywords=payload.keywords,
        category=payload.category,
        content_type=payload.contentType,
        guideline=payload.guideline,
        hashtags=payload.requiredHashtags,
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
    updated = GeneratedContent(
        id=existing.id,
        title=draft.get("title", existing.title),
        body=draft.get("body", existing.body),
        videoUrl=existing.videoUrl,
        script=script,
        createdAt=existing.createdAt,
        platformStatus=existing.platformStatus,  # 발행 상태 유지
    )
    save_content(updated, payload.mediaIds, payload.placeName, _gen_params(payload))
    return updated
