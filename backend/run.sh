#!/usr/bin/env bash
# beconti 백엔드 실행. 프론트(src/lib/api.ts)가 기대하는 localhost:8000 에 뜬다.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "▶ 최초 실행: 가상환경 생성 및 의존성 설치"
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
  ./.venv/bin/python -m playwright install chromium
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "▶ .env 생성됨 — GEMINI_API_KEY / NAVER_* 값을 채워주세요 (키 없이도 스텁으로 동작)"
fi

exec ./.venv/bin/uvicorn app.main:app --reload --port 8000
