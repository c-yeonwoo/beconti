#!/usr/bin/env python3
"""네이버 발행 dry-run 테스트.

가장 최근 생성 콘텐츠(없으면 샘플)를 네이버 블로그 에디터에 입력하는 데까지
진행한다. PUBLISH_DRY_RUN=true(기본)면 발행하지 않고 스크린샷만 남긴다.

    ./.venv/bin/python naver_test.py
"""

import asyncio
import sys

from app.db import (
    get_content_media_ids,
    get_content_place_name,
    get_media_paths,
    init_db,
    list_content,
)
from app.services.naver import publish_naver_blog


async def main() -> None:
    init_db()
    # 매장명: 명령행 인자 > 저장된 place_name > 테스트 기본값
    place_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    items = list_content(limit=1)
    image_paths: list[str] = []
    place_name = place_arg
    if items:
        c = items[0]
        title, body = c.title, c.body
        image_paths = [p for (p, _mime) in get_media_paths(get_content_media_ids(c.id))]
        place_name = place_name or get_content_place_name(c.id)  # 없으면 장소 생략
        print(f"▶ 최근 생성 콘텐츠 사용: {title} (사진 {len(image_paths)}장, 장소 '{place_name or '없음'}')")
    else:
        title = "beconti 발행 테스트"
        body = "## 테스트\n\n네이버 발행 파이프라인 dry-run 테스트입니다."
        print("▶ 저장된 콘텐츠가 없어 샘플로 진행")

    # 테스트는 항상 비공개(private)로 발행해 실수로 공개되지 않게 함
    result = await publish_naver_blog(
        title, body, image_paths, visibility="private", place_name=place_name
    )
    print(f"\n{'✅' if result.ok else '❌'} {result.message}")
    if result.screenshot:
        print(f"📸 스크린샷: {result.screenshot}")


if __name__ == "__main__":
    asyncio.run(main())
