# beconti backend (Phase 1)

프론트엔드([../src/lib/api.ts](../src/lib/api.ts))가 호출하는 `localhost:8000` FastAPI 서버.
사진 업로드 → Gemini 멀티모달 분석 → 블로그 초안 + 숏폼 대본 생성 → SQLite 저장 →
네이버 블로그 Playwright 발행까지의 핵심 파이프라인.

## 빠른 시작

```bash
cd backend
./run.sh          # venv 생성 · 의존성 설치 · playwright chromium 설치 · uvicorn 기동
```

최초 1회 자동으로:
- `.venv` 생성 + `requirements.txt` 설치
- `playwright install chromium`
- `.env.example` → `.env` 복사

**GEMINI_API_KEY 가 없어도 동작합니다** — `/api/generate` 가 스텁(더미) 초안을 반환해
프론트 연결/화면 흐름을 바로 확인할 수 있습니다. 실제 AI 결과는 `.env` 에 키를 넣으면 됩니다.

## 엔드포인트 (프론트 계약과 1:1)

| Method | Path | 설명 |
|---|---|---|
| GET  | `/` | 헬스체크 (`pingBackend`) |
| POST | `/api/upload` | 멀티파트 파일 → `{ mediaIds }` |
| POST | `/api/generate` | `{ keywords, tone, mediaIds }` → `GeneratedContent` |
| POST | `/api/publish` | `{ contentId, platforms[] }` → `{ ok }` |
| GET  | `/api/content` | 생성 콘텐츠 목록 (대시보드/배포관리 확장용) |

## 네이버 발행 설정

`.env` 에서:

```
NAVER_CHROME_USER_DATA_DIR=/Users/<you>/Library/Application Support/Google/Chrome
NAVER_CHROME_PROFILE=Default
NAVER_BLOG_ID=<블로그아이디>
PUBLISH_DRY_RUN=true      # 기본 true: 발행 직전까지만 + 스크린샷
PLAYWRIGHT_HEADLESS=false # 매크로는 화면 보이게 권장
```

주의:
- 프로필을 재사용하려면 **해당 프로필로 열린 크롬을 모두 종료**해야 합니다(프로필 잠금).
- 네이버 SmartEditor 셀렉터는 자주 바뀝니다. `PUBLISH_DRY_RUN=true` + headful 로 먼저
  동작을 확인하고, 어긋나면 [app/services/naver.py](app/services/naver.py) 의 `SEL_*` 상수를 조정하세요.
- 실제 발행은 `PUBLISH_DRY_RUN=false` 로 바꾼 뒤에만 일어납니다.

## 구조

```
backend/
  app/
    main.py            FastAPI + CORS + 라우터 등록
    config.py          .env 설정
    models.py          프론트 계약과 맞춘 pydantic 스키마 (camelCase)
    db.py              SQLite (media / content)
    routers/           upload · generate · publish · content
    services/
      storage.py       업로드 저장
      gemini.py        멀티모달 초안 (키 없으면 스텁)
      naver.py         Playwright 네이버 발행
  requirements.txt
  run.sh
```

## Phase 2~4 (예정)

- Phase 2: Claude 대본 정제 → Creatomate 숏폼 렌더
- Phase 3: 워드프레스/인스타 API, 네이버 클립, Pillow EXIF 세탁, 휴먼라이크 고도화
- Phase 4: BackgroundTasks/Celery 큐, 예약 발행, 에러 로그 가시화
