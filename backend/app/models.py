"""프론트엔드 계약(src/lib/api.ts)과 1:1로 맞춘 스키마.

프론트가 camelCase(videoUrl, createdAt, platformStatus ...)를 기대하므로
필드명을 그대로 camelCase 로 선언해 별도 alias 설정 없이 계약을 보장한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Platform = Literal["naver_blog", "naver_clip", "instagram"]
PublishStatus = Literal["idle", "queued", "success", "failed"]

ALL_PLATFORMS: tuple[Platform, ...] = ("naver_blog", "naver_clip", "instagram")


class ScriptLine(BaseModel):
    time: str
    caption: str
    narration: str


class GeneratePayload(BaseModel):
    keywords: list[str] = []
    category: str = ""                    # 카테고리 (예: 맛집, 뷰티, 여행)
    contentType: str = "place_review"     # 유형: place_review | product_review | vlog
    guideline: str = ""                   # 붙여넣은 가이드라인. 비면 유형별 기본값 사용
    requiredHashtags: list[str] = []      # 필수 해시태그
    placeName: str = ""                   # 매장명(상호) — 네이버 장소 카드 삽입용
    placeUrl: str = ""                    # (옵션) 네이버 지도 링크. 있으면 우선, 없으면 매장명 검색
    mediaIds: list[str] = []
    tone: str = ""                        # deprecated (하위호환용)


class GeneratedContent(BaseModel):
    id: str
    title: str
    body: str
    videoUrl: str | None = None
    script: list[ScriptLine] = []
    createdAt: str
    platformStatus: dict[str, PublishStatus]


class UpdateContentPayload(BaseModel):
    title: str = ""
    body: str = ""
    script: list[ScriptLine] = []


class UploadResponse(BaseModel):
    mediaIds: list[str]


class PublishPayload(BaseModel):
    contentId: str
    platforms: list[Platform]


class PublishResponse(BaseModel):
    ok: bool


def default_platform_status() -> dict[str, PublishStatus]:
    return {p: "idle" for p in ALL_PLATFORMS}


class CompliancePayload(BaseModel):
    body: str = ""
    keywords: list[str] = []
    requiredHashtags: list[str] = []
    guideline: str = ""
    photoCount: int = 0


class ComplianceCheck(BaseModel):
    label: str
    ok: bool


class ComplianceResult(BaseModel):
    checks: list[ComplianceCheck]
    passed: int
    total: int
