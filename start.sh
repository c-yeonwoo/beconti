#!/usr/bin/env bash
# beconti 로컬 실행 — 백엔드(8000) + 프론트(7817) 동시 기동. Ctrl+C 로 둘 다 종료.
set -uo pipefail
cd "$(dirname "$0")"

BUN="$HOME/.bun/bin/bun"
command -v bun >/dev/null 2>&1 && BUN=bun

# 최초 설치 여부 점검
if [ ! -d "backend/.venv" ] || [ ! -d "node_modules" ] || [ ! -f "backend/.env" ]; then
  echo "⚠ 설치가 안 된 것 같습니다. 먼저  ./setup.sh  를 실행하세요."
  exit 1
fi

echo "▶ 백엔드(localhost:8000) + 프론트(localhost:7817) 기동..."
echo "  브라우저: http://localhost:7817   (종료: Ctrl+C)"

(cd backend && exec ./.venv/bin/uvicorn app.main:app --reload --port 8000) &
BE=$!
("$BUN" run dev) &
FE=$!

trap 'echo; echo "▶ 종료 중..."; kill $BE $FE 2>/dev/null' INT TERM EXIT
wait
