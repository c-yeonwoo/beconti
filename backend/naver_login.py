#!/usr/bin/env python3
"""네이버 전용 프로필 최초 로그인 (1회만).

    ./.venv/bin/python naver_login.py

브라우저가 열리면 네이버에 로그인 → 터미널에서 Enter → 세션 저장.
이후 발행은 이 세션을 재사용한다 (메인 크롬과 독립).
"""

import asyncio

from app.services.naver import open_for_login

if __name__ == "__main__":
    asyncio.run(open_for_login())
