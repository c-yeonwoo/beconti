#!/usr/bin/env python3
"""발행 버튼/발행 패널 구조 조사 (실제 발행 안 함)."""

import asyncio

from app.config import settings
from app.services import naver
from playwright.async_api import async_playwright

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"


async def dump_buttons(ctx_frame, label):
    res = await ctx_frame.evaluate(
        """() => {
          const out = [];
          for (const b of document.querySelectorAll('button, [role=button], a')) {
            const t = (b.innerText || b.getAttribute('aria-label') || '').replace(/\\s+/g,' ').trim();
            if (/발행|공개|예약|비공개|이웃|카테고리/.test(t)) {
              out.push({text: t.slice(0,24), cls: (b.className||'').toString().slice(0,60), data: b.getAttribute('data-testid')||b.getAttribute('data-click-area')||''});
            }
          }
          return out;
        }"""
    )
    print(f"\n=== [{label}] 발행/공개 관련 버튼 ===")
    for x in res:
        print(x)


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir, headless=True, no_viewport=True
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(WRITE_URL.format(blog_id=settings.naver_blog_id), wait_until="load")
        await asyncio.sleep(3)
        mf = page.frame(name="mainFrame") or page.main_frame
        frame = page.frame_locator(naver.SEL_MAIN_IFRAME)
        await naver._dismiss_draft_popup(mf)

        # 최소 내용 입력 (발행 버튼 활성화 위해)
        await frame.locator(naver.SEL_TITLE).first.click()
        await page.keyboard.insert_text("발행 셀렉터 조사용 임시글")
        await frame.locator(naver.SEL_BODY).last.click()
        await page.keyboard.insert_text("임시 본문")
        await asyncio.sleep(1)

        await dump_buttons(mf, "발행 버튼 클릭 전 (iframe)")

        # 발행(패널 열기) 버튼 클릭 시도
        for sel in ["button.publish_btn__m9KHH", "button:has-text('발행')", ".se-toolbar-btn-publish"]:
            try:
                btn = frame.locator(sel).first
                if await btn.is_visible(timeout=1500):
                    print(f"\n▶ 발행 열기 버튼 클릭: {sel}")
                    await btn.click()
                    break
            except Exception as e:
                print(f"  {sel} 실패: {str(e)[:50]}")
        await asyncio.sleep(2)
        await dump_buttons(mf, "발행 패널 열린 후 (iframe)")

        # 공개 설정(라디오/라벨) 덤프
        vis = await mf.evaluate(
            """() => {
              const out = [];
              for (const el of document.querySelectorAll('label, input[type=radio], span, button')) {
                const t = (el.innerText || el.getAttribute('aria-label') || el.value || '').replace(/\\s+/g,' ').trim();
                if (/전체공개|이웃공개|서로이웃|비공개/.test(t)) {
                  out.push({tag: el.tagName, text: t.slice(0,16), cls:(el.className||'').toString().slice(0,50), forId: el.getAttribute('for')||el.id||''});
                }
              }
              return out;
            }"""
        )
        print("\n=== 공개 설정 옵션 ===")
        for x in vis:
            print(x)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
