"""Crop a poster into IG square / 9:16 / 16:9 variants.

Strategy: TRUE cover-crop. Scale the poster to fill the target frame entirely,
then crop the overflow. No blurred padding — the result is a real edge-to-edge
image at the requested aspect ratio.

Crop anchors:
  - 1:1 square  → center (most posters have the product centered)
  - 9:16 story  → center (very close to source 2:3 aspect, almost no crop)
  - 16:9 wide   → vertical center, but biased upward 30% so the slogan/title
                  area (typically in the top half of a print poster) survives
                  rather than getting cropped out.

For 16:9 from a 2:3 source, the crop is aggressive (loses ~60% of pixels). The
result is acceptable for a "browser hero" preview but isn't editorial-grade.
For pixel-perfect 16:9, generate a separate horizontal poster at 1536x1024.
"""

from pathlib import Path
from PIL import Image

SIZES = {
    "ig_square": (1080, 1080),
    "ig_story": (1080, 1920),     # 9:16
    "wide": (1200, 675),           # 16:9
}

# Per-size vertical anchor: 0.0 = top, 0.5 = center, 1.0 = bottom.
# 16:9 from a vertical source loses lots of pixels — bias upward to keep the
# title/slogan area visible (most posters put the headline in the top third).
VERTICAL_ANCHOR = {
    "ig_square": 0.5,
    "ig_story": 0.5,
    "wide": 0.35,
}


def _cover_crop(src: Image.Image, target_w: int, target_h: int, vertical_anchor: float = 0.5) -> Image.Image:
    """Scale src to fully cover target_w x target_h, then crop overflow.

    True edge-to-edge fill, no padding. `vertical_anchor` controls which
    horizontal slice survives when overflow is vertical (0=top, 1=bottom).
    """
    src = src.convert("RGB")
    sw, sh = src.size

    scale = max(target_w / sw, target_h / sh)
    new_w, new_h = int(sw * scale), int(sh * scale)
    resized = src.resize((new_w, new_h), Image.LANCZOS)

    # Horizontal: always center
    left = max(0, (new_w - target_w) // 2)
    # Vertical: anchored
    overflow_v = max(0, new_h - target_h)
    top = int(overflow_v * vertical_anchor)

    return resized.crop((left, top, left + target_w, top + target_h))


def generate_social_sizes(poster_path: Path, out_dir: Path) -> dict:
    """Build 3 social-media variants. Returns {size_id: path}."""
    poster_path = Path(poster_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Image.open(poster_path)

    results = {}
    for name, (w, h) in SIZES.items():
        out = out_dir / f"poster_{name}.jpg"
        anchor = VERTICAL_ANCHOR.get(name, 0.5)
        img = _cover_crop(src, w, h, vertical_anchor=anchor)
        img.save(out, "JPEG", quality=92)
        results[name] = str(out)
    return results
