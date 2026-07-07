#!/usr/bin/env python3
"""네이버 클립 반자동 업로드. 콘텐츠의 숏폼 MP4를 올린다.

    ./.venv/bin/python naver_clip_test.py                 # dry-run (헤드리스, 저장 안 함)
    ./.venv/bin/python naver_clip_test.py go              # 반자동 (최신 콘텐츠)
    ./.venv/bin/python naver_clip_test.py go <content_id> # 반자동 (특정 콘텐츠)

반자동 완료(카테고리 선택 + 저장/임시저장 후 Enter) 시,
배포 관리의 '네이버 클립' 상태가 자동으로 성공으로 전환된다.
"""

import asyncio
import os
import sys

from app.db import (
    get_content,
    get_content_gen_params,
    init_db,
    list_content,
    update_platform_status,
)
from app.services.naver_clip import upload_clip


async def main() -> None:
    init_db()
    args = sys.argv[1:]
    handoff = "go" in args
    ids = [a for a in args if a != "go"]
    content = get_content(ids[0]) if ids else (list_content(1) or [None])[0]
    if content is None:
        print("❌ 콘텐츠를 찾을 수 없습니다.")
        return

    mp4 = os.path.abspath(f"data/renders/shortform_{content.id}.mp4")
    if not os.path.exists(mp4):
        print(f"❌ 숏폼 MP4 없음: {mp4}\n   먼저 상세 페이지/앱에서 숏폼 영상을 생성하세요.")
        return

    gp = get_content_gen_params(content.id)
    tags = gp.get("requiredHashtags", []) or []
    print(f"▶ 클립 업로드 {'(반자동)' if handoff else '(dry-run)'}: {content.title[:30]}")
    result = await upload_clip(
        video_path=mp4,
        title=content.title,
        description=(content.body[:80] if content.body else content.title),
        hashtags=tags,
        visibility="private",
        handoff=handoff,
    )
    print(f"\n{'✅' if result.ok else '❌'} {result.message}")
    if result.screenshot:
        print(f"📸 {result.screenshot}")

    # 반자동 업로드 완료 → 배포관리 상태 '성공' 전환
    if handoff and result.ok:
        update_platform_status(content.id, "naver_clip", "success")
        print("✔ 배포 관리: 네이버 클립 → '성공' 으로 전환됨")


if __name__ == "__main__":
    asyncio.run(main())
