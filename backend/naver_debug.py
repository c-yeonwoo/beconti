#!/usr/bin/env python3
"""SmartEditor 툴바 구조 진단 — '사진' 버튼 셀렉터 찾기."""

import asyncio

from app.config import settings
from playwright.async_api import async_playwright

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir, headless=True, no_viewport=True
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(WRITE_URL.format(blog_id=settings.naver_blog_id), wait_until="load")
        await asyncio.sleep(4)

        frame = page.frame(name="mainFrame") or page.main_frame
        # 툴바 버튼들의 텍스트/클래스/data 속성 덤프
        info = await frame.evaluate(
            """() => {
              const out = [];
              const btns = document.querySelectorAll('button, [role=button]');
              for (const b of btns) {
                const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
                if (!t) continue;
                if (/사진|이미지|동영상|MYBOX/.test(t)) {
                  out.push({
                    text: t.slice(0,20),
                    cls: b.className?.toString().slice(0,80),
                    data: b.getAttribute('data-name') || b.getAttribute('data-log') || b.getAttribute('data-testid') || '',
                    tag: b.tagName,
                  });
                }
              }
              return out;
            }"""
        )
        print("=== 사진/이미지/동영상 관련 버튼 ===")
        for x in info:
            print(x)

        # file input 존재 여부
        n_inputs = await frame.evaluate(
            "() => document.querySelectorAll('input[type=file]').length"
        )
        print(f"\ninput[type=file] 개수: {n_inputs}")
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
