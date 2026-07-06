"""캠페인 가이드라인 준수 체크 — 전부 코드 계산 (LLM 토큰 0).

붙여넣은 가이드라인 텍스트에서 숫자 기준(글자수·키워드횟수·사진수)을 정규식으로
추출하고, 생성 본문/입력값이 그 기준을 만족하는지 검사한다.
"""

from __future__ import annotations

import re

DEFAULT_MIN_CHARS = 1000
DISCLOSURE_HINT = "제공받"  # 대가성 문구 핵심 토큰


def _extract_int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text or "")
    return int(m.group(1).replace(",", "")) if m else None


def check_compliance(
    body: str,
    keywords: list[str],
    hashtags: list[str],
    guideline: str,
    photo_count: int,
) -> list[dict]:
    body = body or ""
    g = guideline or ""
    checks: list[dict] = []

    # 글자수
    min_chars = _extract_int(r"(\d[\d,]*)\s*자\s*이상", g) or DEFAULT_MIN_CHARS
    n = len(body)
    checks.append({"label": f"글자수 {n:,}자 / 기준 {min_chars:,}자 이상", "ok": n >= min_chars})

    # 키워드 반복 횟수 (가이드라인에 'N회' 있으면 그 값, 없으면 최소 1회)
    kw_count = (
        _extract_int(r"키워드.{0,20}?(\d+)\s*회", g)
        or _extract_int(r"(\d+)\s*회\s*이상", g)
        or 1
    )
    for kw in keywords:
        c = body.count(kw)
        checks.append(
            {"label": f"키워드 '{kw}' {c}회 / 기준 {kw_count}회", "ok": c >= kw_count}
        )

    # 필수 해시태그 포함 여부
    if hashtags:
        present = [h for h in hashtags if h in body]
        checks.append(
            {
                "label": f"필수 해시태그 {len(present)}/{len(hashtags)}개 포함",
                "ok": len(present) == len(hashtags),
            }
        )

    # 대가성(협찬) 문구
    checks.append(
        {"label": "대가성 문구('제공받아…') 포함", "ok": DISCLOSURE_HINT in body}
    )

    # 사진 수 (가이드라인에 '사진 N장' 명시된 경우만)
    min_photos = _extract_int(r"사진\s*(\d[\d,]*)\s*장", g)
    if min_photos:
        checks.append(
            {"label": f"사진 {photo_count}장 / 기준 {min_photos}장", "ok": photo_count >= min_photos}
        )

    return checks
