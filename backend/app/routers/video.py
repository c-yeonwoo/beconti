"""숏폼 영상 생성 엔드포인트."""

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..db import get_content, get_content_media_ids, get_media_paths, update_video_url
from ..models import GeneratedContent
from ..services.video import render_shortform

router = APIRouter(prefix="/api", tags=["video"])

PUBLIC_BASE = "http://localhost:8000"


@router.post("/video/{content_id}", response_model=GeneratedContent)
def make_video(content_id: str) -> GeneratedContent:
    content = get_content(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    image_paths = [p for (p, _mime) in get_media_paths(get_content_media_ids(content_id))]
    if not image_paths:
        raise HTTPException(status_code=400, detail="영상으로 만들 이미지가 없습니다.")

    out = settings.render_dir / f"shortform_{content_id}.mp4"
    try:
        _, engine = render_shortform(
            image_paths, [s.model_dump() for s in content.script], str(out)
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"숏폼 렌더 실패: {e}")

    url = f"{PUBLIC_BASE}/media/renders/{out.name}"
    update_video_url(content_id, url)
    result = get_content(content_id)
    assert result is not None
    return result
