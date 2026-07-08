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

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
_VID_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


def _blog_images(content_id: str, tmp_holder: list) -> list[str]:
    """블로그용 사진 경로. 이미지가 있으면 그대로, 없고 영상만 있으면 프레임 캡처."""
    from pathlib import Path
    import tempfile

    from ..services.video import extract_video_frames

    media = get_media_paths(get_content_media_ids(content_id))
    images = [p for (p, _m) in media if Path(p).suffix.lower() in _IMG_EXTS]
    if images:
        return images
    videos = [p for (p, _m) in media if Path(p).suffix.lower() in _VID_EXTS]
    if not videos:
        return []
    # 영상만 → 프레임 캡처를 블로그 사진으로 (고해상도)
    td = tempfile.mkdtemp(prefix="blogframes_")
    tmp_holder.append(td)
    frames: list[str] = []
    for v in videos:
        frames += extract_video_frames(v, td, n=6, width=1280)
    return frames


@router.post("/publish", response_model=PublishResponse)
async def publish(payload: PublishPayload) -> PublishResponse:
    content = get_content(payload.contentId)
    if content is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    all_ok = True
    tmp_dirs: list = []

    for platform in payload.platforms:
        update_platform_status(payload.contentId, platform, "queued")

        if platform == "naver_blog":
            image_paths = _blog_images(payload.contentId, tmp_dirs)
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

    # 임시 프레임 폴더 정리
    import shutil
    for d in tmp_dirs:
        shutil.rmtree(d, ignore_errors=True)

    return PublishResponse(ok=all_ok)
