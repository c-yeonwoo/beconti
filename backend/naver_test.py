#!/usr/bin/env python3
"""네이버 발행 dry-run 테스트.

가장 최근 생성 콘텐츠(없으면 샘플)를 네이버 블로그 에디터에 입력하는 데까지
진행한다. PUBLISH_DRY_RUN=true(기본)면 발행하지 않고 스크린샷만 남긴다.

    ./.venv/bin/python naver_test.py
"""

import asyncio

from app.db import init_db, list_content
from app.services.naver import publish_naver_blog


async def main() -> None:
    init_db()
    items = list_content(limit=1)
    if items:
        c = items[0]
        title, body = c.title, c.body
        print(f"▶ 최근 생성 콘텐츠 사용: {title}")
    else:
        title = "beconti 발행 테스트"
        body = "## 테스트\n\n네이버 발행 파이프라인 dry-run 테스트입니다.\n\n[사진 1]"
        print("▶ 저장된 콘텐츠가 없어 샘플로 진행")

    result = await publish_naver_blog(title, body)
    print(f"\n{'✅' if result.ok else '❌'} {result.message}")
    if result.screenshot:
        print(f"📸 스크린샷: {result.screenshot}")


if __name__ == "__main__":
    asyncio.run(main())
