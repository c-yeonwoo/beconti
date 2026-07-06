"""네이버 블로그 Playwright 매크로 (Phase 1).

**전용 프로필 방식**: settings.naver_user_data_dir(기본 data/naver-profile)에
Playwright 번들 크로미움으로 로그인 세션을 저장/재사용한다. 메인 크롬과 독립이라
매번 크롬을 닫을 필요가 없다. 최초 1회만 `python naver_login.py` 로 네이버 로그인.

본문은 클립보드 붙여넣기(Ctrl/Cmd+V) 방식.

⚠️ 네이버 SmartEditor 셀렉터는 수시로 바뀐다. SEL_* 는 실제 화면에 맞춰
튜닝이 필요할 수 있다(headful + PUBLISH_DRY_RUN=true 로 먼저 확인).
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timezone

from ..config import settings

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"
LOGIN_URL = "https://nid.naver.com/nidlogin.login"

# ─── 셀렉터 (튜닝 대상) ─────────────────────────────────────────────
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


def _is_mac() -> bool:
    return sys.platform == "darwin"


async def _human_type(target, text: str) -> None:
    """불규칙한 딜레이로 사람처럼 타이핑."""
    for ch in text:
        await target.type(ch, delay=random.uniform(40, 160))
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.15, 0.5))


def _md_to_plain(md: str) -> list[str]:
    """마크다운을 SmartEditor 본문용 문단 리스트로 정리.

    ## 소제목, **강조**, [사진 N] 표기 등을 눈에 거슬리지 않는 평문으로 변환.
    빈 줄 기준으로 문단을 나눈다.
    """
    import re

    lines: list[str] = []
    for raw in md.splitlines():
        line = raw.rstrip()
        line = re.sub(r"^#{1,6}\s+", "", line)      # 헤딩 마커 제거 (# 뒤 공백일 때만 → 해시태그 보존)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)  # 볼드 제거
        line = re.sub(r"^[-*]\s+", "• ", line)         # 리스트 불릿
        lines.append(line)
    # 연속 빈 줄은 하나로
    out: list[str] = []
    for line in lines:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)
    return out or [""]


async def _fill_body(page, body_el, body: str) -> None:
    """본문 영역에 포커스 후 문단 단위로 입력 (insert_text 기반, 안정적)."""
    await body_el.click()
    await asyncio.sleep(random.uniform(0.3, 0.7))
    paragraphs = _md_to_plain(body)
    for i, para in enumerate(paragraphs):
        if para:
            await page.keyboard.insert_text(para)
        if i < len(paragraphs) - 1:
            await page.keyboard.press("Enter")
            await asyncio.sleep(random.uniform(0.02, 0.12))


async def _dismiss_draft_popup(frame) -> None:
    try:
        btn = frame.locator(SEL_CANCEL_DRAFT).first
        if await btn.is_visible(timeout=2500):
            await btn.click()
    except Exception:
        pass  # 팝업 없으면 무시


def _is_logged_out(url: str) -> bool:
    return "nidlogin" in url or "nid.naver.com" in url


async def open_for_login() -> None:
    """최초 1회: 전용 프로필로 네이버 로그인 페이지를 열고, 로그인 후 Enter 대기.

    persistent context 라 로그인하면 세션이 프로필에 저장돼 이후 재사용된다.
    """
    from playwright.async_api import async_playwright

    settings.ensure_dirs()
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir,
            headless=False,
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(LOGIN_URL, wait_until="load")
        print("\n▶ 열린 브라우저에서 네이버에 로그인하세요.")
        print("  로그인 완료 후, 이 터미널에서 Enter 를 누르면 세션이 저장됩니다.")
        await asyncio.get_event_loop().run_in_executor(None, input)
        await context.close()
        print("✓ 세션 저장 완료. 이제 발행 테스트를 쓸 수 있습니다.")


async def publish_naver_blog(title: str, body: str) -> PublishResult:
    """네이버 블로그에 글 작성. dry-run 이면 발행하지 않고 스크린샷만."""
    if not settings.naver_blog_id:
        return PublishResult(ok=False, message="NAVER_BLOG_ID 가 .env 에 설정되지 않았습니다.")

    from playwright.async_api import async_playwright

    settings.ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shot_path = str(settings.render_dir / f"naver-{ts}.png")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir,
            headless=settings.playwright_headless,
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await context.grant_permissions(["clipboard-read", "clipboard-write"])
            await page.goto(WRITE_URL.format(blog_id=settings.naver_blog_id), wait_until="load")
            await asyncio.sleep(random.uniform(2.0, 3.5))

            if _is_logged_out(page.url):
                return PublishResult(
                    ok=False,
                    message="네이버 로그인 세션이 없습니다. `python naver_login.py` 로 먼저 로그인하세요.",
                )

            frame = page.frame_locator(SEL_MAIN_IFRAME)
            await _dismiss_draft_popup(page.frame(name="mainFrame") or page.main_frame)

            title_el = frame.locator(SEL_TITLE).first
            await title_el.click()
            await _human_type(title_el, title)
            await asyncio.sleep(random.uniform(0.5, 1.2))

            body_el = frame.locator(SEL_BODY).last
            await _fill_body(page, body_el, body)
            await asyncio.sleep(random.uniform(1.0, 2.0))

            await page.screenshot(path=shot_path, full_page=False)

            if settings.publish_dry_run:
                return PublishResult(
                    ok=True,
                    message="DRY-RUN: 제목/본문 입력까지 완료(발행 안 함). 스크린샷 저장됨.",
                    screenshot=shot_path,
                )

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
