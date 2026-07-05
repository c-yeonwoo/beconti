#!/usr/bin/env python3
"""로컬 서버(localhost:8000)에 사진을 넣어 생성 결과를 확인하는 테스트 CLI.

사용법:
    ./.venv/bin/python try.py "키워드" 사진1.jpg 사진2.jpg ...
    ./.venv/bin/python try.py "성수동 감성 카페" ~/Desktop/cafe/*.jpg

폴더를 주면 그 안의 이미지들을 자동으로 집는다:
    ./.venv/bin/python try.py "성수동 카페" ~/Desktop/cafe
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}


def collect(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        pp = Path(p).expanduser()
        if pp.is_dir():
            out += sorted(f for f in pp.iterdir() if f.suffix.lower() in IMG_EXTS | VIDEO_EXTS)
        elif pp.exists():
            out.append(pp)
        else:
            print(f"⚠️  없는 경로 건너뜀: {pp}")
    return out


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    keyword = sys.argv[1]
    files = collect(sys.argv[2:])
    if not files:
        print("❌ 넣을 사진/영상을 못 찾았습니다.")
        sys.exit(1)

    print(f"📷 파일 {len(files)}개, 키워드: '{keyword}'\n" + "\n".join(f"   - {f.name}" for f in files))

    with httpx.Client(base_url=BASE, timeout=180) as c:
        try:
            c.get("/")
        except Exception:
            print("❌ 백엔드(localhost:8000)에 연결 안 됨. 서버가 켜져 있는지 확인하세요.")
            sys.exit(1)

        print("\n⬆️  업로드 중...")
        multipart = [("files", (f.name, f.read_bytes())) for f in files]
        up = c.post("/api/upload", files=multipart).raise_for_status().json()
        media_ids = up["mediaIds"]

        print("✨ 생성 중 (Gemini 분석)... 20초 내외 소요")
        r = c.post("/api/generate", json={"keywords": [keyword], "tone": "review", "mediaIds": media_ids})
        r.raise_for_status()
        d = r.json()

    print("\n" + "=" * 60)
    print("📝 제목:", d["title"])
    print("=" * 60)
    print(d["body"])
    print("\n" + "-" * 60)
    print("🎬 숏폼 대본")
    print("-" * 60)
    for line in d["script"]:
        print(f"  [{line['time']}] {line['caption']}")
        print(f"      🎙️  {line['narration']}")
    print(f"\n✅ 저장됨 (contentId={d['id']}) — 배포 관리에서 조회 가능")


if __name__ == "__main__":
    main()
