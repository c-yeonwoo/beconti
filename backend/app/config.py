"""환경변수 기반 설정. .env 를 읽어 전역 settings 객체로 노출."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5").strip()

        self.data_dir = Path(os.getenv("DATA_DIR", "./data")).expanduser().resolve()
        self.upload_dir = self.data_dir / "uploads"
        self.render_dir = self.data_dir / "renders"
        self.db_path = self.data_dir / "beconti.db"

        # 비어 있으면 자동화 전용 프로필(data/naver-profile) 사용 → 메인 크롬과 독립,
        # 여기 네이버 로그인을 1회만 해두면 세션이 유지된다.
        raw_naver_dir = os.getenv("NAVER_CHROME_USER_DATA_DIR", "").strip()
        self.naver_user_data_dir = raw_naver_dir or str(self.data_dir / "naver-profile")
        self.naver_blog_id = os.getenv("NAVER_BLOG_ID", "").strip()
        self.publish_dry_run = _bool("PUBLISH_DRY_RUN", True)
        self.playwright_headless = _bool("PLAYWRIGHT_HEADLESS", False)

        raw_origins = os.getenv("CORS_ORIGINS", "").strip()
        self.cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.render_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
