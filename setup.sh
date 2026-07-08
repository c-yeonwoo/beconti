#!/usr/bin/env bash
# beconti 최초 설치 — 한 번만 실행. (macOS 기준, Linux 도 대부분 동작)
# 백엔드(Python/FFmpeg/Playwright) + 프론트(bun) 의존성을 모두 설치한다.
set -uo pipefail
cd "$(dirname "$0")"

RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; NC=$'\e[0m'
ok()   { echo "${GRN}✓${NC} $*"; }
warn() { echo "${YLW}!${NC} $*"; }
err()  { echo "${RED}✗${NC} $*"; }

echo "════════════════════════════════════════"
echo " beconti 설치 시작"
echo "════════════════════════════════════════"

# ── 1. 필수 도구 확인 ────────────────────────────────
MISSING=0

if command -v python3 >/dev/null 2>&1; then
  ok "python3 $(python3 -V 2>&1 | awk '{print $2}')"
else
  err "python3 없음 → https://www.python.org/downloads/ 에서 3.11+ 설치"; MISSING=1
fi

if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg"
else
  warn "ffmpeg 없음 — 숏폼 영상 편집에 필요"
  if command -v brew >/dev/null 2>&1; then
    echo "   → brew 로 설치 시도..."; brew install ffmpeg && ok "ffmpeg 설치됨" || { err "ffmpeg 설치 실패"; MISSING=1; }
  else
    err "   brew 가 없습니다. https://ffmpeg.org/download.html 참고해 설치 후 다시 실행"; MISSING=1
  fi
fi

BUN="$HOME/.bun/bin/bun"
command -v bun >/dev/null 2>&1 && BUN=bun
if "$BUN" --version >/dev/null 2>&1; then
  ok "bun $("$BUN" --version)"
else
  warn "bun 없음 — 프론트엔드 실행에 필요. 설치 시도..."
  curl -fsSL https://bun.sh/install | bash && BUN="$HOME/.bun/bin/bun" && ok "bun 설치됨" \
    || { err "bun 설치 실패 → https://bun.sh 참고"; MISSING=1; }
fi

[ "$MISSING" = "1" ] && { echo; err "필수 도구를 먼저 설치한 뒤 다시 ./setup.sh 를 실행하세요."; exit 1; }

# ── 2. 백엔드 설치 ───────────────────────────────────
echo; echo "▶ 백엔드 의존성 설치..."
cd backend
if [ ! -d ".venv" ]; then python3 -m venv .venv; ok "가상환경 생성"; fi
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -r requirements.txt -q && ok "파이썬 패키지 설치"
./.venv/bin/python -m playwright install chromium >/dev/null 2>&1 && ok "Playwright 크로미움 설치"
if [ ! -f ".env" ]; then cp .env.example .env; ok ".env 생성 (GEMINI_API_KEY / NAVER_BLOG_ID 채우세요)"; else ok ".env 이미 있음"; fi
cd ..

# ── 3. 프론트 설치 ───────────────────────────────────
echo; echo "▶ 프론트엔드 의존성 설치..."
"$BUN" install && ok "프론트 패키지 설치"

# ── 4. 안내 ─────────────────────────────────────────
cat <<EOF

════════════════════════════════════════
 ${GRN}설치 완료!${NC} 다음 3가지만 하면 됩니다:
════════════════════════════════════════

 1) Gemini 키 넣기  (필수)
    → backend/.env 파일 열어 GEMINI_API_KEY= 뒤에 붙여넣기
      (발급: https://aistudio.google.com/apikey)
    → NAVER_BLOG_ID= 뒤에 본인 블로그 아이디도

 2) 네이버 로그인  (최초 1회, 발행하려면)
    cd backend && ./.venv/bin/python naver_login.py
    → 뜬 브라우저에서 네이버 로그인 → 터미널 Enter

 3) 실행
    ./start.sh
    → 브라우저에서  http://localhost:7817  접속

EOF
