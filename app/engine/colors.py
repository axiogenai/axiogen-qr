import math
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw

def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Convert hex color string (#RGB, #RGBA, #RRGGBB, #RRGGBBAA) to RGBA tuple."""
    hex_str = hex_color.lstrip('#')
    if len(hex_str) == 3:
        r, g, b = [int(c * 2, 16) for c in hex_str]
        return (r, g, b, alpha)
    elif len(hex_str) == 4:
        r, g, b, a = [int(c * 2, 16) for c in hex_str]
        return (r, g, b, a)
    elif len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b, alpha)
    elif len(hex_str) == 8:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        a = int(hex_str[6:8], 16)
        return (r, g, b, a)
    return (0, 0, 0, alpha)

def interpolate_color(c1: Tuple[int, int, int, int], c2: Tuple[int, int, int, int], factor: float) -> Tuple[int, int, int, int]:
    """Linearly interpolate between two RGBA colors."""
    factor = max(0.0, min(1.0, factor))
    r = int(c1[0] + (c2[0] - c1[0]) * factor)
    g = int(c1[1] + (c2[1] - c1[1]) * factor)
    b = int(c1[2] + (c2[2] - c1[2]) * factor)
    a = int(c1[3] + (c2[3] - c1[3]) * factor)
    return (r, g, b, a)

def create_linear_gradient(
    width: int,
    height: int,
    color_stops: List[Tuple[float, str]],
    angle_deg: float = 45.0
) -> Image.Image:
    """
    Generate a linear gradient image at a specified angle.
    color_stops: [(0.0, '#4F46E5'), (1.0, '#EC4899')]
    angle_deg: 0 (left-to-right), 90 (top-to-bottom), 45 (diagonal)
    """
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    parsed_stops = [(stop, hex_to_rgba(c)) for stop, c in color_stops]
    parsed_stops.sort(key=lambda x: x[0])

    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Calculate bounding projection
    cx, cy = width / 2.0, height / 2.0
    corners = [(0, 0), (width, 0), (width, height), (0, height)]
    projections = [(x - cx) * cos_a + (y - cy) * sin_a for x, y in corners]
    min_proj = min(projections)
    max_proj = max(projections)
    proj_range = max_proj - min_proj if max_proj != min_proj else 1.0

    # Render pixel rows with sampling
    for y in range(height):
        for x in range(width):
            proj = (x - cx) * cos_a + (y - cy) * sin_a
            t = (proj - min_proj) / proj_range

            # Find matching color stop
            if t <= parsed_stops[0][0]:
                col = parsed_stops[0][1]
            elif t >= parsed_stops[-1][0]:
                col = parsed_stops[-1][1]
            else:
                for i in range(len(parsed_stops) - 1):
                    s0, c0 = parsed_stops[i]
                    s1, c1 = parsed_stops[i + 1]
                    if s0 <= t <= s1:
                        sub_t = (t - s0) / (s1 - s0) if s1 != s0 else 0
                        col = interpolate_color(c0, c1, sub_t)
                        break
            gradient.putpixel((x, y), col)

    return gradient

def create_radial_gradient(
    width: int,
    height: int,
    color_stops: List[Tuple[float, str]]
) -> Image.Image:
    """Generate a radial gradient image from center to outer edge."""
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    parsed_stops = [(stop, hex_to_rgba(c)) for stop, c in color_stops]
    parsed_stops.sort(key=lambda x: x[0])

    cx, cy = width / 2.0, height / 2.0
    max_dist = math.sqrt(cx * cx + cy * cy)

    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            t = min(1.0, dist / max_dist)

            if t <= parsed_stops[0][0]:
                col = parsed_stops[0][1]
            elif t >= parsed_stops[-1][0]:
                col = parsed_stops[-1][1]
            else:
                for i in range(len(parsed_stops) - 1):
                    s0, c0 = parsed_stops[i]
                    s1, c1 = parsed_stops[i + 1]
                    if s0 <= t <= s1:
                        sub_t = (t - s0) / (s1 - s0) if s1 != s0 else 0
                        col = interpolate_color(c0, c1, sub_t)
                        break
            gradient.putpixel((x, y), col)

    return gradient
