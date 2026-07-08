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
_VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}

# 숏폼 대본(자막/나레이션) 말투 스타일
SCRIPT_STYLES = {
    "polite": "존댓말의 깔끔하고 친절한 리뷰 말투",
    "cute": "반말로 귀엽고 다정하게, 브이로그 찍듯 친근한 말투 (예: '여기 진짜 맛있어!', '완전 내 취향이야ㅎㅎ')",
    "energetic": "반말로 활기차고 텐션 높게, 숏폼 특유의 리듬감 있는 말투 (예: '이거 실화냐!', '무조건 가야 돼')",
    "broadcast": (
        "'VJ특공대'류 방송 맛집 소개 프로그램의 3인칭 리포터 나레이션 톤. "
        "존댓말 나레이터 시점으로 극적이고 감탄조로 묘사하며, 궁금증을 유발하는 질문형 문장과 "
        "과장된 수식어를 섞는다. "
        "(예: '이곳, 평범해 보이지만 그 안에 특별한 비밀이 숨어있었으니', "
        "'과연 그 비법은 무엇일까?', '손님들의 발길이 끊이지 않는 이유, 지금 공개합니다', "
        "'무려 3대째 이어져 내려오는 손맛이라고 하는데요')"
    ),
}


def default_guideline(content_type: str) -> str:
    return DEFAULT_GUIDELINE_VIDEO if content_type == "vlog" else DEFAULT_GUIDELINE_BLOG


def _build_blog_prompt(
    keywords: list[str],
    category: str,
    content_type: str,
    guideline: str,
    hashtags: list[str],
) -> str:
    kw = ", ".join(keywords) if keywords else "(없음)"
    tags = " ".join(hashtags) if hashtags else "(지정 없음)"
    type_desc = CONTENT_TYPE_LABELS.get(content_type, CONTENT_TYPE_LABELS["place_review"])
    return f"""당신은 체험단 리뷰에 능한 한국어 블로그 작가입니다.
첨부된 사진들은 업로드 순서가 뒤죽박죽일 수 있습니다. 각 사진 내용을 먼저 파악한 뒤,
리뷰 흐름(도입→상세→마무리)에 맞게 **사진 순서·위치를 직접 계획**하고, 정성껏 깊이 있게 작성하세요.

- 카테고리: {category or "(미지정)"}
- 콘텐츠 유형: {type_desc}
- 핵심 키워드: {kw}
- 필수 해시태그: {tags}

[반드시 지킬 가이드라인]
{guideline}

[사진 배치 규칙]
- 사진을 넣을 위치에 정확히 `[사진 N]` 표기 (N = 그 사진의 **업로드 순서 번호**, 1부터).
- 각 사진은 내용상 가장 어울리는 위치에 배치하고, **모든 사진을 한 번씩만** 사용.

[금지]
- 본문에 지도 링크·URL·주소 텍스트 금지 (위치는 발행 시 장소 카드로 자동 첨부).
- 이모지 금지.

아래 JSON 형식으로만 응답하세요. 다른 설명 없이 JSON 만:
{{
  "title": "클릭을 부르는 자연스러운 한국어 제목",
  "body": "마크다운 본문. 소제목(##)·문단 구성. 사진 위치마다 [사진 N] 을 독립된 줄에 표기."
}}
- 필수 해시태그는 반드시 본문에 포함하세요."""


def _build_script_prompt(
    keywords: list[str],
    guideline: str,
    script_style: str,
    segment_times: list[tuple[float, float]] | None,
) -> str:
    kw = ", ".join(keywords) if keywords else "(없음)"
    style_desc = SCRIPT_STYLES.get(script_style, SCRIPT_STYLES["polite"])
    if segment_times:
        seg_list = "\n".join(
            f"  {i + 1}. {s:.1f}-{e:.1f}초" for i, (s, e) in enumerate(segment_times)
        )
        seg_rule = (
            f"- 첨부 이미지는 **영상의 실제 장면 구간별 대표 프레임**이며, 순서대로 아래 "
            f"시간대에 대응합니다:\n{seg_list}\n"
            f"- script 는 **정확히 {len(segment_times)}줄**, 위 순서·구간과 1:1로 작성하고 "
            "각 줄의 \"time\" 은 주어진 시간대를 \"S.S-E.Es\" 형식 그대로 쓰세요(임의 시간 금지).\n"
            "- 각 장면의 실제 내용을 반영하세요."
        )
    else:
        seg_rule = (
            "- 첨부 이미지는 영상에서 뽑은 장면입니다. 영상 내용을 반영해 30초 이상 숏폼용으로 "
            "script 8~12줄 작성. time 은 \"0-4s\" 형식."
        )
    return f"""당신은 숏폼 영상 대본 작가입니다. 아래 규칙으로 자막·나레이션 대본만 작성하세요.

- 핵심 키워드: {kw}

[대본 가이드라인]
{guideline}

[작성 규칙]
{seg_rule}
- caption 은 화면 하단 짧은 자막, narration 은 음성으로 읽을 문장.
- 말투: {style_desc}
- 이모지 금지.

아래 JSON 형식으로만 응답하세요. 다른 설명 없이 JSON 만:
{{
  "script": [
    {{"time": "0-4s", "caption": "짧은 자막", "narration": "나레이션 문장"}}
  ]
}}"""


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


def _image_part(types, path: str):
    data = Path(path).read_bytes()
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
    return types.Part.from_bytes(data=data, mime_type=mime)


def _gemini_json(image_paths: list[str], prompt: str) -> dict:
    """이미지들 + 프롬프트로 Gemini 호출 → JSON dict. (503 지수백오프 재시도)"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    parts: list[object] = [_image_part(types, p) for p in image_paths]
    parts.append(prompt)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.9)

    resp, last_err = None, None
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
    return _parse_json(resp.text or "")


def generate_blog(
    image_paths: list[str],
    keywords: list[str],
    category: str = "",
    content_type: str = "place_review",
    guideline: str = "",
    hashtags: list[str] | None = None,
) -> dict:
    """블로그 글 생성 → {title, body}. 영상은 프레임 몇 장을 맥락으로 함께 전달."""
    import tempfile

    hashtags = hashtags or []
    content_type = TYPE_ALIASES.get(content_type, content_type)
    guideline = guideline.strip() or default_guideline(content_type)
    images = [p for p in image_paths if Path(p).suffix.lower() in _IMAGE_EXTS]
    videos = [p for p in image_paths if Path(p).suffix.lower() in _VIDEO_EXTS]

    if not settings.gemini_api_key:
        kw = ", ".join(keywords) if keywords else "샘플 키워드"
        return {
            "title": f"{kw} 방문 후기",
            "body": (
                f"# {kw} 후기\n\n> GEMINI_API_KEY 미설정 — 스텁 초안입니다.\n\n"
                "## 첫인상\n[사진 1]\n\n## 마무리\n" + (" ".join(hashtags) if hashtags else "")
            ),
        }

    with tempfile.TemporaryDirectory() as td:
        from .video import extract_video_frames

        frames: list[str] = []
        for v in videos:
            try:
                frames += extract_video_frames(v, td, n=6)
            except Exception:  # noqa: BLE001
                pass
        prompt = _build_blog_prompt(keywords, category, content_type, guideline, hashtags)
        data = _gemini_json(images + frames, prompt)

    return {"title": data.get("title") or (", ".join(keywords) or "제목 없음"),
            "body": data.get("body") or ""}


def generate_script(
    video_paths: list[str],
    keywords: list[str],
    guideline: str = "",
    script_style: str = "polite",
) -> dict:
    """숏폼 대본 생성 → {script:[...]}. 영상 없으면 빈 배열."""
    import tempfile

    videos = [p for p in video_paths if Path(p).suffix.lower() in _VIDEO_EXTS]
    if not videos:
        return {"script": []}
    guideline = guideline.strip() or DEFAULT_GUIDELINE_VIDEO

    if not settings.gemini_api_key:
        kw = ", ".join(keywords) if keywords else "샘플"
        return {"script": [
            {"time": "0-5s", "caption": f"{kw} 다녀왔어요", "narration": f"오늘은 {kw}입니다."},
            {"time": "5-10s", "caption": "하이라이트", "narration": "가장 인상 깊었던 부분입니다."},
        ]}

    with tempfile.TemporaryDirectory() as td:
        from .video import compute_script_segments, extract_frame_at

        frame_paths: list[str] = []
        segment_times: list[tuple[float, float]] = []
        try:
            for i, seg in enumerate(compute_script_segments(videos)):
                mid = (seg["local_start"] + seg["local_end"]) / 2
                p = str(Path(td) / f"seg_{i}.jpg")
                if extract_frame_at(seg["video"], mid, p):
                    frame_paths.append(p)
                    segment_times.append((seg["start"], seg["end"]))
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ 장면 구간 분석 실패: {str(e)[:60]}")
            segment_times = []
        prompt = _build_script_prompt(keywords, guideline, script_style, segment_times or None)
        data = _gemini_json(frame_paths, prompt)

    return {"script": data.get("script") or []}
