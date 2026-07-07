from fastapi import APIRouter, HTTPException

from ..db import (
    get_content,
    get_content_gen_params,
    get_content_media_ids,
    get_content_place_name,
    get_media_paths,
    update_platform_status,
)
from ..models import PublishPayload, PublishResponse
from ..services.naver import publish_naver_blog

router = APIRouter(prefix="/api", tags=["publish"])


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
            place_url = get_content_gen_params(payload.contentId).get("placeUrl", "")
            result = await publish_naver_blog(
                content.title, content.body, image_paths,
                place_name=place_name, place_url=place_url,
            )
            status = "success" if result.ok else "failed"
            update_platform_status(payload.contentId, platform, status)
            all_ok = all_ok and result.ok

        elif platform == "naver_clip":
            # 클립은 반자동(CLI 핸드오프)로 업로드 → API 로는 실패가 아닌 '대기(수동)'.
            # 실제 성공 전환은 CLI(naver_clip_test.py) 완료 시 이뤄짐.
            update_platform_status(payload.contentId, platform, "queued")

        else:
            # 인스타 등 미구현 → 실패 표시
            update_platform_status(payload.contentId, platform, "failed")
            all_ok = False

    return PublishResponse(ok=all_ok)
