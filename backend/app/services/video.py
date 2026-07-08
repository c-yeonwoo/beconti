"""숏폼 영상 렌더링 엔진.

기본: Creatomate(키 있으면) → 실패/키없음 시 FFmpeg(로컬, 무료) fallback.
FFmpeg 엔진: 사진들을 9:16 세로 슬라이드쇼로 만들고(켄번즈 줌), 대본 자막을
하단에 새겨넣는다. Creatomate 는 키 확보 후 구현(현재는 미구현→fallback).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from ..config import settings

W, H, FPS = 1080, 1920, 30
MIN_TOTAL_SEC = 30.0  # 숏폼 최소 길이 (체험단 규칙: 30초 이상)
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}

# 이모지/그림문자 제거 (자막 폰트에서 깨짐)
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U0000FE00-\U0000FE0F\U00002190-\U000021FF\U00002B00-\U00002BFF]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text or "").strip()

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

    text = _strip_emoji(text)  # 자막에서 깨지는 이모지 제거
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


def _probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", path],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def extract_video_frames(video_path: str, out_dir: str, n: int = 6) -> list[str]:
    """영상에서 균등 간격으로 n장 프레임 추출(가로 768px 축소) → jpg 경로 목록.

    Gemini 가 영상 '내용'을 보고 글/대본을 쓰게 하기 위한 가벼운 방법.
    """
    dur = _probe_duration(video_path) or 1.0
    n = max(1, min(n, 8))
    step = dur / (n + 1)
    out: list[str] = []
    for i in range(1, n + 1):
        t = step * i
        p = str(Path(out_dir) / f"vframe_{Path(video_path).stem}_{i}.jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", video_path,
                 "-frames:v", "1", "-vf", "scale=768:-1", p],
                check=True, capture_output=True,
            )
            if Path(p).exists():
                out.append(p)
        except Exception:
            continue
    return out


def _has_audio(path: str) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    ).stdout.strip()
    return bool(out)


def _normalize_video(path: str, out_path: str) -> str:
    """영상 → 9:16 1080x1920, 30fps, h264+aac 로 통일 (오디오 없으면 무음 추가)."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"
    if _has_audio(path):
        cmd = [
            "ffmpeg", "-y", "-i", path, "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            out_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", path,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", vf, "-map", "0:v", "-map", "1:a", "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            out_path,
        ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def _find_bgm() -> str | None:
    """data/bgm/ 에 있는 첫 음원 파일. 없으면 None."""
    if not settings.bgm_dir.exists():
        return None
    for f in sorted(settings.bgm_dir.iterdir()):
        if f.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}:
            return str(f)
    return None


def _mix_audio(video_in: str, narration: list[tuple[str, float]], bgm: str | None,
               duration: float, out_path: str) -> None:
    """영상(자막 포함)에 나레이션 TTS + 배경음 + 원본소리(약하게)를 믹스."""
    inputs = ["-i", video_in]
    filt = [f"[0:a]volume={settings.orig_audio_volume}[oa]"]
    labels = ["[oa]"]
    idx = 1
    for mp3, start in narration:
        inputs += ["-i", mp3]
        ms = max(int(start * 1000), 0)
        filt.append(f"[{idx}:a]adelay={ms}|{ms},volume={settings.narration_volume}[n{idx}]")
        labels.append(f"[n{idx}]")
        idx += 1
    if bgm:
        inputs += ["-stream_loop", "-1", "-i", bgm]
        filt.append(
            f"[{idx}:a]volume={settings.bgm_volume},atrim=0:{duration:.2f},"
            f"asetpts=PTS-STARTPTS[bg]"
        )
        labels.append("[bg]")
        idx += 1
    filt.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[aout]")
    subprocess.run(
        ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filt),
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-t", f"{duration:.2f}", out_path],
        check=True, capture_output=True,
    )


def render_from_videos(video_paths: list[str], script: list[dict], out_path: str) -> str:
    """실촬영 영상 → 9:16 정규화·이어붙이기 + 자막 + (TTS 내레이션 + 배경음) 믹스."""
    from . import tts

    lines = script or []
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        norm = [_normalize_video(v, str(tmpd / f"nv_{j}.mp4")) for j, v in enumerate(video_paths)]

        # 이어붙이기 (동일 코덱이라 copy 가능)
        base = norm[0]
        if len(norm) > 1:
            base = str(tmpd / "base.mp4")
            lst = tmpd / "list.txt"
            lst.write_text("".join(f"file '{s}'\n" for s in norm))
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", base],
                check=True, capture_output=True,
            )

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        dur = _probe_duration(base) or MIN_TOTAL_SEC
        win = dur / max(len(lines), 1)

        # 1) 자막 오버레이 (라인별 시간창)
        capped = str(tmpd / "capped.mp4")
        overlay_inputs, chains, cur, n_png = ["-i", base], [], "0:v", 0
        for i, line in enumerate(lines):
            cap = _strip_emoji(str(line.get("caption", "")))
            if not cap:
                continue
            n_png += 1
            png = str(tmpd / f"cap_{i}.png")
            _make_caption_png(cap, png)
            overlay_inputs += ["-i", png]
            s, e = i * win, (i + 1) * win
            nxt = f"v{n_png}"
            chains.append(
                f"[{cur}][{n_png}:v]overlay=(W-w)/2:H-h-180:enable='between(t,{s:.2f},{e:.2f})'[{nxt}]"
            )
            cur = nxt
        if chains:
            subprocess.run(
                ["ffmpeg", "-y", *overlay_inputs, "-filter_complex", ";".join(chains),
                 "-map", f"[{cur}]", "-map", "0:a?",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", capped],
                check=True, capture_output=True,
            )
        else:
            capped = base

        # 2) 나레이션 TTS (라인별, 자막과 같은 시간창 시작점)
        narration: list[tuple[str, float]] = []
        if tts.is_enabled():
            for i, line in enumerate(lines):
                txt = _strip_emoji(str(line.get("narration", "")))
                if not txt:
                    continue
                mp3 = str(tmpd / f"tts_{i}.mp3")
                if tts.synthesize(txt, mp3):
                    narration.append((mp3, i * win))

        # 3) 배경음 + 믹스
        bgm = _find_bgm()
        if not narration and not bgm:
            if capped != out_path:
                subprocess.run(["ffmpeg", "-y", "-i", capped, "-c", "copy", out_path],
                               check=True, capture_output=True)
            return out_path

        _mix_audio(capped, narration, bgm, dur, out_path)
    return out_path


def render_ffmpeg(image_paths: list[str], script: list[dict], out_path: str) -> str:
    """FFmpeg 로 9:16 숏폼 생성. 영상이 있으면 영상 편집, 없으면 사진 슬라이드쇼."""
    videos = [p for p in image_paths if Path(p).suffix.lower() in VIDEO_EXTS]
    if videos:
        # 실촬영 영상 우선 (체험단 클립 규칙: 사진 편집 영상 불가)
        return render_from_videos(videos, script, out_path)

    images = [p for p in image_paths if Path(p).suffix.lower() in IMG_EXTS]
    if not images:
        raise ValueError("이미지·영상이 없어 숏폼을 만들 수 없습니다.")
    lines = script or [{"caption": "", "time": ""}]

    # 각 컷 길이 계산 후, 전체가 30초 미만이면 30초 이상이 되도록 균등 확대
    durations = [_parse_duration(line.get("time", "")) for line in lines]
    total = sum(durations) or 1.0
    if total < MIN_TOTAL_SEC:
        scale = MIN_TOTAL_SEC / total
        durations = [d * scale for d in durations]

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
            _render_segment(img, cap_png, round(durations[i], 2), seg)
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
