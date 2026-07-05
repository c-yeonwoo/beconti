"""프론트엔드 계약(src/lib/api.ts)과 1:1로 맞춘 스키마.

프론트가 camelCase(videoUrl, createdAt, platformStatus ...)를 기대하므로
필드명을 그대로 camelCase 로 선언해 별도 alias 설정 없이 계약을 보장한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Platform = Literal["naver_blog", "naver_clip", "wordpress", "instagram"]
PublishStatus = Literal["idle", "queued", "success", "failed"]

ALL_PLATFORMS: tuple[Platform, ...] = ("naver_blog", "naver_clip", "wordpress", "instagram")


class ScriptLine(BaseModel):
    time: str
    caption: str
    narration: str


class GeneratePayload(BaseModel):
    keywords: list[str] = []
    tone: str = "review"
    mediaIds: list[str] = []


class GeneratedContent(BaseModel):
    id: str
    title: str
    body: str
    videoUrl: str | None = None
    script: list[ScriptLine] = []
    createdAt: str
    platformStatus: dict[str, PublishStatus]


class UploadResponse(BaseModel):
    mediaIds: list[str]


class PublishPayload(BaseModel):
    contentId: str
    platforms: list[Platform]


class PublishResponse(BaseModel):
    ok: bool


def default_platform_status() -> dict[str, PublishStatus]:
    return {p: "idle" for p in ALL_PLATFORMS}
