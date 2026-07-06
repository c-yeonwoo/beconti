#!/usr/bin/env bash
# beconti 로컬 실행 — 백엔드(8000) + 프론트(8080) 동시 기동. Ctrl+C 로 둘 다 종료.
set -uo pipefail
cd "$(dirname "$0")"

BUN="$HOME/.bun/bin/bun"
command -v bun >/dev/null 2>&1 && BUN=bun

echo "▶ 백엔드(localhost:8000) + 프론트(localhost:8080) 기동..."
echo "  브라우저: http://localhost:8080   (종료: Ctrl+C)"

(cd backend && exec ./.venv/bin/uvicorn app.main:app --reload --port 8000) &
BE=$!
("$BUN" run dev) &
FE=$!

trap 'echo; echo "▶ 종료 중..."; kill $BE $FE 2>/dev/null' INT TERM EXIT
wait
