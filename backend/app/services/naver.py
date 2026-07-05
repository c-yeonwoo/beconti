"""네이버 블로그 Playwright 매크로 (Phase 1).

로컬 크롬 프로필을 그대로 로드해 로그인 세션을 재사용하고, SmartEditor ONE
에디터에 제목/본문을 입력한다. 본문은 클립보드 붙여넣기(Ctrl+V) 방식.

⚠️ 주의
- 네이버 에디터 DOM/셀렉터는 수시로 바뀐다. 아래 SEL_* 상수는 실제 화면에
  맞춰 튜닝이 필요할 수 있다 (headful + PUBLISH_DRY_RUN=true 로 먼저 확인).
- 프로필을 쓰려면 해당 프로필로 켜진 크롬을 모두 종료해야 한다 (프로필 잠금).
- PUBLISH_DRY_RUN=true(기본) 면 발행 직전까지만 진행하고 스크린샷을 남긴다.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from ..config import settings

# ─── 셀렉터 (튜닝 대상) ─────────────────────────────────────────────
WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"
SEL_MAIN_IFRAME = "iframe#mainFrame"
SEL_TITLE = ".se-section-documentTitle .se-text-paragraph, .se-documentTitle .se-text-paragraph"
SEL_BODY = ".se-section-text .se-text-paragraph, .se-component-content .se-text-paragraph"
SEL_CANCEL_DRAFT = "button.se-popup-button-cancel"  # "이어서 작성" 팝업 취소
SEL_PUBLISH_OPEN = "button.publish_btn__m9KHH, button[data-testid='publishButton'], .btn_area .publish"
SEL_PUBLISH_CONFIRM = "button.confirm_btn__WEaBq, button[data-testid='seOnePublishBtn']"


class PublishResult:
    def __init__(self, ok: bool, message: str, screenshot: str | None = None) -> None:
        self.ok = ok
        self.message = message
        self.screenshot = screenshot


async def _human_type(target, text: str) -> None:
    """불규칙한 딜레이로 사람처럼 타이핑."""
    for ch in text:
        await target.type(ch, delay=random.uniform(40, 160))
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.15, 0.5))


async def _dismiss_draft_popup(frame) -> None:
    try:
        btn = frame.locator(SEL_CANCEL_DRAFT).first
        if await btn.is_visible(timeout=2500):
            await btn.click()
    except Exception:
        pass  # 팝업이 없으면 무시


async def publish_naver_blog(title: str, body: str) -> PublishResult:
    """네이버 블로그에 글을 작성한다. dry-run 이면 발행하지 않는다."""
    if not settings.naver_user_data_dir or not settings.naver_blog_id:
        return PublishResult(
            ok=False,
            message="NAVER_CHROME_USER_DATA_DIR / NAVER_BLOG_ID 가 .env 에 설정되지 않았습니다.",
        )

    from playwright.async_api import async_playwright

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shot_path = str(settings.render_dir / f"naver-{ts}.png")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir,
            channel="chrome",
            headless=settings.playwright_headless,
            args=[f"--profile-directory={settings.naver_profile}"],
            no_viewport=True,
        )
        try:
            await context.grant_permissions(["clipboard-read", "clipboard-write"])
            page = context.pages[0] if context.pages else await context.new_page()

            await page.goto(WRITE_URL.format(blog_id=settings.naver_blog_id), wait_until="load")
            await asyncio.sleep(random.uniform(2.0, 3.5))

            # 에디터는 iframe 안에 있다
            frame = page.frame_locator(SEL_MAIN_IFRAME)
            await _dismiss_draft_popup(page.frame(name="mainFrame") or page.main_frame)

            # 제목 입력
            title_el = frame.locator(SEL_TITLE).first
            await title_el.click()
            await _human_type(title_el, title)
            await asyncio.sleep(random.uniform(0.5, 1.2))

            # 본문: 클립보드에 넣고 Ctrl+V
            body_el = frame.locator(SEL_BODY).first
            await body_el.click()
            await page.evaluate("(t) => navigator.clipboard.writeText(t)", body)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            modifier = "Meta" if _is_mac() else "Control"
            await page.keyboard.press(f"{modifier}+V")
            await asyncio.sleep(random.uniform(1.0, 2.0))

            await page.screenshot(path=shot_path, full_page=False)

            if settings.publish_dry_run:
                return PublishResult(
                    ok=True,
                    message="DRY-RUN: 제목/본문 입력까지 완료(발행 안 함). 스크린샷 저장됨.",
                    screenshot=shot_path,
                )

            # 실제 발행: 발행 패널 열기 → 확인
            await page.locator(SEL_PUBLISH_OPEN).first.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await page.locator(SEL_PUBLISH_CONFIRM).first.click()
            await asyncio.sleep(random.uniform(2.0, 4.0))

            return PublishResult(ok=True, message="네이버 블로그 발행 완료", screenshot=shot_path)

        except Exception as e:  # noqa: BLE001
            try:
                await page.screenshot(path=shot_path, full_page=False)
            except Exception:
                pass
            return PublishResult(ok=False, message=f"발행 실패: {e}", screenshot=shot_path)
        finally:
            await context.close()


def _is_mac() -> bool:
    import sys

    return sys.platform == "darwin"
