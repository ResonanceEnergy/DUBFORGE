"""DUBFORGE — Artwork Generator.

Generates album/single artwork assets (cover, banner, social) using
PIL/Pillow. Falls back to simple SVG generation if Pillow is unavailable.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

# Color palettes
PALETTES = {
    "obsidian": {
        "bg": (10, 10, 15),
        "accent": (180, 40, 40),
        "text": (220, 220, 225),
        "glow": (120, 20, 20),
    },
    "neon": {
        "bg": (5, 5, 20),
        "accent": (0, 255, 180),
        "text": (255, 255, 255),
        "glow": (0, 180, 120),
    },
    "void": {
        "bg": (0, 0, 0),
        "accent": (100, 0, 200),
        "text": (200, 200, 210),
        "glow": (60, 0, 140),
    },
}


def _generate_svg(track_name: str, artist_name: str,
                  palette: dict, width: int, height: int,
                  energy: float, darkness: float) -> str:
    """Generate SVG artwork as fallback."""
    bg = palette["bg"]
    accent = palette["accent"]
    text_color = palette["text"]
    glow = palette["glow"]

    # Darken background based on darkness param
    bg = tuple(int(c * (1 - darkness * 0.3)) for c in bg)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'  <rect width="100%" height="100%" fill="rgb{bg}"/>',
    ]

    # Energy-based concentric circles
    cx, cy = width // 2, height // 2
    num_rings = int(5 + energy * 10)
    for i in range(num_rings):
        r = (i + 1) * min(width, height) / (num_rings * 2.2)
        opacity = 0.1 + 0.3 * (1 - i / num_rings) * energy
        lines.append(
            f'  <circle cx="{cx}" cy="{cy}" r="{r:.0f}" '
            f'fill="none" stroke="rgb{accent}" stroke-width="1" '
            f'opacity="{opacity:.2f}"/>'
        )

    # Glow center
    lines.append(
        f'  <circle cx="{cx}" cy="{cy}" r="{min(width, height) * 0.15:.0f}" '
        f'fill="rgb{glow}" opacity="{energy * 0.4:.2f}"/>'
    )

    # Track name
    font_size = width // 18
    lines.append(
        f'  <text x="{cx}" y="{height * 0.85:.0f}" '
        f'font-family="Arial, sans-serif" font-size="{font_size}" '
        f'fill="rgb{text_color}" text-anchor="middle" font-weight="bold">'
        f'{track_name}</text>'
    )

    # Artist name
    font_size_small = font_size // 2
    lines.append(
        f'  <text x="{cx}" y="{height * 0.92:.0f}" '
        f'font-family="Arial, sans-serif" font-size="{font_size_small}" '
        f'fill="rgb{text_color}" text-anchor="middle" opacity="0.7">'
        f'{artist_name}</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def generate_full_artwork(track_name: str, artist_name: str,
                          palette_name: str = "obsidian",
                          output_dir: str = "output/press",
                          energy: float = 0.85,
                          darkness: float = 0.9) -> dict[str, str]:
    """Generate full set of artwork assets.

    Returns dict of asset_name → file_path.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    palette = PALETTES.get(palette_name, PALETTES["obsidian"])
    results: dict[str, str] = {}

    # Define sizes
    sizes = {
        "cover_3000": (3000, 3000),
        "cover_1500": (1500, 1500),
        "banner_1500x500": (1500, 500),
        "social_1200x630": (1200, 630),
    }

    # Try Pillow first
    try:
        from PIL import Image, ImageDraw, ImageFont
        _HAS_PIL = True
    except ImportError:
        _HAS_PIL = False

    for name, (w, h) in sizes.items():
        if _HAS_PIL:
            path = out / f"{name}.png"
            img = _render_pillow(track_name, artist_name, palette,
                                 w, h, energy, darkness)
            img.save(str(path))
            results[name] = str(path)
        else:
            path = out / f"{name}.svg"
            svg = _generate_svg(track_name, artist_name, palette,
                                w, h, energy, darkness)
            path.write_text(svg)
            results[name] = str(path)

    return results


def _render_pillow(track_name: str, artist_name: str,
                   palette: dict, width: int, height: int,
                   energy: float, darkness: float):
    """Render artwork using Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    bg = palette["bg"]
    accent = palette["accent"]
    text_color = palette["text"]
    glow = palette["glow"]

    # Darken
    bg = tuple(int(c * (1 - darkness * 0.3)) for c in bg)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2

    # Energy rings
    num_rings = int(5 + energy * 10)
    for i in range(num_rings):
        r = int((i + 1) * min(width, height) / (num_rings * 2.2))
        opacity_factor = 0.1 + 0.3 * (1 - i / num_rings) * energy
        ring_color = tuple(int(c * opacity_factor) for c in accent)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=ring_color, width=max(1, width // 500)
        )

    # Glow
    glow_r = int(min(width, height) * 0.15)
    glow_color = tuple(int(c * energy * 0.4) for c in glow)
    draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=glow_color
    )

    # Text
    try:
        font_size = width // 18
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",
                                         font_size // 2)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Track name
    bbox = draw.textbbox((0, 0), track_name, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        (cx - tw // 2, int(height * 0.80)),
        track_name, fill=text_color, font=font
    )

    # Artist
    bbox2 = draw.textbbox((0, 0), artist_name, font=font_small)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(
        (cx - tw2 // 2, int(height * 0.90)),
        artist_name, fill=text_color, font=font_small
    )

    return img
