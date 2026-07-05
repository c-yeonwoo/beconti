"""Gemini 멀티모달: 이미지들을 분석해 블로그 초안 + 숏폼 대본 생성.

GEMINI_API_KEY 가 없으면 스텁 초안을 반환한다 → 키 없이도 전체 파이프라인
(업로드 → 생성 → 저장 → 배포)을 프론트와 연결해 테스트할 수 있다.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..config import settings

TONE_LABELS = {
    "review": "생생한 방문 리뷰형 (직접 다녀온 듯 구체적이고 솔직한 후기)",
    "info": "정보 전달형 (핵심 정보를 정리해 주는 가이드 톤)",
    "daily": "일상 브이로그형 (친근한 말투의 일상 기록)",
}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}


def _build_prompt(keywords: list[str], tone: str) -> str:
    kw = ", ".join(keywords) if keywords else "(키워드 없음)"
    tone_desc = TONE_LABELS.get(tone, TONE_LABELS["review"])
    return f"""당신은 네이버 블로그 상위노출에 능한 한국어 콘텐츠 작가입니다.
첨부된 사진들을 **업로드된 순서대로** 하나의 방문/경험 흐름으로 보고 분석하세요.

- 핵심 키워드: {kw}
- 톤/스타일: {tone_desc}

아래 JSON 형식으로만 응답하세요. 다른 설명 없이 JSON 만 출력합니다.

{{
  "title": "클릭을 부르는 자연스러운 한국어 제목",
  "body": "마크다운 형식의 블로그 본문. 소제목(##)과 문단으로 구성하고, 사진 위치에 [사진 N] 표기를 넣어 흐름을 잡아주세요. 800자 이상.",
  "script": [
    {{"time": "0-3s", "caption": "화면 하단 자막(짧게)", "narration": "나레이션 대본 문장"}}
  ]
}}

script 는 위 사진들로 만들 15~30초 숏폼용으로 5~7줄 작성하세요."""


def _parse_json(text: str) -> dict:
    """모델 응답에서 JSON 객체를 견고하게 추출."""
    text = text.strip()
    # 코드펜스 제거
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _stub(keywords: list[str], tone: str, n_images: int) -> dict:
    kw = ", ".join(keywords) if keywords else "샘플 키워드"
    body = (
        f"# {kw} 후기\n\n"
        "> ⚠️ GEMINI_API_KEY 가 설정되지 않아 **스텁(더미) 초안**이 반환되었습니다.\n"
        "> backend/.env 에 키를 넣으면 실제 AI 분석 결과로 대체됩니다.\n\n"
        f"## 첫인상\n\n업로드한 사진 {n_images}장을 바탕으로 작성될 자리입니다. "
        f"'{kw}' 키워드와 {TONE_LABELS.get(tone, tone)} 톤으로 생성됩니다.\n\n"
        "## 상세\n\n[사진 1] 이 위치에 사진별 설명이 들어갑니다.\n\n"
        "## 마무리\n\n방문을 고민 중이라면 참고가 되었길 바랍니다."
    )
    script = [
        {"time": "0-3s", "caption": f"{kw} 다녀왔어요", "narration": f"오늘은 {kw}에 다녀왔습니다."},
        {"time": "3-8s", "caption": "첫인상", "narration": "입구부터 분위기가 좋았어요."},
        {"time": "8-15s", "caption": "하이라이트", "narration": "가장 인상 깊었던 부분을 소개할게요."},
        {"time": "15-20s", "caption": "총평", "narration": "다시 방문할 의향 100%입니다."},
    ]
    return {"title": f"{kw} 방문 후기", "body": body, "script": script}


def generate_draft(image_paths: list[str], keywords: list[str], tone: str) -> dict:
    """이미지 경로 목록 → {title, body, script[]} dict 반환."""
    images = [p for p in image_paths if Path(p).suffix.lower() in _IMAGE_EXTS]

    if not settings.gemini_api_key:
        return _stub(keywords, tone, len(images))

    # 지연 import: 키 없는 환경에서 SDK 미설치여도 스텁 경로는 동작
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    parts: list[object] = []
    for path in images:
        data = Path(path).read_bytes()
        suffix = Path(path).suffix.lower().lstrip(".")
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    parts.append(_build_prompt(keywords, tone))

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.9,
    )

    # 2.5 모델은 과부하 시 503 UNAVAILABLE 을 자주 반환 → 지수 백오프 재시도
    resp = None
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            resp = client.models.generate_content(
                model=settings.gemini_model, contents=parts, config=config
            )
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                time.sleep(2 * (attempt + 1))
                continue
            raise
    if resp is None:
        raise RuntimeError(f"Gemini 호출 실패(과부하 지속): {last_err}")

    data = _parse_json(resp.text or "")
    data.setdefault("title", ", ".join(keywords) or "제목 없음")
    data.setdefault("body", "")
    data.setdefault("script", [])
    return data
