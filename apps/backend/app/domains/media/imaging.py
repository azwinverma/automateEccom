"""Image validation, normalisation, quality scoring and derivatives (pure functions, no DB).

* Format is detected from bytes (Pillow), never trusted from the client's Content-Type/extension.
* Decompression bombs are rejected (pixel cap).
* EXIF orientation is applied, then all metadata (incl. GPS location) is dropped from derivatives.
* Derivatives never alter product appearance: they resize and *pad*, never crop into the product or
  recolour it. Real background removal is an AI edit (MED-005) with fidelity review.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import pillow_heif
from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

pillow_heif.register_heif_opener()

MAX_PIXELS = 50_000_000  # ~8K x 6K; above this treat as a decompression bomb
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "HEIF": "image/heic",
    "MPO": "image/jpeg",
}
MIN_SHORT_EDGE = 600
CLOUD = (248, 250, 252)  # design token neutral.cloud: neutral padding that never tints the product
WHITE = (255, 255, 255)


class ImageRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class Derivative:
    kind: str
    data: bytes
    content_type: str
    width: int
    height: int


@dataclass
class Processed:
    format: str
    width: int
    height: int
    had_location: bool
    quality_score: float
    quality_flags: list[str] = field(default_factory=list)
    derivatives: list[Derivative] = field(default_factory=list)


# kind → (canvas size or None for "fit within", max edge, background, format)
SPECS: dict[str, tuple[tuple[int, int] | None, int, tuple[int, int, int], str]] = {
    "thumb": (None, 320, CLOUD, "WEBP"),
    "medium": (None, 1080, CLOUD, "WEBP"),
    "square_white": ((1080, 1080), 1080, WHITE, "JPEG"),  # marketplaces require white canvas
    "portrait_4_5": ((1080, 1350), 1350, CLOUD, "JPEG"),  # Instagram/Facebook feed
    "story_9_16": ((1080, 1920), 1920, CLOUD, "JPEG"),  # Stories/Reels/TikTok
}


def _open(data: bytes) -> Image.Image:
    try:
        probe = Image.open(io.BytesIO(data))
        # Pillow only *raises* above 2x MAX_IMAGE_PIXELS (it merely warns between 1x and 2x), so check the
        # header dimensions ourselves before any pixel data is decoded.
        if probe.width * probe.height > MAX_PIXELS:
            raise ImageRejected("image_too_large")
        probe.verify()  # structural check; image must be reopened after verify()
        img = Image.open(io.BytesIO(data))
        img.load()
    except Image.DecompressionBombError as e:
        raise ImageRejected("image_too_large") from e
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as e:
        raise ImageRejected("not_an_image") from e
    if (img.format or "").upper() not in ALLOWED_FORMATS:
        raise ImageRejected("unsupported_format")
    return img


def _has_gps(img: Image.Image) -> bool:
    try:
        return bool(img.getexif().get_ifd(0x8825))  # GPSInfo IFD
    except Exception:
        return False


def _quality(img: Image.Image) -> tuple[float, list[str]]:
    flags: list[str] = []
    w, h = img.size
    if min(w, h) < MIN_SHORT_EDGE:
        flags.append("low_resolution")
    small = img.convert("L")
    small.thumbnail((512, 512))
    brightness = ImageStat.Stat(small).mean[0]
    if brightness < 50:
        flags.append("too_dark")
    elif brightness > 230:
        flags.append("overexposed")
    edges = small.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).var[0]
    if sharpness < 60:
        flags.append("blurry")
    score = (
        1.0
        - 0.3 * ("low_resolution" in flags)
        - 0.25 * ("blurry" in flags)
        - 0.2 * bool({"too_dark", "overexposed"} & set(flags))
    )
    return round(max(score, 0.0), 2), flags


def _render(img: Image.Image, kind: str) -> Derivative:
    canvas, max_edge, bg, fmt = SPECS[kind]
    src = img.copy()
    if canvas is None:
        src.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        out = src
    else:
        src.thumbnail(canvas, Image.Resampling.LANCZOS)
        out = Image.new("RGB", canvas, bg)
        out.paste(
            src,
            ((canvas[0] - src.width) // 2, (canvas[1] - src.height) // 2),
            src if src.mode == "RGBA" else None,
        )
    if fmt == "JPEG" and out.mode != "RGB":
        flat = Image.new("RGB", out.size, bg)
        flat.paste(out, mask=out.split()[-1] if out.mode in ("RGBA", "LA") else None)
        out = flat
    buf = io.BytesIO()
    # No exif/icc kwargs → metadata (incl. GPS) is not written.
    out.save(buf, format=fmt, quality=85, optimize=True)
    return Derivative(
        kind, buf.getvalue(), "image/webp" if fmt == "WEBP" else "image/jpeg", out.width, out.height
    )


def process(data: bytes) -> Processed:
    img = _open(data)
    fmt = (img.format or "").upper()
    had_location = _has_gps(img)
    img = ImageOps.exif_transpose(img) or img
    img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
    score, flags = _quality(img)
    derivatives = [_render(img, k) for k in SPECS]
    return Processed(
        "JPEG" if fmt == "MPO" else fmt, img.width, img.height, had_location, score, flags, derivatives
    )
