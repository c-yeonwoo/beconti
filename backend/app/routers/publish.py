from fastapi import APIRouter, HTTPException

from ..db import (
    get_content,
    get_content_media_ids,
    get_content_place_name,
    get_media_paths,
    update_platform_status,
)
from ..models import PublishPayload, PublishResponse
from ..services.naver import publish_naver_blog

router = APIRouter(prefix="/api", tags=["publish"])

# Phase 2~3 에서 구현될 플랫폼 (지금은 미지원 표시)
_NOT_IMPLEMENTED = {"naver_clip", "wordpress", "instagram"}


@router.post("/publish", response_model=PublishResponse)
async def publish(payload: PublishPayload) -> PublishResponse:
    content = get_content(payload.contentId)
    if content is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    all_ok = True

    for platform in payload.platforms:
        update_platform_status(payload.contentId, platform, "queued")

        if platform == "naver_blog":
            media_ids = get_content_media_ids(payload.contentId)
            image_paths = [p for (p, _mime) in get_media_paths(media_ids)]
            place_name = get_content_place_name(payload.contentId)
            result = await publish_naver_blog(
                content.title, content.body, image_paths, place_name=place_name
            )
            status = "success" if result.ok else "failed"
            update_platform_status(payload.contentId, platform, status)
            all_ok = all_ok and result.ok

        elif platform in _NOT_IMPLEMENTED:
            # 아직 미구현 → 실패로 표시 (Phase 2~3)
            update_platform_status(payload.contentId, platform, "failed")
            all_ok = False

        else:
            update_platform_status(payload.contentId, platform, "failed")
            all_ok = False

    return PublishResponse(ok=all_ok)
