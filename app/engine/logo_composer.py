import io
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageOps, ImageFilter

class LogoPosition:
    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"

def process_logo(
    logo_image: Image.Image,
    target_size: int,
    background_color: Optional[Tuple[int, int, int, int]] = (255, 255, 255, 255),
    padding_ratio: float = 0.15,
    border_radius_ratio: float = 0.22,
    border_color: Optional[Tuple[int, int, int, int]] = None
) -> Image.Image:
    """
    Resize, pad, and frame a logo image into a clean emblem badge.
    target_size: Exact pixel dimension of the logo badge.
    padding_ratio: Padding inside the emblem around the logo.
    border_radius_ratio: Rounded corner radius.
    border_color: Optional subtle border for contrast.
    """
    logo = logo_image.convert("RGBA")
    
    # Calculate inner icon size with padding
    pad = int(target_size * padding_ratio)
    inner_size = max(8, target_size - (pad * 2))
    
    # Scale logo maintaining aspect ratio with high quality lanczos resampling
    logo.thumbnail((inner_size, inner_size), Image.Resampling.LANCZOS)
    
    # Create framed canvas
    framed = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(framed)
    
    radius = int(target_size * border_radius_ratio)
    
    # Draw background badge
    if background_color and background_color[3] > 0:
        draw.rounded_rectangle(
            [0, 0, target_size - 1, target_size - 1],
            radius=radius,
            fill=background_color,
            outline=border_color or (220, 220, 220, 180),
            width=max(1, int(target_size * 0.02))
        )
    
    # Center inner logo on the framed badge
    offset_x = (target_size - logo.width) // 2
    offset_y = (target_size - logo.height) // 2
    framed.paste(logo, (offset_x, offset_y), mask=logo)
    
    return framed

def compose_logo_on_qr(
    qr_image: Image.Image,
    logo_image: Image.Image,
    position: str = LogoPosition.CENTER,
    logo_size_ratio: float = 0.22,
    bg_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    module_size: int = 16,
    matrix_size: int = 21,
    quiet_zone: int = 4
) -> Image.Image:
    """
    Compose logo onto the QR image aligned to module grid boundaries.
    """
    qr_w, qr_h = qr_image.size
    
    # Calculate grid-aligned logo size
    logo_modules = max(3, int(matrix_size * logo_size_ratio))
    target_logo_size = logo_modules * module_size
    
    framed_logo = process_logo(
        logo_image,
        target_logo_size,
        background_color=bg_color,
        border_color=(bg_color[0], bg_color[1], bg_color[2], 255)
    )
    
    # Calculate grid-aligned paste coordinates
    if position == LogoPosition.CENTER:
        start_mod = (matrix_size - logo_modules) // 2
        x = (quiet_zone + start_mod) * module_size
        y = (quiet_zone + start_mod) * module_size
    elif position == LogoPosition.TOP:
        x = (qr_w - target_logo_size) // 2
        y = int(qr_h * 0.08)
    elif position == LogoPosition.BOTTOM:
        x = (qr_w - target_logo_size) // 2
        y = qr_h - target_logo_size - int(qr_h * 0.08)
    else:
        start_mod = (matrix_size - logo_modules) // 2
        x = (quiet_zone + start_mod) * module_size
        y = (quiet_zone + start_mod) * module_size

    # Paste with alpha transparency
    result = qr_image.copy()
    result.paste(framed_logo, (x, y), mask=framed_logo)
    return result
