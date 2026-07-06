#!/usr/bin/env python3
"""네이버 클립 업로드 테스트. 최신 콘텐츠의 숏폼 MP4를 올린다.

    ./.venv/bin/python naver_clip_test.py          # dry-run (저장 안 함)
    ./.venv/bin/python naver_clip_test.py go       # 실제 저장(비공개)
"""

import asyncio
import os
import sys

from app.db import get_content_place_name, init_db, list_content
from app.services.naver_clip import upload_clip


async def main() -> None:
    init_db()
    c = list_content(1)[0]
    mp4 = os.path.abspath(f"data/renders/shortform_{c.id}.mp4")
    if not os.path.exists(mp4):
        print(f"❌ MP4 없음: {mp4} — 먼저 숏폼을 생성하세요.")
        return

    dry = not (len(sys.argv) > 1 and sys.argv[1] == "go")
    hashtags = [f"#{s.caption.split()[0]}" for s in c.script[:1]] if c.script else []
    tags = ["#먹골역맛집", "#엄마손돼지불백", "#혼밥"]

    print(f"▶ 클립 업로드 {'(dry-run)' if dry else '(실제 저장, 비공개)'}: {c.title[:30]}")
    result = await upload_clip(
        video_path=mp4,
        title=c.title,
        description="먹골역 24시간 든든한 한식 맛집 후기 클립입니다.",
        hashtags=tags,
        category="맛집",
        visibility="private",
        dry_run=dry,
    )
    print(f"\n{'✅' if result.ok else '❌'} {result.message}")
    if result.screenshot:
        print(f"📸 {result.screenshot}")


if __name__ == "__main__":
    asyncio.run(main())
