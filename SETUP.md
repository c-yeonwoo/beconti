# beconti 설치 가이드 (친구용)

사진/영상을 넣으면 AI가 블로그 글·숏폼을 만들어 네이버에 발행해주는 로컬 도구입니다.
**각자 본인 컴퓨터에 설치해서** 씁니다 (데이터·네이버 로그인은 전부 내 PC에만 저장, 서버로 안 나감).

## 준비물 (macOS 기준)

- macOS (Windows는 아직 미검증)
- 인터넷 + 네이버 블로그 계정
- Gemini API 키 (무료) — https://aistudio.google.com/apikey

> Python·FFmpeg·bun 이 없어도 `setup.sh` 가 자동 설치를 시도합니다.
> (Homebrew 가 있으면 가장 매끄럽습니다: https://brew.sh)

## 설치 (3단계)

```bash
# 1. 코드 받기
git clone https://github.com/c-yeonwoo/beconti.git
cd beconti

# 2. 설치 (한 번만)
./setup.sh

# 3. 실행
./start.sh
```

`./setup.sh` 가 끝나면 아래 두 가지만 채우면 됩니다.

### (1) Gemini 키 + 블로그 아이디

`backend/.env` 파일을 열어서:

```
GEMINI_API_KEY=여기에_발급받은_키
NAVER_BLOG_ID=내블로그아이디      # blog.naver.com/[이 부분]
```

### (2) 네이버 로그인 (최초 1회, 발행하려면)

```bash
cd backend
./.venv/bin/python naver_login.py
```
→ 뜬 브라우저에서 네이버 로그인 → 터미널에서 Enter (세션이 내 PC에 저장됨)

## 사용

```bash
./start.sh
```
→ 브라우저에서 **http://localhost:7817** 접속 → 콘텐츠 생성

- **발행 안전장치**: 기본은 `PUBLISH_DRY_RUN=true` (에디터에 입력만, 실제 발행 안 함).
  실제로 올리려면 `backend/.env` 에서 `PUBLISH_DRY_RUN=false` 로 바꾸세요.
- **네이버 클립**: 반자동입니다. `backend` 에서
  `./.venv/bin/python naver_clip_test.py go <콘텐츠ID>` 실행 →
  브라우저에서 카테고리 선택 + 저장 → 터미널 Enter.

## 자주 묻는 것

- **내 데이터 어디 있나요?** `backend/data/` (SQLite + 업로드 파일). 백업하려면 이 폴더 복사.
- **네이버 비번이 서버로 가나요?** 아니요. 네이버 로그인 세션은 **내 PC의 `backend/data/naver-profile`** 에만 있습니다.
- **비용?** Gemini 토큰(콘텐츠 1건당 1회 호출)만. 네이버 발행/클립/사진편집은 전부 무료(로컬).
- **업데이트?** `git pull` 후 `./setup.sh` 다시 한 번.
