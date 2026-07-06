"""숏폼 영상 렌더링 엔진.

기본: Creatomate(키 있으면) → 실패/키없음 시 FFmpeg(로컬, 무료) fallback.
FFmpeg 엔진: 사진들을 9:16 세로 슬라이드쇼로 만들고(켄번즈 줌), 대본 자막을
하단에 새겨넣는다. Creatomate 는 키 확보 후 구현(현재는 미구현→fallback).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..config import settings

W, H, FPS = 1080, 1920, 30
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}

FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
    "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
]


def _font_path() -> str | None:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return None


def _parse_duration(time_str: str, default: float = 3.5) -> float:
    """'0-3s' / '3-8s' 형태에서 구간 길이(초) 추출. 실패 시 default."""
    import re

    nums = re.findall(r"\d+(?:\.\d+)?", time_str or "")
    if len(nums) >= 2:
        d = float(nums[1]) - float(nums[0])
        return d if 1.0 <= d <= 12.0 else default
    return default


def _make_caption_png(text: str, out_path: str) -> None:
    """자막 PNG(투명 배경, 흰 글씨 + 반투명 검정 박스) 생성 — 한글 안정 렌더."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = _font_path()
    font = ImageFont.truetype(font_path, 58) if font_path else ImageFont.load_default()

    # 단순 줄바꿈 (글자수 기준)
    max_chars = 16
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars:
            lines.append(cur.strip())
            cur = w
        else:
            cur += " " + w
    if cur.strip():
        lines.append(cur.strip())
    lines = lines[:3] or [""]

    line_h = 76
    total_h = line_h * len(lines)
    y0 = (400 - total_h) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = y0 + i * line_h
        # 반투명 박스
        pad = 16
        draw.rectangle([x - pad, y - 8, x + tw + pad, y + line_h - 12], fill=(0, 0, 0, 140))
        # 외곽선 + 흰 글씨
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
    img.save(out_path)


def _normalize_image(path: str, out_path: str) -> str:
    """HEIC 등 → 표준 JPEG 로 변환 + EXIF 방향 보정 (ffmpeg 호환)."""
    from PIL import Image, ImageOps

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass

    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    im.convert("RGB").save(out_path, "JPEG", quality=90)
    return out_path


def _render_segment(image: str, caption_png: str, duration: float, out_path: str) -> None:
    """이미지 1장 → 9:16 켄번즈 세그먼트 + 자막 오버레이."""
    frames = max(int(duration * FPS), 1)
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"zoompan=z='min(zoom+0.0012,1.12)':d={frames}:s={W}x{H}:fps={FPS}[bg];"
        f"[bg][1:v]overlay=(W-w)/2:H-h-160[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,
        "-i", caption_png,
        "-filter_complex", vf,
        "-map", "[v]",
        "-t", f"{duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_ffmpeg(image_paths: list[str], script: list[dict], out_path: str) -> str:
    """FFmpeg 로 9:16 숏폼 생성. 대본 줄마다 이미지를 순환 배정."""
    images = [p for p in image_paths if Path(p).suffix.lower() in IMG_EXTS]
    if not images:
        raise ValueError("이미지가 없어 숏폼을 만들 수 없습니다.")
    lines = script or [{"caption": "", "time": ""}]

    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        # 이미지들을 표준 JPEG 로 정규화(HEIC 변환·방향 보정)
        norm = [_normalize_image(p, str(tmpd / f"norm_{j}.jpg")) for j, p in enumerate(images)]

        segments: list[str] = []
        for i, line in enumerate(lines):
            img = norm[i % len(norm)]
            cap_png = str(tmpd / f"cap_{i}.png")
            _make_caption_png(str(line.get("caption", "")), cap_png)
            seg = str(tmpd / f"seg_{i}.mp4")
            _render_segment(img, cap_png, _parse_duration(line.get("time", "")), seg)
            segments.append(seg)

        concat_txt = tmpd / "list.txt"
        concat_txt.write_text("".join(f"file '{s}'\n" for s in segments))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
             "-c", "copy", out_path],
            check=True, capture_output=True,
        )
    return out_path


def render_creatomate(image_paths: list[str], script: list[dict], out_path: str) -> str:
    """Creatomate 렌더 (키+템플릿 필요). 미구현 → NotImplementedError 로 fallback 유도."""
    raise NotImplementedError("Creatomate 연동은 키/템플릿 확보 후 구현 예정")


def render_shortform(
    image_paths: list[str], script: list[dict], out_path: str, engine: str | None = None
) -> tuple[str, str]:
    """숏폼 생성. (출력경로, 사용엔진) 반환. Creatomate 우선, 실패 시 FFmpeg."""
    prefer = engine or ("creatomate" if settings.creatomate_api_key else "ffmpeg")
    if prefer == "creatomate":
        try:
            return render_creatomate(image_paths, script, out_path), "creatomate"
        except Exception as e:  # noqa: BLE001
            print(f"Creatomate 실패 → FFmpeg fallback: {e}")
    return render_ffmpeg(image_paths, script, out_path), "ffmpeg"
