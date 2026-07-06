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

CONTENT_TYPE_LABELS = {
    "place_review": "장소 리뷰 (방문 경험 중심 — 위치·분위기·메뉴/가격·재방문 의향)",
    "product_review": "제품 리뷰 (개봉·사용 경험 중심 — 특징·장단점·추천 대상)",
    "vlog": "브이로그 (시간 흐름의 일상 기록, 친근한 말투 — 영상 중심)",
}

# 유형 한글 라벨 → 내부 키
TYPE_ALIASES = {"장소리뷰": "place_review", "제품리뷰": "product_review", "브이로그": "vlog"}

# 붙여넣은 가이드라인이 없을 때 쓰는 유형별 기본값
DEFAULT_GUIDELINE_BLOG = """- 실제로 방문/사용한 것처럼 생생하고 구체적으로, 광고 티는 최소화
- 본문 1,000자 이상, 소제목(##)으로 문단 구분해 가독성 확보
- 핵심 키워드를 본문에 자연스럽게 5회 이상 반복
- 사진이 들어갈 위치에 [사진 N] 표기
- 대가성 문구 포함: "소정의 제품/서비스를 제공받아 작성한 후기입니다"
- 마지막에 필수 해시태그를 나열"""

DEFAULT_GUIDELINE_VIDEO = """- 15~30초 세로 영상(9:16) 기준
- 첫 3초에 강한 후킹, 지루하지 않게 장면 전환
- 각 컷에 짧은 자막 필수, 브랜드/제품명을 초반에 노출
- 마지막 컷에 필수 해시태그 안내"""

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}


def default_guideline(content_type: str) -> str:
    return DEFAULT_GUIDELINE_VIDEO if content_type == "vlog" else DEFAULT_GUIDELINE_BLOG


def _build_prompt(
    keywords: list[str],
    category: str,
    content_type: str,
    guideline: str,
    hashtags: list[str],
    has_video: bool,
) -> str:
    kw = ", ".join(keywords) if keywords else "(없음)"
    tags = " ".join(hashtags) if hashtags else "(지정 없음)"
    type_desc = CONTENT_TYPE_LABELS.get(content_type, CONTENT_TYPE_LABELS["place_review"])
    n_note = (
        "첨부된 사진들은 업로드된 순서가 뒤죽박죽일 수 있습니다. "
        "각 사진의 내용을 먼저 파악한 뒤, 리뷰 흐름(도입→상세→마무리)에 가장 잘 맞도록 "
        "**사진의 노출 순서와 위치를 직접 계획**하세요."
    )
    if has_video:
        script_json = '  "script": [\n    {{"time": "0-3s", "caption": "자막(짧게)", "narration": "나레이션"}}\n  ]'
        script_rule = (
            "- 첨부된 영상들을 편집한 **30초 이상** 숏폼용으로 script 를 8~12줄 작성 "
            "(배경음+자막 전제). caption/narration 에 이모지 금지."
        )
    else:
        script_json = '  "script": []'
        script_rule = "- 영상이 첨부되지 않았으므로 script 는 **반드시 빈 배열 [] 로** 두세요."
    return f"""당신은 체험단 리뷰에 능한 한국어 콘텐츠 작가입니다.
{n_note}
그 계획에 맞춰 블로그 본문을 중심으로 작성하세요.

- 카테고리: {category or "(미지정)"}
- 콘텐츠 유형: {type_desc}
- 핵심 키워드: {kw}
- 필수 해시태그: {tags}

[반드시 지킬 가이드라인]
{guideline}

[사진 배치 규칙]
- 사진을 넣을 위치에 정확히 `[사진 N]` 표기 (N = 그 사진의 **업로드 순서 번호**, 1부터).
- 각 사진은 내용상 가장 어울리는 위치에 배치하고, **모든 사진을 한 번씩만** 사용.
- 예: 3번째 업로드 사진이 음식 클로즈업이면 음식 설명 문단 앞에 `[사진 3]`.

[금지]
- 본문에 지도 링크·URL·"지도 위치 링크"·주소 텍스트를 넣지 마세요.
  위치/지도는 발행 시 별도의 장소 카드로 자동 첨부됩니다.
- **이모지(😀🍽️✨ 등)를 절대 쓰지 마세요.**

아래 JSON 형식으로만 응답하세요. 다른 설명 없이 JSON 만 출력합니다.

{{
  "title": "클릭을 부르는 자연스러운 한국어 제목",
  "body": "마크다운 본문. 소제목(##)·문단 구성. 사진 위치마다 [사진 N] 을 독립된 줄에 표기.",
{script_json}
}}

- 필수 해시태그는 반드시 결과에 포함하세요.
{script_rule}"""


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


def _stub(keywords: list[str], content_type: str, hashtags: list[str], n_images: int, has_video: bool) -> dict:
    kw = ", ".join(keywords) if keywords else "샘플 키워드"
    tags = " ".join(hashtags) if hashtags else "#샘플태그"
    body = (
        f"# {kw} 후기\n\n"
        "> ⚠️ GEMINI_API_KEY 가 설정되지 않아 **스텁(더미) 초안**이 반환되었습니다.\n"
        "> backend/.env 에 키를 넣으면 실제 AI 분석 결과로 대체됩니다.\n\n"
        f"## 첫인상\n\n업로드한 사진 {n_images}장 · 유형 '{content_type}' 로 작성될 자리입니다.\n\n"
        "## 상세\n\n[사진 1] 이 위치에 사진별 설명이 들어갑니다.\n\n"
        f"## 마무리\n\n방문을 고민 중이라면 참고가 되었길 바랍니다.\n\n{tags}"
    )
    script = (
        [
            {"time": "0-5s", "caption": f"{kw} 다녀왔어요", "narration": f"오늘은 {kw}에 다녀왔습니다."},
            {"time": "5-15s", "caption": "하이라이트", "narration": "가장 인상 깊었던 부분입니다."},
            {"time": "15-30s", "caption": "총평", "narration": "다시 방문할 의향 100%입니다."},
        ]
        if has_video
        else []
    )
    return {"title": f"{kw} 방문 후기", "body": body, "script": script}


def generate_draft(
    image_paths: list[str],
    keywords: list[str],
    category: str = "",
    content_type: str = "place_review",
    guideline: str = "",
    hashtags: list[str] | None = None,
    has_video: bool = False,
) -> dict:
    """이미지 경로 + 생성 옵션 → {title, body, script[]} dict 반환.

    guideline 이 비어 있으면 유형별 기본 가이드라인을 사용한다.
    숏폼 대본(script)은 has_video=True(영상 첨부)일 때만 생성된다.
    """
    hashtags = hashtags or []
    content_type = TYPE_ALIASES.get(content_type, content_type)
    guideline = guideline.strip() or default_guideline(content_type)
    images = [p for p in image_paths if Path(p).suffix.lower() in _IMAGE_EXTS]

    if not settings.gemini_api_key:
        return _stub(keywords, content_type, hashtags, len(images), has_video)

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
    parts.append(_build_prompt(keywords, category, content_type, guideline, hashtags, has_video))

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
    if not has_video:
        data["script"] = []  # 영상 없으면 대본 미생성
    return data
