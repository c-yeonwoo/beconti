"""Typecast TTS — 대본 나레이션을 음성으로 합성.

TYPECAST_API_KEY 가 없으면 None 을 반환(비활성). 응답은 오디오 바이너리.
"""

from __future__ import annotations

import time

import httpx

from ..config import settings

TTS_URL = "https://api.typecast.ai/v1/text-to-speech"
VOICES_URL = "https://api.typecast.ai/v2/voices"


def is_enabled() -> bool:
    return bool(settings.typecast_api_key and settings.typecast_voice_id)


def list_voices() -> list[dict]:
    """사용 가능한 음성 목록 (voice_id 확인용)."""
    r = httpx.get(VOICES_URL, headers={"X-API-KEY": settings.typecast_api_key}, timeout=30)
    r.raise_for_status()
    return r.json()


def synthesize(
    text: str, out_path: str, voice_id: str | None = None, tempo: float | None = None
) -> str | None:
    """text → mp3 파일. 키/보이스 없으면 None. tempo 기본은 settings.tts_tempo(겹침/짤림 방지)."""
    text = (text or "").strip()
    if not text or not settings.typecast_api_key:
        return None
    vid = voice_id or settings.typecast_voice_id
    if not vid:
        return None

    tempo = tempo if tempo is not None else settings.tts_tempo
    tempo = max(0.5, min(2.0, tempo))

    payload = {
        "voice_id": vid,
        "text": text[:2000],
        "model": settings.typecast_model,
        "language": "kor",
        "output": {"audio_format": "mp3", "volume": 100, "audio_tempo": tempo},
    }
    headers = {"X-API-KEY": settings.typecast_api_key, "Content-Type": "application/json"}

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            r = httpx.post(TTS_URL, json=payload, headers=headers, timeout=60)
            if r.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(r.content)
                return out_path
            if r.status_code in (429, 500, 502, 503):
                last_err = RuntimeError(f"{r.status_code} {r.text[:100]}")
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Typecast {r.status_code}: {r.text[:200]}")
        except httpx.HTTPError as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    print(f"  ⚠️ TTS 실패: {last_err}")
    return None
