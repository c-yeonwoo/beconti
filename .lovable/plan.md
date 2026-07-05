
## 목표
Phase 1-1 프롬프트에 명시된 마케팅 자동화 대시보드의 **프론트엔드 UI**만 구축합니다. 실제 AI/배포 로직은 별도 FastAPI 백엔드(`localhost:8000`)가 담당하며, 이 앱은 그 API를 호출하는 클라이언트입니다.

## 라우트 구조 (TanStack Router)
```
src/routes/
  __root.tsx                 → 사이드바 레이아웃 + <Outlet/>
  index.tsx                  → /  (대시보드: 최근 작업 요약)
  create.tsx                 → /create  (콘텐츠 생성 - 메인 화면)
  publish.tsx                → /publish (배포 관리 - 큐/상태 목록)
  settings.tsx               → /settings (API 주소, 플랫폼 계정 상태)
```

## 화면별 구성

### 사이드바 (전역)
- 로고 + 4개 메뉴: 대시보드 / 콘텐츠 생성 / 배포 관리 / 세팅
- 하단에 백엔드 연결 상태 표시(초록/빨강 점 + "localhost:8000")

### 대시보드 `/`
- 카드 4개: 총 생성 콘텐츠, 배포 성공, 배포 실패, 대기 중
- 최근 콘텐츠 리스트(썸네일, 제목, 상태 배지)

### 콘텐츠 생성 `/create` — 핵심 화면
2단계 뷰:
1. **입력 단계**
   - 이미지/영상 Drag & Drop 업로더 (다중 파일, 썸네일 미리보기, 삭제 가능)
   - 핵심 키워드 입력창 (chip 형태로 여러 개 추가)
   - 톤/스타일 셀렉트 (리뷰형/정보형/일상형)
   - "생성하기" 버튼 → `POST /api/generate` 호출
2. **결과 단계 (Split View)**
   - 좌측: 블로그 글 에디터 (제목 + 본문 textarea, 마크다운 지원)
   - 우측: 숏폼 영상 미리보기 자리(placeholder 비디오 플레이어) + 자막/대본 편집 리스트 (`[시간, 자막, 나레이션]` 행 편집)
   - 하단 액션: "저장" / "배포 관리로 보내기" 버튼

### 배포 관리 `/publish`
- 콘텐츠 목록 테이블: 제목 · 생성일 · 플랫폼별 상태 배지(네이버 블로그/클립, 워드프레스, 인스타)
- 각 행에 "발행" / "재시도" 버튼 → `POST /api/publish`
- 상세 drawer에서 로그 확인

### 세팅 `/settings`
- 백엔드 API Base URL 표시(읽기 전용 + 환경변수 안내)
- 플랫폼 계정 연결 상태 목록(네이버, 워드프레스, 인스타) — 표시만
- Playwright 세션 상태 뱃지

## 백엔드 연동 (Axios)
- `src/lib/api.ts` 생성. `axios.create({ baseURL: "http://localhost:8000" })`
- 함수: `uploadMedia(files)` → `/api/upload`, `generateContent(payload)` → `/api/generate`, `publishContent(payload)` → `/api/publish`
- TanStack Query로 감쌈 (mutations 위주)
- 백엔드 미기동 시 에러 토스트 + 대시보드 상태 점 빨강

## 디자인
- shadcn/ui + Tailwind 그대로 활용 (sidebar, card, table, tabs, textarea, badge, drawer, sonner toast)
- 밝고 미니멀한 관리자 톤. 상태 색상: 성공=green, 대기=amber, 실패=destructive

## 이번 Phase에서 하지 않는 것
- 실제 Gemini/Claude/Creatomate 호출 (백엔드 몫)
- Playwright, 네이버 매크로
- Lovable Cloud/DB — 상태는 백엔드가 소유, 프론트는 표시만
- 인증

동의하시면 이대로 구현하겠습니다.
