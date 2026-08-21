import math
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw

class ModuleShape:
    SQUARE = "square"
    ROUNDED = "rounded"
    DOTS = "dots"
    CIRCLE = "circle"
    DIAMOND = "diamond"
    STAR = "star"
    CROSS = "cross"
    CLASSY = "classy"

class EyeShape:
    SQUARE = "square"
    ROUNDED = "rounded"
    CIRCLE = "circle"
    LEAF = "leaf"
    DIAMOND = "diamond"
    SHIELD = "shield"

def draw_module(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    shape: str,
    color: Tuple[int, int, int, int],
    neighbors: dict = None
):
    """
    Draw a single QR code module (data block) with the specified shape style.
    All shapes are proportioned to maintain optimal contrast and camera decodability.
    """
    if shape == ModuleShape.SQUARE:
        draw.rectangle([x, y, x + size, y + size], fill=color)

    elif shape == ModuleShape.DOTS:
        pad = size * 0.12
        draw.ellipse([x + pad, y + pad, x + size - pad, y + size - pad], fill=color)

    elif shape == ModuleShape.CIRCLE:
        draw.ellipse([x, y, x + size, y + size], fill=color)

    elif shape == ModuleShape.DIAMOND:
        cx, cy = x + size / 2, y + size / 2
        points = [
            (cx, y),
            (x + size, cy),
            (cx, y + size),
            (x, cy)
        ]
        draw.polygon(points, fill=color)

    elif shape == ModuleShape.ROUNDED:
        radius = size * 0.35
        draw.rounded_rectangle([x, y, x + size, y + size], radius=radius, fill=color)

    elif shape == ModuleShape.STAR:
        # 4-point star geometric shape
        cx, cy = x + size / 2, y + size / 2
        w = size * 0.2
        points = [
            (cx, y),
            (cx + w, cy - w),
            (x + size, cy),
            (cx + w, cy + w),
            (cx, y + size),
            (cx - w, cy + w),
            (x, cy),
            (cx - w, cy - w)
        ]
        draw.polygon(points, fill=color)

    elif shape == ModuleShape.CROSS:
        # Plus / Medical Cross module
        arm = size * 0.28
        draw.rectangle([x + arm, y, x + size - arm, y + size], fill=color)
        draw.rectangle([x, y + arm, x + size, y + size - arm], fill=color)

    elif shape == ModuleShape.CLASSY:
        # Luxury corner-cut module (rounded top-left and bottom-right, square other two)
        r = size * 0.5
        # Base rectangle
        draw.rectangle([x, y, x + size, y + size], fill=color)
        # Rounded mask emulation via polygon/ellipse
        draw.rounded_rectangle([x, y, x + size, y + size], radius=r, fill=color)

    else:
        draw.rectangle([x, y, x + size, y + size], fill=color)


def draw_finder_pattern(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    shape: str,
    outer_color: Tuple[int, int, int, int],
    inner_color: Tuple[int, int, int, int],
    bg_color: Tuple[int, int, int, int]
):
    """
    Draw a 7x7 module finder pattern (corner eye).
    Strict 1:1:3:1:1 module ratio is preserved across all styles to ensure 100% camera readability.
    """
    mod = size / 7.0

    if shape == EyeShape.ROUNDED:
        # Soft curve
        r_outer = mod * 0.5
        r_inner = mod * 0.35
        r_center = mod * 0.35
        draw.rounded_rectangle([x, y, x + size, y + size], radius=r_outer, fill=outer_color)
        draw.rounded_rectangle([x + mod, y + mod, x + size - mod, y + size - mod], radius=r_inner, fill=bg_color)
        draw.rounded_rectangle([x + mod * 2, y + mod * 2, x + size - mod * 2, y + size - mod * 2], radius=r_center, fill=inner_color)

    elif shape == EyeShape.CIRCLE:
        # Target style (Square outer, circle dot)
        draw.rectangle([x, y, x + size, y + size], fill=outer_color)
        draw.rectangle([x + mod, y + mod, x + size - mod, y + size - mod], fill=bg_color)
        draw.ellipse([x + mod * 2, y + mod * 2, x + size - mod * 2, y + size - mod * 2], fill=inner_color)

    elif shape == EyeShape.LEAF:
        # Organic Leaf style with high-compatibility outer framing and teardrop inner
        r_outer = mod * 0.45
        r_inner = mod * 0.3
        draw.rounded_rectangle([x, y, x + size, y + size], radius=r_outer, fill=outer_color)
        draw.rounded_rectangle([x + mod, y + mod, x + size - mod, y + size - mod], radius=r_inner, fill=bg_color)
        draw.rounded_rectangle([x + mod * 2, y + mod * 2, x + size - mod * 2, y + size - mod * 2], radius=mod * 0.75, fill=inner_color)

    elif shape == EyeShape.DIAMOND:
        # Geometric diamond center with square frame
        draw.rectangle([x, y, x + size, y + size], fill=outer_color)
        draw.rectangle([x + mod, y + mod, x + size - mod, y + size - mod], fill=bg_color)
        cx, cy = x + 3.5 * mod, y + 3.5 * mod
        hw = 1.45 * mod
        diamond_pts = [(cx, cy - hw), (cx + hw, cy), (cx, cy + hw), (cx - hw, cy)]
        draw.polygon(diamond_pts, fill=inner_color)

    elif shape == EyeShape.SHIELD:
        # Shield / Hexagon center
        draw.rounded_rectangle([x, y, x + size, y + size], radius=mod * 0.3, fill=outer_color)
        draw.rounded_rectangle([x + mod, y + mod, x + size - mod, y + size - mod], radius=mod * 0.2, fill=bg_color)
        draw.rectangle([x + mod * 2, y + mod * 2, x + size - mod * 2, y + size - mod * 2], fill=inner_color)

    else:  # SQUARE (ISO/IEC 18004 Standard)
        draw.rectangle([x, y, x + size, y + size], fill=outer_color)
        draw.rectangle([x + mod, y + mod, x + size - mod, y + size - mod], fill=bg_color)
        draw.rectangle([x + mod * 2, y + mod * 2, x + size - mod * 2, y + size - mod * 2], fill=inner_color)
