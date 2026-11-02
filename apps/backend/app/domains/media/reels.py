"""Auto Reel renderer (MED-008): seller photos → short H.264 video without generative AI.

* Slides: each photo is shown *whole* (contain) over a blurred, dimmed copy of itself, so the product
  is never cropped, recoloured or distorted. Subtle Ken Burns zoom (≤8%) and crossfades.
* Overlay card: headline / price / CTA rendered with Pillow using bundled Inter + Noto Sans Devanagari.
  Devanagari requires complex-text shaping (libraqm); without it we refuse rather than render broken
  Nepali (matras in the wrong place).
* Price text is supplied by the caller from the catalog (internal facts), never generated.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, features

FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
ASPECTS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),
}
FPS = 30
XFADE = 0.5
INK = (15, 23, 42)
WHITE = (255, 255, 255)
BLUE = (37, 99, 235)
DEVANAGARI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


class ReelError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Overlay:
    headline: str | None = None
    price: str | None = None
    cta: str | None = None


@dataclass(frozen=True)
class RenderResult:
    video: bytes
    poster_jpeg: bytes
    duration_s: float
    width: int
    height: int


def has_devanagari(text: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def shaping_available() -> bool:
    return bool(features.check("raqm"))


def format_npr(minor: int, locale: str, from_prefix: bool = False) -> str:
    """Nepali/Indian digit grouping (1,25,000). Devanagari digits and रू for ne; Rs for en."""
    rupees, paisa = divmod(minor, 100)
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    if paisa:
        s += f".{paisa:02d}"
    if locale == "ne":
        return ("देखि " if from_prefix else "") + "रू " + s.translate(DEVANAGARI_DIGITS)
    return ("From " if from_prefix else "") + "Rs " + s


def _font(text: str, weight: str, size: int) -> ImageFont.FreeTypeFont:
    family = "NotoSansDevanagari" if has_devanagari(text) else "Inter"
    layout = ImageFont.Layout.RAQM if shaping_available() else ImageFont.Layout.BASIC
    return ImageFont.truetype(str(FONTS / f"{family}-{weight}.ttf"), size, layout_engine=layout)


def _check_text(*texts: str | None) -> None:
    if any(t and has_devanagari(t) for t in texts) and not shaping_available():
        raise ReelError(
            "text_shaping_unavailable",
            "Nepali text needs libraqm for correct rendering; install libraqm on the worker",
        )


def slide(image_bytes: bytes, size: tuple[int, int], reserved_bottom: int = 0) -> Image.Image:
    """Whole photo over a blurred copy of itself. ``reserved_bottom`` keeps the product clear of the
    overlay card so text never covers the item."""
    with Image.open(io.BytesIO(image_bytes)) as src:
        img = (ImageOps.exif_transpose(src) or src).convert("RGB")
    bg = ImageOps.fit(img, size, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", size, INK), 0.35)
    fg = img.copy()
    margin = int(min(size) * 0.06)
    avail_h = size[1] - 2 * margin - reserved_bottom
    fg.thumbnail((size[0] - 2 * margin, avail_h), Image.Resampling.LANCZOS)
    bg.paste(fg, ((size[0] - fg.width) // 2, margin + (avail_h - fg.height) // 2))
    return bg


def card(size: tuple[int, int], overlay: Overlay) -> tuple[Image.Image, int]:
    """Transparent overlay with a calm bottom panel: headline, price, CTA button (md radius, no pill).
    Returns (layer, height of the bottom region the panel occupies)."""
    _check_text(overlay.headline, overlay.price, overlay.cta)
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    if not (overlay.headline or overlay.price or overlay.cta):
        return layer, 0
    draw = ImageDraw.Draw(layer)
    unit = min(w, h) // 30
    pad = unit * 2
    lines: list[tuple[str, ImageFont.FreeTypeFont, tuple[int, int, int]]] = []
    if overlay.headline:
        lines.append((overlay.headline, _font(overlay.headline, "SemiBold", unit * 2), WHITE))
    if overlay.price:
        lines.append((overlay.price, _font(overlay.price, "Bold", int(unit * 2.6)), WHITE))
    heights = [f.getbbox(t)[3] - f.getbbox(t)[1] for t, f, _ in lines]
    cta_h = unit * 3 if overlay.cta else 0
    panel_h = (
        pad * 2
        + sum(heights)
        + unit * (len(lines) - 1 if lines else 0)
        + (cta_h + unit if overlay.cta else 0)
    )
    top = h - panel_h - pad
    draw.rounded_rectangle((pad, top, w - pad, h - pad), radius=unit // 2, fill=(*INK, 205))
    y = top + pad
    for (text, font, color), lh in zip(lines, heights, strict=True):
        draw.text((pad * 2, y - font.getbbox(text)[1]), text, font=font, fill=color)
        y += lh + unit
    if overlay.cta:
        f = _font(overlay.cta, "SemiBold", int(unit * 1.4))
        tw = f.getlength(overlay.cta)
        draw.rounded_rectangle(
            (pad * 2, y, pad * 2 + tw + unit * 2, y + cta_h), radius=unit // 2, fill=(*BLUE, 255)
        )
        bbox = f.getbbox(overlay.cta)
        draw.text(
            (pad * 2 + unit, y + (cta_h - (bbox[3] - bbox[1])) // 2 - bbox[1]),
            overlay.cta,
            font=f,
            fill=WHITE,
        )
    return layer, int(h - top)


def render(photos: list[bytes], aspect: str, seconds_per_slide: float, overlay: Overlay) -> RenderResult:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ReelError("renderer_unavailable", "ffmpeg not installed on the worker")
    if not 1 <= len(photos) <= 10:
        raise ReelError("invalid_photo_count")
    if not 1.5 <= seconds_per_slide <= 6:
        raise ReelError("invalid_slide_duration")
    size = ASPECTS[aspect]
    overlay_img, reserved = card(size, overlay)  # validates text shaping before any heavy work
    d = seconds_per_slide
    frames = int(d * FPS)
    with tempfile.TemporaryDirectory(prefix="reel-") as tmp:
        t = Path(tmp)
        slides = [slide(p, size, reserved) for p in photos]
        for i, s in enumerate(slides):
            s.save(t / f"s{i}.png")
        overlay_img.save(t / "card.png")
        args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        for i in range(len(slides)):
            args += ["-i", str(t / f"s{i}.png")]
        args += ["-loop", "1", "-i", str(t / "card.png")]
        w, h = size
        parts = []
        for i in range(len(slides)):
            # Alternate zoom-in / zoom-out; zoom ≤ 1.08 keeps the product fully in frame.
            z = f"min(1+0.08*on/{frames},1.08)" if i % 2 == 0 else f"max(1.08-0.08*on/{frames},1)"
            parts.append(
                f"[{i}:v]scale={w * 2}:{h * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
            )
        last = "v0"
        for i in range(1, len(slides)):
            offset = i * d - i * XFADE
            parts.append(f"[{last}][v{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[x{i}]")
            last = f"x{i}"
        n = len(slides)
        parts.append(f"[{last}][{n}:v]overlay=0:0:shortest=1:format=auto,format=yuv420p[out]")
        out = t / "reel.mp4"
        args += [
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[out]",
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(out),
        ]
        try:
            subprocess.run(args, check=True, capture_output=True, timeout=300)  # noqa: S603 - fixed argv, no shell
        except subprocess.CalledProcessError as e:
            raise ReelError("render_failed", e.stderr.decode(errors="replace")[-300:]) from e
        except subprocess.TimeoutExpired as e:
            raise ReelError("render_timeout") from e
        poster = io.BytesIO()
        Image.alpha_composite(slides[0].convert("RGBA"), overlay_img).convert("RGB").save(
            poster, "JPEG", quality=85
        )
        duration = n * d - (n - 1) * XFADE
        return RenderResult(out.read_bytes(), poster.getvalue(), round(duration, 2), w, h)
