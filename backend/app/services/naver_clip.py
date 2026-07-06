"""네이버 클립 업로드 (Creator Studio 2.0, creator.tv.naver.com).

만들기 → 클립 업로드 → 파일 선택(MP4) → 인코딩 대기 → 제목/설명/카테고리/공개범위 → 저장.
전용 네이버 프로필 세션 재사용(블로그와 동일). LLM 비용 0.

⚠️ 셀렉터는 네이버 UI 변경 시 튜닝 필요.
"""

from __future__ import annotations

import asyncio
import random
import re
from datetime import datetime, timezone

from ..config import settings

STUDIO_URL = "https://creator.tv.naver.com/"

# 콘텐츠 카테고리 → 네이버 클립 1차 카테고리
CATEGORY_MAP = {
    "맛집": "푸드", "음식": "푸드", "카페": "푸드", "디저트": "푸드", "푸드": "푸드",
    "여행": "여행", "뷰티": "뷰티", "패션": "패션", "리빙": "리빙, 홈", "홈": "리빙, 홈",
    "동물": "동물", "반려": "동물", "과학": "과학", "음악": "음악", "미술": "미술",
}
DEFAULT_CATEGORY = "푸드"
OPEN_TYPE = {"public": "open", "private": "private"}


class ClipResult:
    def __init__(self, ok: bool, message: str, screenshot: str | None = None) -> None:
        self.ok = ok
        self.message = message
        self.screenshot = screenshot


async def _pick_dropdown(pg, dropdown_label: str, option_text: str | None) -> bool:
    """카테고리 드롭다운을 열고 옵션 선택. option_text=None 이면 첫 옵션.

    옵션은 role=button + 정확한 텍스트(get_by_role)로 클릭 (li 클릭은 미작동).
    """
    try:
        await pg.get_by_text(dropdown_label, exact=True).first.click()
        await asyncio.sleep(1.2)
        # 비디오 플레이어 오버레이가 클릭을 가로채므로 pointer-events 무력화
        await pg.evaluate(
            "() => document.querySelectorAll('.pzp-ui-dimmed,.pzp-dimmed,.pzp-pc__dimmed,.pzp')"
            ".forEach(e => { e.style.pointerEvents='none'; })"
        )
        if option_text:
            opt = pg.locator(
                "button.Dropdown_button_depth_item___Wygz",
                has_text=re.compile(rf"^{re.escape(option_text)}$"),
            ).first
        else:
            opt = pg.locator("button.Dropdown_button_depth_item___Wygz").first
        await opt.wait_for(state="visible", timeout=4000)
        await opt.click(timeout=4000)
        await asyncio.sleep(0.8)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ 드롭다운({dropdown_label}→{option_text}) 실패: {str(e)[:50]}")
        return False


async def _select_file(pg, path: str) -> None:
    async with pg.expect_file_chooser(timeout=8000) as fc:
        await pg.get_by_text("파일 선택", exact=True).first.click()
    chooser = await fc.value
    await chooser.set_files(path)


def _build_description(description: str, hashtags: list[str], title: str) -> str:
    desc = (description or "").strip()
    if hashtags:
        desc = (desc + "\n" + " ".join(hashtags)).strip()
    if len(desc) < 10:
        desc = (desc + " " + title + " 클립").strip()
    return desc[:200]


async def upload_clip(
    video_path: str,
    title: str,
    description: str = "",
    hashtags: list[str] | None = None,
    category: str = "",
    visibility: str = "private",
    dry_run: bool = True,
) -> ClipResult:
    """네이버 클립 업로드. dry_run 이면 저장 직전까지만(스크린샷)."""
    from playwright.async_api import async_playwright

    hashtags = hashtags or []
    cat = CATEGORY_MAP.get((category or "").strip(), DEFAULT_CATEGORY)
    title = (title or "무제")[:24]
    desc = _build_description(description, hashtags, title)
    open_val = OPEN_TYPE.get(visibility, "private")

    settings.ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shot = str(settings.render_dir / f"clip-{ts}.png")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir,
            headless=settings.playwright_headless,
            no_viewport=True,
        )
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            await pg.goto(STUDIO_URL, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            if "nidlogin" in pg.url:
                return ClipResult(False, "네이버 로그인 필요: python naver_login.py")

            await pg.get_by_text("만들기", exact=True).first.click()
            await asyncio.sleep(1)
            await pg.get_by_text("클립 업로드", exact=True).first.click()
            await asyncio.sleep(2)

            await _select_file(pg, video_path)
            title_in = pg.locator("input[name='clipTitle']")
            try:
                await title_in.wait_for(state="visible", timeout=25000)
            except Exception:
                await _select_file(pg, video_path)  # 한 번 재시도
                await title_in.wait_for(state="visible", timeout=25000)
            await asyncio.sleep(1.5)

            # 제목 / 설명
            await title_in.fill(title)
            await pg.locator("textarea[name='clipDescription']").fill(desc)
            await asyncio.sleep(0.5)

            # 카테고리 (1차 필수) — 드롭다운 열고 옵션 스크롤·클릭
            await _pick_dropdown(pg, "1차 카테고리", cat)
            # 2차 카테고리 (첫 옵션)
            await _pick_dropdown(pg, "2차 카테고리", None)

            # 공개범위
            try:
                await pg.locator(
                    f"label:has(input[name='openType'][value='{open_val}'])"
                ).first.click()
                await asyncio.sleep(0.4)
            except Exception:
                pass

            # 인코딩 완료 + 저장 버튼 활성화 대기 (최대 ~3분)
            save = pg.locator(
                "button.VideoDetailModal_button_save__gSwLV, button:has-text('저장')"
            ).first
            enabled = False
            for _ in range(90):
                await asyncio.sleep(2)
                try:
                    if not await save.is_disabled():
                        enabled = True
                        break
                except Exception:
                    pass

            await pg.screenshot(path=shot, full_page=True)
            vis_ko = {"public": "공개", "private": "비공개"}

            if dry_run:
                return ClipResult(
                    True,
                    f"DRY-RUN: 폼 입력 완료(저장 안 함). 저장버튼 활성={enabled}, 공개범위={vis_ko.get(visibility)}",
                    shot,
                )

            if not enabled:
                return ClipResult(False, "저장 버튼이 활성화되지 않음(인코딩/필수항목 확인)", shot)

            await save.click()
            await asyncio.sleep(4)
            await pg.screenshot(path=shot, full_page=True)
            return ClipResult(True, f"클립 업로드 완료 (공개범위: {vis_ko.get(visibility)})", shot)

        except Exception as e:  # noqa: BLE001
            try:
                await pg.screenshot(path=shot, full_page=True)
            except Exception:
                pass
            return ClipResult(False, f"클립 업로드 실패: {e}", shot)
        finally:
            await ctx.close()
