"""Export a 4-5 page PDF Pitch Deck using Pillow.

Each page is a hand-laid PIL Image (gradient bg, text, embedded poster, palette
swatches, video keyframe grid). Saved as multi-page PDF via PIL's save_all.
"""

import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PAGE_W, PAGE_H = 1240, 1754  # A4 @ 150dpi portrait


# --- font loading ---------------------------------------------------------

def _font(size, bold=False):
    """Try to find a system font; fall back to PIL default."""
    candidates_bold = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidates_regular = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in (candidates_bold if bold else candidates_regular):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# --- helpers --------------------------------------------------------------

def _hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _extract_hex_codes(text):
    return [c for c in re.findall(r"#[0-9A-Fa-f]{6}", text or "")]


def _gradient_bg(w, h, top_rgb, bot_rgb):
    bg = Image.new("RGB", (w, h), top_rgb)
    draw = ImageDraw.Draw(bg)
    for y in range(h):
        ratio = y / h
        r = int(top_rgb[0] * (1 - ratio) + bot_rgb[0] * ratio)
        g = int(top_rgb[1] * (1 - ratio) + bot_rgb[1] * ratio)
        b = int(top_rgb[2] * (1 - ratio) + bot_rgb[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return bg


def _wrap_text(draw, text, font, max_w):
    """Word-wrap text to fit max_w pixels. Returns list of lines."""
    if not text:
        return []
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _draw_centered_lines(draw, lines, font, y, w, fill, line_gap=10):
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((w - tw) // 2, y), line, font=font, fill=fill)
        y += th + line_gap
    return y


# --- pages ----------------------------------------------------------------

def _page_cover(theme, product_info, palette_rgb):
    top = palette_rgb[0] if palette_rgb else (20, 20, 35)
    bot = palette_rgb[-1] if len(palette_rgb) > 1 else (5, 5, 15)
    img = _gradient_bg(PAGE_W, PAGE_H, top, bot)
    draw = ImageDraw.Draw(img)

    # Subtle vignette
    vignette = Image.new("L", (PAGE_W, PAGE_H), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse((-200, -200, PAGE_W + 200, PAGE_H + 200), fill=180)
    vignette = vignette.filter(ImageFilter.GaussianBlur(120))

    # Eyebrow
    eyebrow_font = _font(28, bold=True)
    draw.text((100, 140), "AD CAMPAIGN PITCH", font=eyebrow_font, fill=(255, 255, 255, 180))

    # Product name (big)
    name_font = _font(110, bold=True)
    name_lines = _wrap_text(draw, product_info["product_name"], name_font, PAGE_W - 200)
    y = 240
    for line in name_lines:
        draw.text((100, y), line, font=name_font, fill=(255, 255, 255))
        y += 130

    # Company
    company_font = _font(36)
    draw.text((100, y + 20), f"by {product_info['company_name']}", font=company_font, fill=(255, 255, 255, 200))

    # Slogan (big italic-feel serif)
    slogan_font = _font(72, bold=True)
    slogan_y = PAGE_H - 600
    draw.text((100, slogan_y - 80), "—  SLOGAN  —", font=_font(24), fill=(255, 255, 255, 160))
    slogan_lines = _wrap_text(draw, f"“{theme['slogan']}”", slogan_font, PAGE_W - 200)
    y = slogan_y
    for line in slogan_lines:
        draw.text((100, y), line, font=slogan_font, fill=(255, 255, 255))
        y += 90

    # Footer
    footer_font = _font(22)
    draw.text((100, PAGE_H - 100), "Generated with AI Ad Campaign Studio", font=footer_font, fill=(255, 255, 255, 160))
    return img


def _page_poster(poster_path, palette_rgb):
    bg_top = palette_rgb[0] if palette_rgb else (15, 15, 25)
    bg_bot = (10, 10, 18)
    img = _gradient_bg(PAGE_W, PAGE_H, bg_top, bg_bot)
    poster = Image.open(poster_path).convert("RGB")
    pw, ph = poster.size
    margin = 80
    max_w = PAGE_W - 2 * margin
    max_h = PAGE_H - 2 * margin - 100  # room for caption
    scale = min(max_w / pw, max_h / ph)
    new_w, new_h = int(pw * scale), int(ph * scale)
    poster_resized = poster.resize((new_w, new_h), Image.LANCZOS)
    px = (PAGE_W - new_w) // 2
    py = margin + 60
    # Drop shadow
    shadow = Image.new("RGBA", (new_w + 60, new_h + 60), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((30, 30, new_w + 30, new_h + 30), fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    img.paste(shadow, (px - 30, py - 30 + 15), shadow)
    img.paste(poster_resized, (px, py))

    draw = ImageDraw.Draw(img)
    cap_font = _font(28, bold=True)
    caption = "PRINT POSTER"
    bbox = draw.textbbox((0, 0), caption, font=cap_font)
    cw = bbox[2] - bbox[0]
    draw.text(((PAGE_W - cw) // 2, margin), caption, font=cap_font, fill=(255, 255, 255, 200))
    return img


def _page_theme(theme, palette_rgb):
    img = _gradient_bg(PAGE_W, PAGE_H, (18, 18, 28), (8, 8, 14))
    draw = ImageDraw.Draw(img)

    # Header
    header_font = _font(60, bold=True)
    draw.text((100, 120), "Creative Direction", font=header_font, fill=(255, 255, 255))
    draw.line([(100, 210), (PAGE_W - 100, 210)], fill=(255, 255, 255, 80), width=2)

    label_font = _font(26, bold=True)
    body_font = _font(28)

    y = 260

    def section(label, body):
        nonlocal y
        draw.text((100, y), label.upper(), font=label_font, fill=(180, 180, 220))
        y += 50
        lines = _wrap_text(draw, body, body_font, PAGE_W - 200)
        for line in lines:
            draw.text((100, y), line, font=body_font, fill=(240, 240, 245))
            y += 42
        y += 30

    section("Theme", theme.get("theme", ""))
    section("Tone", theme.get("tone", ""))
    section("Visual Style", theme.get("visual_style", ""))

    # Color swatches
    if palette_rgb:
        draw.text((100, y), "COLOR PALETTE", font=label_font, fill=(180, 180, 220))
        y += 50
        sw_size = 140
        sw_gap = 30
        for i, rgb in enumerate(palette_rgb[:5]):
            x = 100 + i * (sw_size + sw_gap)
            draw.rounded_rectangle((x, y, x + sw_size, y + sw_size), radius=18, fill=rgb)
            hex_label = "#%02X%02X%02X" % rgb
            draw.text((x, y + sw_size + 12), hex_label, font=_font(20), fill=(220, 220, 220))
    return img


def _extract_keyframes(video_path, n=4):
    """Use ffmpeg to extract n evenly-spaced frames. Returns list of PIL Images or []"""
    if not shutil.which("ffmpeg"):
        return []
    out = []
    tmp = Path(video_path).parent / "_keyframes"
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("*.jpg"):
        f.unlink()
    try:
        # 10s video, 4 frames at 1.5, 4, 6.5, 9 sec
        timestamps = [1.5, 4.0, 6.5, 9.0][:n]
        for i, t in enumerate(timestamps):
            cmd = [
                "ffmpeg", "-y", "-ss", str(t), "-i", str(video_path),
                "-frames:v", "1", "-q:v", "2",
                str(tmp / f"frame_{i}.jpg"),
            ]
            subprocess.run(cmd, capture_output=True, timeout=30, check=True)
            out.append(Image.open(tmp / f"frame_{i}.jpg").copy())
    except Exception:
        return []
    return out


def _page_video_grid(video_path, palette_rgb):
    img = _gradient_bg(PAGE_W, PAGE_H, (15, 15, 25), (5, 5, 12))
    draw = ImageDraw.Draw(img)
    header_font = _font(60, bold=True)
    draw.text((100, 120), "Video Storyboard", font=header_font, fill=(255, 255, 255))
    draw.line([(100, 210), (PAGE_W - 100, 210)], fill=(255, 255, 255, 80), width=2)

    frames = _extract_keyframes(video_path, n=4)
    if not frames:
        draw.text((100, 280), "(ffmpeg not available — keyframes skipped)", font=_font(28), fill=(220, 220, 220))
        return img

    # 2x2 grid
    grid_top = 280
    grid_w = PAGE_W - 200
    grid_h = PAGE_H - grid_top - 120
    cell_w = (grid_w - 40) // 2
    cell_h = (grid_h - 40) // 2
    for i, frame in enumerate(frames[:4]):
        col = i % 2
        row = i // 2
        x = 100 + col * (cell_w + 40)
        y = grid_top + row * (cell_h + 40)
        f = frame.resize((cell_w, cell_h), Image.LANCZOS)
        img.paste(f, (x, y))
        draw.rectangle((x, y, x + cell_w, y + cell_h), outline=(255, 255, 255, 100), width=2)
    return img


def _page_cta(theme, product_info, palette_rgb):
    top = palette_rgb[-1] if palette_rgb else (10, 10, 18)
    bot = palette_rgb[0] if palette_rgb else (30, 30, 50)
    img = _gradient_bg(PAGE_W, PAGE_H, top, bot)
    draw = ImageDraw.Draw(img)

    eyebrow_font = _font(28, bold=True)
    draw.text((100, 140), "CALL TO ACTION", font=eyebrow_font, fill=(255, 255, 255, 200))

    cta_font = _font(80, bold=True)
    cta_lines = _wrap_text(draw, product_info["call_to_action"], cta_font, PAGE_W - 200)
    y = 240
    for line in cta_lines:
        draw.text((100, y), line, font=cta_font, fill=(255, 255, 255))
        y += 100

    y += 80
    draw.text((100, y), "TARGET AUDIENCE", font=eyebrow_font, fill=(255, 255, 255, 200))
    y += 50
    aud_lines = _wrap_text(draw, product_info["target_audience"], _font(28), PAGE_W - 200)
    for line in aud_lines:
        draw.text((100, y), line, font=_font(28), fill=(240, 240, 245))
        y += 42

    y += 50
    draw.text((100, y), "KEY SELLING POINTS", font=eyebrow_font, fill=(255, 255, 255, 200))
    y += 50
    for sp in product_info.get("selling_points", [])[:5]:
        for line in _wrap_text(draw, "•  " + sp, _font(26), PAGE_W - 200):
            draw.text((100, y), line, font=_font(26), fill=(240, 240, 245))
            y += 38
        y += 6

    draw.text((100, PAGE_H - 100), "Generated with AI Ad Campaign Studio", font=_font(22), fill=(255, 255, 255, 170))
    return img


def export_pitch_deck(campaign_dir: Path, out_path: Path) -> Path:
    """Build a 5-page PDF for the campaign in `campaign_dir`. Returns out_path."""
    campaign_dir = Path(campaign_dir)
    out_path = Path(out_path)

    summary_path = campaign_dir / "campaign_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"campaign_summary.json missing in {campaign_dir}")
    with open(summary_path) as f:
        summary = json.load(f)
    product_info = summary["product_info"]
    theme = summary["campaign_theme"]

    palette_text = (theme.get("color_palette") or "") + " " + (product_info.get("brand_colors") or "")
    palette_rgb = [c for c in (_hex_to_rgb(h) for h in _extract_hex_codes(palette_text)) if c]
    if not palette_rgb:
        palette_rgb = [(30, 30, 50), (10, 10, 18)]

    poster_path = campaign_dir / "poster.png"
    video_path = campaign_dir / "ad_video.mp4"

    pages = [
        _page_cover(theme, product_info, palette_rgb),
    ]
    if poster_path.exists():
        pages.append(_page_poster(poster_path, palette_rgb))
    pages.append(_page_theme(theme, palette_rgb))
    if video_path.exists():
        pages.append(_page_video_grid(video_path, palette_rgb))
    pages.append(_page_cta(theme, product_info, palette_rgb))

    first, *rest = pages
    first.save(out_path, "PDF", save_all=True, append_images=rest, resolution=150)
    return out_path
