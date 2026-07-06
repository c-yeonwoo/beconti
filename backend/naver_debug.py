#!/usr/bin/env python3
"""장소: 결과 클릭 직후 모달 상태 + 확인버튼 활성 여부 확인."""

import asyncio

from app.config import settings
from app.services import naver
from playwright.async_api import async_playwright

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir, headless=True, no_viewport=True
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.set_viewport_size({"width": 1280, "height": 900})
        await page.goto(WRITE_URL.format(blog_id=settings.naver_blog_id), wait_until="load")
        await asyncio.sleep(3)
        mf = page.frame(name="mainFrame") or page.main_frame
        frame = page.frame_locator(naver.SEL_MAIN_IFRAME)
        await naver._dismiss_draft_popup(mf)
        await frame.locator(naver.SEL_TITLE).first.click()
        await page.keyboard.insert_text("장소 조사")

        await frame.locator(naver.SEL_PLACE_BTN).first.click()
        await asyncio.sleep(2)
        inp = frame.locator(naver.SEL_PLACE_INPUT).first
        await inp.fill("스타벅스 강남대로점")
        await inp.press("Enter")
        await asyncio.sleep(3.5)

        # 첫 결과 클릭
        await frame.locator("a.se-place-map-search-result-link").first.click()
        await asyncio.sleep(1.5)
        await page.screenshot(path="data/renders/dbg_place_click.png")

        # 확인 버튼 상태
        dis = await frame.locator(naver.SEL_PLACE_CONFIRM).first.is_disabled()
        print("확인 버튼 disabled?", dis)
        # 선택 상태 클래스 확인
        sel = await mf.evaluate(
            """() => {
              const on = document.querySelector('.se-place-map-search-result-item.on, .se-place-map-search-result-item[aria-selected=true], .se-place-map-search-result-item--selected');
              const items = document.querySelectorAll('.se-place-map-search-result-item');
              return {selectedFound: !!on, itemCount: items.length, firstCls: items[0]?.className||''};
            }"""
        )
        print("선택상태:", sel)
        print("스크린샷: dbg_place_click.png")
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
