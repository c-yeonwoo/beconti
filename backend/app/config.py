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

        # 숏폼 렌더: Creatomate 우선, 크레딧/키 없으면 FFmpeg fallback
        self.creatomate_api_key = os.getenv("CREATOMATE_API_KEY", "").strip()
        self.creatomate_template_id = os.getenv("CREATOMATE_TEMPLATE_ID", "").strip()

        # Typecast TTS (내레이션 음성). 키 없으면 TTS 생략
        self.typecast_api_key = os.getenv("TYPECAST_API_KEY", "").strip()
        self.typecast_voice_id = os.getenv("TYPECAST_VOICE_ID", "").strip()
        self.typecast_model = os.getenv("TYPECAST_MODEL", "ssfm-v30").strip() or "ssfm-v30"
        # 나레이션 배속 (겹침/짤림 방지). 1.0=기본속도, 1.2=20% 빠르게
        self.tts_tempo = float(os.getenv("TTS_TEMPO", "1.2") or 1.2)

        self.data_dir = Path(os.getenv("DATA_DIR", "./data")).expanduser().resolve()
        self.upload_dir = self.data_dir / "uploads"
        self.render_dir = self.data_dir / "renders"
        self.bgm_dir = self.data_dir / "bgm"  # 배경음악 파일을 여기 넣으면 자동 사용
        self.db_path = self.data_dir / "beconti.db"

        # 오디오 믹스 볼륨 (0~1)
        self.bgm_volume = float(os.getenv("BGM_VOLUME", "0.15") or 0.15)
        self.narration_volume = float(os.getenv("NARRATION_VOLUME", "1.0") or 1.0)
        self.orig_audio_volume = float(os.getenv("ORIG_AUDIO_VOLUME", "0.25") or 0.25)

        # 비어 있으면 자동화 전용 프로필(data/naver-profile) 사용 → 메인 크롬과 독립,
        # 여기 네이버 로그인을 1회만 해두면 세션이 유지된다.
        raw_naver_dir = os.getenv("NAVER_CHROME_USER_DATA_DIR", "").strip()
        self.naver_user_data_dir = raw_naver_dir or str(self.data_dir / "naver-profile")
        self.naver_blog_id = os.getenv("NAVER_BLOG_ID", "").strip()
        # 공개 범위: public | neighbor | both | private (기본 public=전체공개)
        self.naver_visibility = os.getenv("NAVER_PUBLISH_VISIBILITY", "public").strip() or "public"
        self.publish_dry_run = _bool("PUBLISH_DRY_RUN", True)
        self.playwright_headless = _bool("PLAYWRIGHT_HEADLESS", False)

        raw_origins = os.getenv("CORS_ORIGINS", "").strip()
        self.cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.render_dir.mkdir(parents=True, exist_ok=True)
        self.bgm_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
