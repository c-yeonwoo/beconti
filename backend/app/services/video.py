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


# 자막 스타일: (글자크기, 글자색, 외곽선색, 외곽선두께, 박스색 or None, 글로우색 or None)
CAPTION_STYLES = {
    "basic": (58, (255, 255, 255, 255), (0, 0, 0, 255), 6, (0, 0, 0, 150), None),
    "yellow": (72, (255, 231, 64, 255), (0, 0, 0, 255), 12, None, None),
    "neon": (68, (176, 255, 92, 255), (10, 40, 10, 255), 10, None, (120, 255, 90, 200)),
}


def _make_caption_png(text: str, out_path: str, style: str = "basic") -> None:
    """자막 PNG(투명 배경) 생성. style: basic | yellow | neon."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    size, fill, stroke, stroke_w, box, glow = CAPTION_STYLES.get(style, CAPTION_STYLES["basic"])
    font_path = _font_path()
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    text = _strip_emoji(text)
    max_chars = max(10, int(16 * 58 / size))
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

    line_h = int(size * 1.32)
    total_h = line_h * len(lines)
    canvas_h = max(400, total_h + 60)
    img = Image.new("RGBA", (W, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y0 = (canvas_h - total_h) // 2

    def _pos(line):
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)
        return (W - (bbox[2] - bbox[0])) // 2

    # 박스 스타일
    if box:
        for i, line in enumerate(lines):
            x, y = _pos(line), y0 + i * line_h
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            draw.rounded_rectangle(
                [x - 20, y - 6, x + tw + 20, y + line_h - 10], radius=14, fill=box
            )

    # 네온 글로우 (별도 레이어 블러 후 합성)
    if glow:
        gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        for i, line in enumerate(lines):
            gd.text((_pos(line), y0 + i * line_h), line, font=font, fill=glow,
                    stroke_width=stroke_w + 6, stroke_fill=glow)
        gl = gl.filter(ImageFilter.GaussianBlur(10))
        img.alpha_composite(gl)

    # 본 텍스트 (외곽선 + 채움)
    for i, line in enumerate(lines):
        draw.text((_pos(line), y0 + i * line_h), line, font=font,
                  fill=fill, stroke_width=stroke_w, stroke_fill=stroke)
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


def extract_video_frames(video_path: str, out_dir: str, n: int = 6, width: int = 768) -> list[str]:
    """영상에서 균등 간격으로 n장 프레임 추출 → jpg 경로 목록.

    Gemini 분석용은 작게(768), 블로그 사진용은 크게(예: 1280) 쓴다.
    width<=0 이면 원본 해상도.
    """
    dur = _probe_duration(video_path) or 1.0
    n = max(1, min(n, 12))
    step = dur / (n + 1)
    vf = f"scale={width}:-1" if width and width > 0 else None
    out: list[str] = []
    for i in range(1, n + 1):
        t = step * i
        p = str(Path(out_dir) / f"vframe_{Path(video_path).stem}_{i}.jpg")
        cmd = ["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", video_path, "-frames:v", "1"]
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-q:v", "3", p]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if Path(p).exists():
                out.append(p)
        except Exception:
            continue
    return out


def extract_frame_at(video_path: str, t: float, out_path: str, width: int = 768) -> bool:
    """영상의 특정 시점(초) 프레임 1장 추출."""
    cmd = ["ffmpeg", "-y", "-ss", f"{max(t, 0):.2f}", "-i", video_path, "-frames:v", "1"]
    if width and width > 0:
        cmd += ["-vf", f"scale={width}:-1"]
    cmd += ["-q:v", "3", out_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return Path(out_path).exists()
    except Exception:
        return False


def detect_scene_cuts(video_path: str, threshold: float = 0.35) -> list[float]:
    """ffmpeg 장면전환 감지 → 컷 발생 시점(초) 목록."""
    proc = subprocess.run(
        ["ffmpeg", "-i", video_path, "-filter:v", f"select='gt(scene,{threshold})',showinfo",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", proc.stderr)]


def build_scene_segments(
    duration: float, video_path: str, min_seg: float = 3.0, max_seg: float = 5.5
) -> list[tuple[float, float]]:
    """나레이션이 여유 있게(약 3~5초) 들어갈 구간을 만든다.

    모든 화면전환마다 끊지 않는다 — 장면전환 시점을 "괜찮은 끊는 지점" 후보로만
    쓰고, 목표 길이(min~max) 범위 안에 후보가 있으면 그 지점에서 끊어 자연스럽게
    이어지도록 하고, 없으면 목표 길이에서 그냥 자른다. 구간 길이가 고르므로
    나레이션 배속 편차(짧은 구간 때문에 확 빨라지는 문제)도 줄어든다.
    """
    if duration <= 0:
        return [(0.0, MIN_TOTAL_SEC)]

    candidates: set[float] = set()
    for threshold in (0.3, 0.4, 0.5):
        candidates.update(detect_scene_cuts(video_path, threshold))
    cuts = sorted(c for c in candidates if 0 < c < duration)

    segments: list[tuple[float, float]] = []
    start = 0.0
    target = (min_seg + max_seg) / 2
    while start < duration - 0.5:
        window = [c for c in cuts if start + min_seg <= c <= start + max_seg]
        if window:
            end = min(window, key=lambda c: abs(c - (start + target)))
        else:
            end = min(start + max_seg, duration)
        if duration - end < min_seg:  # 마지막 자투리는 직전 구간에 합침
            end = duration
        segments.append((start, end))
        start = end

    return segments or [(0.0, duration)]


def compute_script_segments(video_paths: list[str]) -> list[dict]:
    """영상(들)의 실제 장면전환 기준 구간 목록. 콘텐츠 순서대로 누적 시간 오프셋 부여.

    generate(분석)와 render(타이밍) 양쪽에서 동일 입력에 결정적으로 같은 결과를 내
    대본 줄 수와 실제 영상 구간이 1:1로 맞물리게 한다.
    """
    segments: list[dict] = []
    offset = 0.0
    for v in video_paths:
        dur = _probe_duration(v)
        if dur <= 0:
            continue
        for s, e in build_scene_segments(dur, v):
            segments.append(
                {"video": v, "local_start": s, "local_end": e, "start": s + offset, "end": e + offset}
            )
        offset += dur
    return segments


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


def _speed_audio(in_path: str, factor: float, out_path: str) -> None:
    """오디오를 factor 배속으로. ffmpeg atempo 는 1개당 0.5~2.0 범위라 필요시 체인."""
    factor = max(0.5, min(factor, 4.0))
    filters, f = [], factor
    while f > 2.0:
        filters.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        filters.append("atempo=0.5")
        f /= 0.5
    filters.append(f"atempo={f:.4f}")
    subprocess.run(
        ["ffmpeg", "-y", "-i", in_path, "-filter:a", ",".join(filters), out_path],
        check=True, capture_output=True,
    )


def _fit_narration_to_window(mp3_path: str, window: float, tmp_dir: Path, tag: str) -> str:
    """나레이션이 배정된 시간창보다 길면 추가 가속해 창 안에 맞춘다 (겹침/짤림 방지)."""
    dur = _probe_duration(mp3_path)
    target = window * 0.92  # 다음 줄과 약간의 여유
    if dur <= 0 or dur <= target:
        return mp3_path
    fitted = str(tmp_dir / f"tts_fit_{tag}.mp3")
    try:
        _speed_audio(mp3_path, dur / target, fitted)
        return fitted
    except Exception:  # noqa: BLE001
        return mp3_path


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


def render_from_videos(
    video_paths: list[str], script: list[dict], out_path: str, caption_style: str = "basic"
) -> str:
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

        # 대본 줄 수와 실제 장면전환 구간 수가 일치하면 그 구간을 그대로 시간창으로 사용
        # (화면 전환에 맞춘 자막/나레이션 타이밍). 불일치(수동 편집 등) 시 균등분할로 폴백.
        segments = compute_script_segments(video_paths)
        if len(segments) == len(lines) and lines:
            windows = [(seg["start"], seg["end"]) for seg in segments]
        else:
            win = dur / max(len(lines), 1)
            windows = [(i * win, (i + 1) * win) for i in range(len(lines))]

        # 1) 자막 오버레이 (라인별 실제 장면 구간)
        capped = str(tmpd / "capped.mp4")
        overlay_inputs, chains, cur, n_png = ["-i", base], [], "0:v", 0
        for i, line in enumerate(lines):
            cap = _strip_emoji(str(line.get("caption", "")))
            if not cap:
                continue
            n_png += 1
            png = str(tmpd / f"cap_{i}.png")
            _make_caption_png(cap, png, caption_style)
            overlay_inputs += ["-i", png]
            s, e = windows[i]
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

        # 2) 나레이션 TTS (라인별, 같은 장면 구간 시작점)
        # 구간 길이보다 길면 추가 가속해 다음 줄과 겹치거나 끝에서 잘리지 않게 맞춘다.
        narration: list[tuple[str, float]] = []
        if tts.is_enabled():
            for i, line in enumerate(lines):
                txt = _strip_emoji(str(line.get("narration", "")))
                if not txt:
                    continue
                mp3 = str(tmpd / f"tts_{i}.mp3")
                if tts.synthesize(txt, mp3):
                    s, e = windows[i]
                    mp3 = _fit_narration_to_window(mp3, e - s, tmpd, str(i))
                    narration.append((mp3, s))

        # 3) 배경음 + 믹스
        bgm = _find_bgm()
        if not narration and not bgm:
            if capped != out_path:
                subprocess.run(["ffmpeg", "-y", "-i", capped, "-c", "copy", out_path],
                               check=True, capture_output=True)
            return out_path

        _mix_audio(capped, narration, bgm, dur, out_path)
    return out_path


def render_ffmpeg(
    image_paths: list[str], script: list[dict], out_path: str, caption_style: str = "basic"
) -> str:
    """FFmpeg 로 9:16 숏폼 생성. 영상이 있으면 영상 편집, 없으면 사진 슬라이드쇼."""
    videos = [p for p in image_paths if Path(p).suffix.lower() in VIDEO_EXTS]
    if videos:
        # 실촬영 영상 우선 (체험단 클립 규칙: 사진 편집 영상 불가)
        return render_from_videos(videos, script, out_path, caption_style)

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
            _make_caption_png(str(line.get("caption", "")), cap_png, caption_style)
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
    image_paths: list[str], script: list[dict], out_path: str,
    engine: str | None = None, caption_style: str = "basic",
) -> tuple[str, str]:
    """숏폼 생성. (출력경로, 사용엔진) 반환. Creatomate 우선, 실패 시 FFmpeg."""
    prefer = engine or ("creatomate" if settings.creatomate_api_key else "ffmpeg")
    if prefer == "creatomate":
        try:
            return render_creatomate(image_paths, script, out_path), "creatomate"
        except Exception as e:  # noqa: BLE001
            print(f"Creatomate 실패 → FFmpeg fallback: {e}")
    return render_ffmpeg(image_paths, script, out_path, caption_style), "ffmpeg"
