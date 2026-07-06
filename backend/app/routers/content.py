"""대시보드 / 배포관리 화면에서 쓸 조회 엔드포인트 (프론트 확장용)."""

from fastapi import APIRouter, HTTPException

from ..db import get_content, list_content, update_content_fields
from ..models import GeneratedContent, UpdateContentPayload

router = APIRouter(prefix="/api", tags=["content"])


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
        content_id,
        payload.title,
        payload.body,
        [s.model_dump() for s in payload.script],
    )
    result = get_content(content_id)
    assert result is not None
    return result
