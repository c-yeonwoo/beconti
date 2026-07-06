"""네이버 클립 반자동 업로드 (Creator Studio 2.0, creator.tv.naver.com).

만들기 → 클립 업로드 → 파일 선택(MP4) → 제목/설명/태그/공개범위 자동 입력 →
카테고리(필수 커스텀 드롭다운)는 플레이어 오버레이에 막혀 자동화 불가 →
사용자가 열린 브라우저에서 카테고리 선택 + 저장(핸드오프).
전용 네이버 프로필 세션 재사용(블로그와 동일). LLM 비용 0.

⚠️ 셀렉터는 네이버 UI 변경 시 튜닝 필요.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..config import settings

STUDIO_URL = "https://creator.tv.naver.com/"
OPEN_TYPE = {"public": "open", "private": "private"}


class ClipResult:
    def __init__(self, ok: bool, message: str, screenshot: str | None = None) -> None:
        self.ok = ok
        self.message = message
        self.screenshot = screenshot


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
    visibility: str = "private",
    handoff: bool = True,
) -> ClipResult:
    """네이버 클립 반자동 업로드.

    자동: 파일 업로드 + 제목 + 설명/태그 + (best-effort)공개범위.
    수동(handoff): 카테고리(필수 커스텀 드롭다운)는 플레이어 오버레이에 막혀
      자동화 불가 → 사용자가 열린 브라우저에서 카테고리 선택 + 저장.
    handoff=False 면 폼만 채우고 스크린샷(저장 안 함).
    """
    from playwright.async_api import async_playwright

    hashtags = hashtags or []
    title = (title or "무제")[:24]
    desc = _build_description(description, hashtags, title)
    open_val = OPEN_TYPE.get(visibility, "private")

    settings.ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shot = str(settings.render_dir / f"clip-{ts}.png")
    # 핸드오프는 사용자가 화면을 봐야 하므로 headful 강제
    headless = False if handoff else settings.playwright_headless

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=settings.naver_user_data_dir,
            headless=headless,
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

            # 제목 / 설명 / 태그
            await title_in.fill(title)
            await pg.locator("textarea[name='clipDescription']").fill(desc)
            await asyncio.sleep(0.5)

            # 공개범위 (best-effort)
            try:
                await pg.locator(
                    f"label:has(input[name='openType'][value='{open_val}'])"
                ).first.click()
                await asyncio.sleep(0.4)
            except Exception:
                pass

            await pg.screenshot(path=shot, full_page=True)

            if not handoff:
                return ClipResult(True, "폼 입력 완료(저장 안 함). 카테고리·저장은 수동 필요.", shot)

            # 핸드오프: 사용자가 브라우저에서 카테고리 선택 + 저장
            print("\n" + "=" * 56)
            print("▶ 열린 브라우저 창에서 아래를 직접 해주세요:")
            print("   1) '카테고리 설정' 에서 1차/2차 카테고리 선택")
            print("   2) 공개범위 확인 (기본: 비공개)")
            print("   3) '저장' 버튼 클릭")
            print("   완료 후 이 터미널에서 Enter")
            print("=" * 56)
            await asyncio.get_event_loop().run_in_executor(None, input)
            return ClipResult(True, "반자동 업로드 완료(제목·설명·태그 자동 + 카테고리·저장 수동)", shot)

        except Exception as e:  # noqa: BLE001
            try:
                await pg.screenshot(path=shot, full_page=True)
            except Exception:
                pass
            return ClipResult(False, f"클립 업로드 실패: {e}", shot)
        finally:
            await ctx.close()
