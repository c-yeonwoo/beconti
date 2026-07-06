#!/usr/bin/env python3
"""발행 dry-run 후 본문 컴포넌트(텍스트/이미지) 순서를 덤프해 분산 배치 확인."""

import asyncio

from app.config import settings
from app.db import get_content_media_ids, get_media_paths, init_db, list_content
from app.services import naver
from playwright.async_api import async_playwright

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"


async def main() -> None:
    init_db()
    c = list_content(1)[0]
    imgs = [p for (p, _m) in get_media_paths(get_content_media_ids(c.id))]

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir, headless=True, no_viewport=True
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(WRITE_URL.format(blog_id=settings.naver_blog_id), wait_until="load")
        await asyncio.sleep(3)
        frame = page.frame_locator(naver.SEL_MAIN_IFRAME)
        await naver._dismiss_draft_popup(page.frame(name="mainFrame") or page.main_frame)

        # 제목
        await frame.locator(naver.SEL_TITLE).first.click()
        await page.keyboard.insert_text(c.title)
        # 본문 + 사진 분산
        await naver._fill_body(page, frame, c.body, imgs)
        await asyncio.sleep(1)

        # 본문 컴포넌트 순서 덤프
        seq = await (page.frame(name="mainFrame") or page.main_frame).evaluate(
            """() => {
              const comps = document.querySelectorAll('.se-component');
              return Array.from(comps).map(c => {
                if (c.classList.contains('se-image')) return 'IMAGE';
                if (c.classList.contains('se-text')) {
                  const t = (c.innerText||'').replace(/\\s+/g,' ').trim().slice(0,24);
                  return 'TEXT: ' + t;
                }
                return 'OTHER:' + c.className.slice(0,20);
              });
            }"""
        )
        print("=== 본문 컴포넌트 순서 ===")
        for i, s in enumerate(seq):
            print(f"{i:2d}. {s}")
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
