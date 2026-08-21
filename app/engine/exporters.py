import io
import base64
from typing import List, Tuple, Optional
from PIL import Image
from .shapes import ModuleShape, EyeShape

def export_png_bytes(image: Image.Image, dpi: int = 300) -> bytes:
    """Export PIL Image as high-DPI PNG byte array."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(dpi, dpi), optimize=True)
    return buffer.getvalue()

def export_png_base64(image: Image.Image, dpi: int = 300) -> str:
    """Export PIL Image as base64 data URI."""
    raw_bytes = export_png_bytes(image, dpi=dpi)
    b64_str = base64.b64encode(raw_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64_str}"

def export_svg_string(
    matrix: List[List[bool]],
    module_size: int = 10,
    quiet_zone: int = 4,
    shape: str = ModuleShape.SQUARE,
    eye_shape: str = EyeShape.SQUARE,
    foreground_color: str = "#000000",
    background_color: str = "#FFFFFF",
    gradient_stops: Optional[List[Tuple[float, str]]] = None,
    gradient_type: str = "linear",
    gradient_angle: float = 45.0,
    logo_svg_data: Optional[str] = None
) -> str:
    """
    Generate clean, pure Scalable Vector Graphics (SVG) XML string.
    Supports all 8 module shapes and 6 corner eye styles.
    """
    matrix_size = len(matrix)
    total_modules = matrix_size + (quiet_zone * 2)
    viewbox_dim = total_modules * module_size

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {viewbox_dim} {viewbox_dim}" width="{viewbox_dim}" height="{viewbox_dim}">'
    ]

    # 1. Defs section for Gradients
    fill_id = "qr-fg"
    if gradient_stops and len(gradient_stops) >= 2:
        svg_parts.append('<defs>')
        if gradient_type == "radial":
            svg_parts.append('<radialGradient id="qr-gradient" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">')
        else: # linear
            import math
            rad = math.radians(gradient_angle)
            x1 = 50 - 50 * math.cos(rad)
            y1 = 50 - 50 * math.sin(rad)
            x2 = 50 + 50 * math.cos(rad)
            y2 = 50 + 50 * math.sin(rad)
            svg_parts.append(f'<linearGradient id="qr-gradient" x1="{x1:.1f}%" y1="{y1:.1f}%" x2="{x2:.1f}%" y2="{y2:.1f}%">')

        for stop, col in gradient_stops:
            svg_parts.append(f'  <stop offset="{stop * 100:.1f}%" stop-color="{col}"/>')

        if gradient_type == "radial":
            svg_parts.append('</radialGradient>')
        else:
            svg_parts.append('</linearGradient>')
        svg_parts.append('</defs>')
        fill_id = "url(#qr-gradient)"
    else:
        fill_id = foreground_color

    # 2. Background Rect
    if background_color and background_color.lower() != "transparent":
        svg_parts.append(f'<rect width="{viewbox_dim}" height="{viewbox_dim}" fill="{background_color}"/>')

    # Finder Pattern Coordinate Ranges
    def is_finder_module(r: int, c: int) -> bool:
        if r < 7 and c < 7:
            return True
        if r < 7 and c >= matrix_size - 7:
            return True
        if r >= matrix_size - 7 and c < 7:
            return True
        return False

    # 3. Draw Finder Eyes
    finder_coords = [
        (quiet_zone, quiet_zone),
        (quiet_zone, quiet_zone + matrix_size - 7),
        (quiet_zone + matrix_size - 7, quiet_zone)
    ]

    for fx, fy in finder_coords:
        x_px = fx * module_size
        y_px = fy * module_size
        eye_dim = 7 * module_size
        mod = module_size

        if eye_shape == EyeShape.ROUNDED:
            rx = mod * 0.5
            svg_parts.append(f'<rect x="{x_px}" y="{y_px}" width="{eye_dim}" height="{eye_dim}" rx="{rx}" fill="{fill_id}"/>')
            svg_parts.append(f'<rect x="{x_px + mod}" y="{y_px + mod}" width="{eye_dim - mod*2}" height="{eye_dim - mod*2}" rx="{rx * 0.7}" fill="{background_color}"/>')
            svg_parts.append(f'<rect x="{x_px + mod*2}" y="{y_px + mod*2}" width="{eye_dim - mod*4}" height="{eye_dim - mod*4}" rx="{rx * 0.5}" fill="{fill_id}"/>')
        elif eye_shape == EyeShape.CIRCLE:
            svg_parts.append(f'<rect x="{x_px}" y="{y_px}" width="{eye_dim}" height="{eye_dim}" fill="{fill_id}"/>')
            svg_parts.append(f'<rect x="{x_px + mod}" y="{y_px + mod}" width="{eye_dim - mod*2}" height="{eye_dim - mod*2}" fill="{background_color}"/>')
            cx, cy = x_px + 3.5 * mod, y_px + 3.5 * mod
            svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{1.5 * mod}" fill="{fill_id}"/>')
        elif eye_shape == EyeShape.LEAF:
            rx = mod * 1.5
            svg_parts.append(f'<rect x="{x_px}" y="{y_px}" width="{eye_dim}" height="{eye_dim}" rx="{rx}" fill="{fill_id}"/>')
            svg_parts.append(f'<rect x="{x_px + mod}" y="{y_px + mod}" width="{eye_dim - mod*2}" height="{eye_dim - mod*2}" rx="{rx * 0.7}" fill="{background_color}"/>')
            svg_parts.append(f'<rect x="{x_px + mod*2}" y="{y_px + mod*2}" width="{eye_dim - mod*4}" height="{eye_dim - mod*4}" rx="{rx * 0.5}" fill="{fill_id}"/>')
        elif eye_shape == EyeShape.DIAMOND:
            svg_parts.append(f'<rect x="{x_px}" y="{y_px}" width="{eye_dim}" height="{eye_dim}" fill="{fill_id}"/>')
            svg_parts.append(f'<rect x="{x_px + mod}" y="{y_px + mod}" width="{eye_dim - mod*2}" height="{eye_dim - mod*2}" fill="{background_color}"/>')
            cx, cy = x_px + 3.5 * mod, y_px + 3.5 * mod
            hw = 1.5 * mod
            svg_parts.append(f'<polygon points="{cx},{cy-hw} {cx+hw},{cy} {cx},{cy+hw} {cx-hw},{cy}" fill="{fill_id}"/>')
        elif eye_shape == EyeShape.SHIELD:
            rx = mod * 0.3
            svg_parts.append(f'<rect x="{x_px}" y="{y_px}" width="{eye_dim}" height="{eye_dim}" rx="{rx}" fill="{fill_id}"/>')
            svg_parts.append(f'<rect x="{x_px + mod}" y="{y_px + mod}" width="{eye_dim - mod*2}" height="{eye_dim - mod*2}" rx="{rx * 0.7}" fill="{background_color}"/>')
            svg_parts.append(f'<rect x="{x_px + mod*2}" y="{y_px + mod*2}" width="{eye_dim - mod*4}" height="{eye_dim - mod*4}" fill="{fill_id}"/>')
        else: # SQUARE
            svg_parts.append(f'<rect x="{x_px}" y="{y_px}" width="{eye_dim}" height="{eye_dim}" fill="{fill_id}"/>')
            svg_parts.append(f'<rect x="{x_px + mod}" y="{y_px + mod}" width="{eye_dim - mod*2}" height="{eye_dim - mod*2}" fill="{background_color}"/>')
            svg_parts.append(f'<rect x="{x_px + mod*2}" y="{y_px + mod*2}" width="{eye_dim - mod*4}" height="{eye_dim - mod*4}" fill="{fill_id}"/>')

    # 4. Draw Data Modules
    path_data = []
    for r in range(matrix_size):
        for c in range(matrix_size):
            if not matrix[r][c] or is_finder_module(r, c):
                continue

            x = (quiet_zone + c) * module_size
            y = (quiet_zone + r) * module_size
            ms = module_size

            if shape == ModuleShape.DOTS:
                cx, cy = x + ms / 2.0, y + ms / 2.0
                rad = ms * 0.38
                path_data.append(f'M {cx-rad},{cy} a {rad},{rad} 0 1,0 {rad*2},0 a {rad},{rad} 0 1,0 {-rad*2},0')

            elif shape == ModuleShape.CIRCLE:
                cx, cy = x + ms / 2.0, y + ms / 2.0
                rad = ms / 2.0
                path_data.append(f'M {cx-rad},{cy} a {rad},{rad} 0 1,0 {rad*2},0 a {rad},{rad} 0 1,0 {-rad*2},0')

            elif shape == ModuleShape.DIAMOND:
                cx, cy = x + ms / 2.0, y + ms / 2.0
                path_data.append(f'M {cx},{y} L {x+ms},{cy} L {cx},{y+ms} L {x},{cy} Z')

            elif shape == ModuleShape.ROUNDED:
                rad = ms * 0.35
                path_data.append(f'M {x+rad},{y} H {x+ms-rad} A {rad},{rad} 0 0 1 {x+ms},{y+rad} V {y+ms-rad} A {rad},{rad} 0 0 1 {x+ms-rad},{y+ms} H {x+rad} A {rad},{rad} 0 0 1 {x},{y+ms-rad} V {y+rad} A {rad},{rad} 0 0 1 {x+rad},{y} Z')

            elif shape == ModuleShape.STAR:
                cx, cy = x + ms / 2.0, y + ms / 2.0
                w = ms * 0.2
                path_data.append(f'M {cx},{y} L {cx+w},{cy-w} L {x+ms},{cy} L {cx+w},{cy+w} L {cx},{y+ms} L {cx-w},{cy+w} L {x},{cy} L {cx-w},{cy-w} Z')

            elif shape == ModuleShape.CROSS:
                arm = ms * 0.28
                path_data.append(f'M {x+arm},{y} H {x+ms-arm} V {y+arm} H {x+ms} V {y+ms-arm} H {x+ms-arm} V {y+ms} H {x+arm} V {y+ms-arm} H {x} V {y+arm} H {x+arm} Z')

            elif shape == ModuleShape.CLASSY:
                rad = ms * 0.45
                path_data.append(f'M {x+rad},{y} H {x+ms} V {y+ms-rad} A {rad},{rad} 0 0 1 {x+ms-rad},{y+ms} H {x} V {y+rad} A {rad},{rad} 0 0 1 {x+rad},{y} Z')

            else: # SQUARE
                path_data.append(f'M {x},{y} H {x+ms} V {y+ms} H {x} Z')

    if path_data:
        svg_parts.append(f'<path d="{" ".join(path_data)}" fill="{fill_id}"/>')

    svg_parts.append('</svg>')
    return "".join(svg_parts)
