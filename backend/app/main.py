"""beconti 백엔드 진입점.

프론트엔드(src/lib/api.ts)의 계약에 맞춘 FastAPI 서버.
  GET  /               → 헬스체크 (pingBackend)
  POST /api/upload     → 미디어 업로드
  POST /api/generate   → Gemini 멀티모달 초안 생성
  POST /api/publish    → 네이버 블로그 Playwright 발행
  GET  /api/content    → 생성 콘텐츠 목록 (프론트 확장용)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .routers import content, generate, publish, upload, video


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    yield


app = FastAPI(title="beconti backend", version="0.1.0", lifespan=lifespan)

# CORS: 명시 origin 이 없으면 모든 localhost 포트 허용 (개발 편의)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(upload.router)
app.include_router(generate.router)
app.include_router(publish.router)
app.include_router(content.router)
app.include_router(video.router)

# 렌더된 MP4 등 정적 서빙 (프론트에서 재생) → http://localhost:8000/media/renders/<file>
settings.ensure_dirs()
app.mount("/media", StaticFiles(directory=str(settings.data_dir)), name="media")


@app.get("/")
def health() -> dict:
    return {
        "service": "beconti-backend",
        "status": "ok",
        "gemini": bool(settings.gemini_api_key),
        "dryRun": settings.publish_dry_run,
    }
