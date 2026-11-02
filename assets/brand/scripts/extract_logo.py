"""Extract the approved Nivaro logo (mark + wordmark) from the owner's concept boards.

The owner chose the concept-board artwork as the logo (ADR-032). This script cuts it out with a clean
alpha channel so it works on light and dark surfaces:

  python assets/brand/scripts/extract_logo.py   # needs numpy + pillow

Inputs:  assets/brand/reference/nivaro-concept-branding-v1.png      (mark, wordmark: highest resolution)
         assets/brand/reference/nivaro-concept-brand-system-v1.png  (monochrome marks)
Outputs: assets/brand/logo/source/*.png  (render.mjs builds every other size and surface from these)

Alpha is "unmixed" against the locally sampled background (colour-to-alpha), then boosted so the
ribbon's light highlights stay opaque; edge pixels are recoloured so no white fringe shows on navy.
The ™ is cropped out until the trademark is filed (GAP-BRAND-TRADEMARK).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "assets/brand/reference"
OUT = ROOT / "assets/brand/logo/source"
INK = np.array([15, 23, 42], dtype=np.float64)  # Deep Navy / Ink #0F172A


def load(name: str) -> np.ndarray:
    return np.asarray(Image.open(REF / name).convert("RGB"), dtype=np.float64)


def border_bg(a: np.ndarray) -> np.ndarray:
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return np.median(edge, axis=0)


def unmix(crop: np.ndarray, *, lo: float = 0.035, span: float = 0.30) -> np.ndarray:
    """Colour-to-alpha against a light background; returns RGBA float array."""
    bg = border_bg(crop)
    raw = np.max((bg - crop) / np.maximum(bg, 1), axis=2).clip(0, 1)
    alpha = ((raw - lo) / span).clip(0, 1)
    safe = np.maximum(alpha, 1e-6)[..., None]
    fg = ((crop - (1 - alpha[..., None]) * bg) / safe).clip(0, 255)
    return np.dstack([fg, alpha * 255])


def ink_mask(crop: np.ndarray, *, on_dark: bool = False) -> np.ndarray:
    """Single-colour artwork → alpha from luminance distance to background."""
    lum = crop.mean(axis=2)
    bg = np.median(np.concatenate([lum[0], lum[-1], lum[:, 0], lum[:, -1]]))
    ink = lum.max() if on_dark else lum.min()
    alpha = ((lum - bg) / (ink - bg)).clip(0, 1)
    alpha = ((alpha - 0.06) / 0.88).clip(0, 1)
    return alpha * 255


def trim(rgba: np.ndarray, pad: int = 3) -> np.ndarray:
    ys, xs = np.where(rgba[..., 3] > 6)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    out = np.zeros((y1 - y0 + 1 + 2 * pad, x1 - x0 + 1 + 2 * pad, 4))
    out[pad:-pad, pad:-pad] = rgba[y0 : y1 + 1, x0 : x1 + 1]
    return out


def solid(alpha: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    out = np.zeros((*alpha.shape, 4))
    out[..., :3] = rgb
    out[..., 3] = alpha
    return out


def save(a: np.ndarray, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a.round().astype(np.uint8), "RGBA").save(OUT / name, optimize=True)
    print(f"{name}: {a.shape[1]}×{a.shape[0]}")


def main() -> None:
    board = load("nivaro-concept-branding-v1.png")
    # Colour N-loop mark (board 1, hero).
    save(trim(unmix(board[195:485, 275:690])), "nivaro-mark.png")
    # Wordmark "nivaro" (board 1, hero), ™ removed (it sits top-right of the final "o").
    word = board[195:418, 700:1440].copy()
    bg = border_bg(word)
    word[:100, 718:] = bg  # board y<295, x>1418 → the ™ glyph
    save(trim(solid(ink_mask(word), INK)), "nivaro-wordmark-ink.png")
    save(trim(solid(ink_mask(word), np.array([255.0, 255.0, 255.0]))), "nivaro-wordmark-white.png")

    system = load("nivaro-concept-brand-system-v1.png")
    # Monochrome marks (board 2, "Monochrome Usage"): ink on white, white on navy.
    mono = system[700:795, 95:222]
    save(trim(solid(ink_mask(mono), INK)), "nivaro-mark-ink.png")
    save(trim(solid(ink_mask(mono), np.array([255.0, 255.0, 255.0]))), "nivaro-mark-white.png")


if __name__ == "__main__":
    main()
