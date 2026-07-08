"""콘텐츠 조회/수정/삭제/재생성 엔드포인트."""

import os

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..db import (
    delete_content,
    get_content,
    get_content_gen_params,
    get_content_media_ids,
    get_media_infos,
    get_media_paths,
    list_content,
    save_content,
    update_content_fields,
    update_content_script,
)
from ..models import GeneratedContent, GeneratePayload, ScriptLine, UpdateContentPayload
from ..services.gemini import default_guideline, generate_blog, generate_script
from .generate import gen_params

router = APIRouter(prefix="/api", tags=["content"])

PUBLIC_BASE = "http://localhost:8000"


def _media_url(path: str) -> str:
    return f"{PUBLIC_BASE}/media/uploads/{os.path.basename(path)}"


def _script_models(raw: list) -> list[ScriptLine]:
    return [
        ScriptLine(
            time=str(line.get("time", "")),
            caption=str(line.get("caption", "")),
            narration=str(line.get("narration", "")),
        )
        for line in raw
        if isinstance(line, dict)
    ]


@router.get("/defaults")
def get_defaults() -> dict:
    """유형별 기본 가이드라인 (프론트 placeholder 용)."""
    return {"blog": default_guideline("place_review"), "video": default_guideline("vlog")}


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


@router.delete("/content/{content_id}")
def remove_one(content_id: str) -> dict:
    """콘텐츠 삭제 + 렌더된 숏폼 파일 정리."""
    if not delete_content(content_id):
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
    try:
        mp4 = settings.render_dir / f"shortform_{content_id}.mp4"
        if mp4.exists():
            mp4.unlink()
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


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
        # 하위호환: 예전 guideline 은 blogGuideline 로 노출
        "blogGuideline": gp.get("blogGuideline", gp.get("guideline", "")),
        "shortsGuideline": gp.get("shortsGuideline", ""),
        "requiredHashtags": gp.get("requiredHashtags", []),
        "placeName": gp.get("placeName", ""),
        "placeUrl": gp.get("placeUrl", ""),
        "scriptStyle": gp.get("scriptStyle", "polite"),
        "captionStyle": gp.get("captionStyle", "basic"),
        "media": [{"mediaId": m["id"], "url": _media_url(m["path"])} for m in infos],
    }


@router.post("/content/{content_id}/regenerate-blog", response_model=GeneratedContent)
def regenerate_blog(content_id: str, payload: GeneratePayload) -> GeneratedContent:
    """블로그 글(제목·본문)만 재생성. 숏폼 대본은 그대로 유지."""
    existing = get_content(content_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    paths = [p for (p, _m) in get_media_paths(payload.mediaIds)]
    if not paths and payload.mediaIds:
        raise HTTPException(status_code=404, detail="mediaIds 에 해당하는 파일을 찾을 수 없습니다.")

    draft = generate_blog(
        paths,
        keywords=payload.keywords,
        category=payload.category,
        content_type=payload.contentType,
        guideline=payload.blogGuideline or payload.guideline,
        hashtags=payload.requiredHashtags,
    )
    updated = GeneratedContent(
        id=existing.id,
        title=draft.get("title", existing.title),
        body=draft.get("body", existing.body),
        videoUrl=existing.videoUrl,
        script=existing.script,  # 대본 유지
        createdAt=existing.createdAt,
        platformStatus=existing.platformStatus,
    )
    save_content(updated, payload.mediaIds, payload.placeName, gen_params(payload))
    return updated


@router.post("/content/{content_id}/regenerate-script", response_model=GeneratedContent)
def regenerate_script(content_id: str, payload: GeneratePayload) -> GeneratedContent:
    """숏폼 대본만 (재)생성. 블로그 글은 그대로 유지. 영상 없으면 400."""
    existing = get_content(content_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    video_paths = [p for (p, _m) in get_media_paths(payload.mediaIds)]
    result = generate_script(
        video_paths,
        keywords=payload.keywords,
        guideline=payload.shortsGuideline,
        script_style=payload.scriptStyle,
    )
    script = _script_models(result.get("script", []))
    if not script:
        raise HTTPException(
            status_code=400, detail="숏폼 대본을 만들 영상이 없습니다. 영상을 업로드하세요."
        )
    update_content_script(content_id, [s.model_dump() for s in script])
    # 설정도 갱신 저장(대본 스타일/가이드라인 유지용)
    save_content(
        GeneratedContent(
            id=existing.id, title=existing.title, body=existing.body,
            videoUrl=existing.videoUrl, script=script,
            createdAt=existing.createdAt, platformStatus=existing.platformStatus,
        ),
        payload.mediaIds, payload.placeName, gen_params(payload),
    )
    result_content = get_content(content_id)
    assert result_content is not None
    return result_content
